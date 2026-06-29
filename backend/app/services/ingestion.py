"""Document ingestion workflow."""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from pathlib import Path

from app.clients.chroma import ChromaRepository
from app.clients.openai import OpenAIClient
from app.exceptions import EmptyDocumentError, UnsupportedDocumentError
from app.models import IndexedDocument, TextChunk
from app.repositories.supabase_repository import SupabaseRepository
from app.services.chunking import build_chunks_for_page
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
        document_id = str(uuid.uuid4())
        collection_name = f"doc_{document_id}"

        chunks = [
            chunk
            for page in pages
            for chunk in build_chunks_for_page(page.text, page.page_number)
        ]
        if not chunks:
            raise EmptyDocumentError("This PDF appears to be scanned. OCR support coming soon.")

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
            doc_hash=hashlib.sha256(pdf_bytes).hexdigest()[:16],
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
            )
        except Exception:
            # If metadata fails after vector insertion, remove the now-unreachable
            # collection so a retry does not leave orphaned Chroma data behind.
            await asyncio.to_thread(self.chroma_repository.delete_collection_if_exists, collection_name)
            raise

        return IndexedDocument(
            document_id=document_id,
            filename=normalized_filename,
            collection_name=collection_name,
            page_count=page_count,
            chunk_count=len(chunks),
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
        doc_hash: str,
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
                "doc_hash": doc_hash,
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


def _validate_pdf_upload(filename: str | None, pdf_bytes: bytes) -> str:
    if not filename or Path(filename).suffix.lower() != ".pdf":
        raise UnsupportedDocumentError("Only PDF files are supported.")
    if not pdf_bytes:
        raise UnsupportedDocumentError("Uploaded file is empty.")
    return filename
