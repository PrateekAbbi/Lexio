"""Document ingestion workflow."""

from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path

from app.clients.chroma import ChromaRepository
from app.clients.openai import OpenAIClient
from app.exceptions import EmptyDocumentError, UnsupportedDocumentError
from app.models import IndexedDocument, TextChunk
from app.repositories.supabase_repository import SupabaseRepository
from app.services.audit import log_ingest
from app.services.chunking import build_chunks_for_page
from app.services.pii import process_document, validate_no_pii_remains
from app.services.pdf import extract_pdf_text


class DocumentIngestionService:
    """Coordinates validation, parsing, embedding, vector storage, and metadata."""

    def __init__(
        self,
        *,
        openai_client: OpenAIClient | None = None,
        chroma_repository: ChromaRepository | None = None,
        supabase_repository: SupabaseRepository | None = None,
    ) -> None:
        self.openai_client = openai_client or OpenAIClient()
        self.chroma_repository = chroma_repository or ChromaRepository()
        self.supabase_repository = supabase_repository or SupabaseRepository()

    async def ingest_pdf(self, *, filename: str | None, pdf_bytes: bytes, user_id: str) -> IndexedDocument:
        started = time.perf_counter()
        normalized_filename = _validate_pdf_upload(filename, pdf_bytes)

        pages, page_count = await asyncio.to_thread(extract_pdf_text, pdf_bytes)
        redaction_result = await process_document(pages)
        document_id = str(uuid.uuid4())
        collection_name = f"doc_{document_id}"

        chunks = [
            chunk
            for page in redaction_result["redacted_pages"]
            for chunk in build_chunks_for_page(page["text"], page["page_number"])
        ]
        if not chunks:
            raise EmptyDocumentError("This PDF appears to be scanned. OCR support coming soon.")

        chunks, chunk_second_pass_catches = self._validate_chunks_before_embedding(chunks)
        texts = [chunk.text for chunk in chunks]
        embed_started = time.perf_counter()
        embeddings = await self.openai_client.embed_texts(texts)
        embed_time_ms = round((time.perf_counter() - embed_started) * 1000)

        await asyncio.to_thread(
            self._store_vectors,
            document_id=document_id,
            collection_name=collection_name,
            user_id=user_id,
            filename=normalized_filename,
            doc_type=redaction_result["doc_type"],
            chunks=chunks,
            embeddings=embeddings,
        )

        try:
            await self.supabase_repository.create_document(
                document_id=document_id,
                user_id=user_id,
                filename=normalized_filename,
                page_count=page_count,
                chunk_count=len(chunks),
                collection_name=collection_name,
                doc_type=redaction_result["doc_type"],
                roles_detected=redaction_result["roles_detected"],
                total_redactions=redaction_result["total_redactions"] + chunk_second_pass_catches,
            )
        except Exception:
            # If metadata fails after vector insertion, remove the now-unreachable
            # collection so a retry does not leave orphaned Chroma data behind.
            await asyncio.to_thread(self.chroma_repository.delete_collection_if_exists, collection_name)
            raise

        doc_type = redaction_result["doc_type"]
        roles_detected = redaction_result["roles_detected"]
        total_redactions = redaction_result["total_redactions"] + chunk_second_pass_catches
        total_second_pass_catches = redaction_result["second_pass_catches"] + chunk_second_pass_catches
        log_ingest(
            doc_id=document_id,
            doc_type=doc_type,
            total_redactions=total_redactions,
            second_pass_catches=total_second_pass_catches,
            roles_detected=roles_detected,
        )

        role_map = redaction_result.get("role_map")
        del pages, redaction_result, role_map, pdf_bytes, texts, embeddings

        return IndexedDocument(
            document_id=document_id,
            filename=normalized_filename,
            collection_name=collection_name,
            page_count=page_count,
            chunk_count=len(chunks),
            doc_type=doc_type,
            roles_detected=roles_detected,
            total_redactions=total_redactions,
            embed_time_ms=embed_time_ms,
            ingest_time_ms=round((time.perf_counter() - started) * 1000),
        )

    def _store_vectors(
        self,
        *,
        document_id: str,
        collection_name: str,
        user_id: str,
        filename: str,
        doc_type: str,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
    ) -> None:
        ids = [f"{document_id}:{index}" for index in range(len(chunks))]
        metadatas = [
            {
                "document_id": document_id,
                "user_id": user_id,
                "filename": filename,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "global_chunk_index": index,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "doc_type": doc_type,
            }
            for index, chunk in enumerate(chunks)
        ]

        self.chroma_repository.add_chunks(
            collection_name=collection_name,
            ids=ids,
            texts=[chunk.text for chunk in chunks],
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def _validate_chunks_before_embedding(self, chunks: list[TextChunk]) -> tuple[list[TextChunk], int]:
        clean_chunks: list[TextChunk] = []
        extra_redactions = 0
        for chunk in chunks:
            clean_text, count = validate_no_pii_remains(chunk.text)
            extra_redactions += count
            clean_chunks.append(
                TextChunk(
                    text=clean_text,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                )
            )
        return clean_chunks, extra_redactions


def _validate_pdf_upload(filename: str | None, pdf_bytes: bytes) -> str:
    if not filename or Path(filename).suffix.lower() != ".pdf":
        raise UnsupportedDocumentError("Only PDF files are supported.")
    if not pdf_bytes:
        raise UnsupportedDocumentError("Uploaded file is empty.")
    return filename
