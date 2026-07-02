"""Question answering workflow over indexed legal documents."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.clients.chroma import ChromaRepository
from app.clients.openai import OpenAIClient
from app.config import Settings, get_settings
from app.models import AnswerResult, RetrievedChunk
from app.repositories.supabase_repository import SupabaseRepository
from app.services.audit import log_chunk_pii_detected_at_query_time, log_query_blocked
from app.services.guardrail import is_identity_seeking_query
from app.services.pii import scan_all_pii, validate_no_pii_remains
from app.services.prompt_security import (
    LockedAnswerPlan,
    build_guarded_chat_messages,
    format_untrusted_context,
    get_locked_answer_plan,
)


PRIVACY_SAFE_IDENTITY_RESPONSE = (
    "For privacy reasons, this system does not store or reveal personal information from uploaded documents, "
    "including real names, addresses, phone numbers, email addresses, account numbers, government IDs, or other "
    "identifying details. I can describe the parties by their document roles, such as [LANDLORD], [TENANT], "
    "[CANDIDATE], or [OFFEROR], and summarize their obligations using the redacted document text."
)


class QuestionAnsweringService:
    """Coordinates ownership checks, retrieval, answer generation, and history."""

    def __init__(
        self,
        *,
        openai_client: OpenAIClient | None = None,
        chroma_repository: ChromaRepository | None = None,
        supabase_repository: SupabaseRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.openai_client = openai_client or OpenAIClient(self.settings)
        self.chroma_repository = chroma_repository or ChromaRepository()
        self.supabase_repository = supabase_repository or SupabaseRepository()

    async def create_session(self, *, document_id: str, user_id: str) -> str:
        await self.supabase_repository.get_owned_document(document_id, user_id)
        session = await self.supabase_repository.create_session(user_id, document_id)
        return session["id"]

    async def answer_session_question(
        self,
        *,
        session_id: str,
        question: str,
        user_id: str,
    ) -> AnswerResult:
        started = time.perf_counter()
        locked_plan = get_locked_answer_plan()
        session = await self.supabase_repository.get_owned_session(session_id, user_id)
        if is_identity_seeking_query(question):
            log_query_blocked(session_id, "identity_seeking_query")
            latency_ms = round((time.perf_counter() - started) * 1000)
            prior_messages = await self.supabase_repository.list_messages(session_id)
            first_user_message = not any(message["role"] == "user" for message in prior_messages)
            await self._persist_exchange(
                session_id=session_id,
                question=question,
                answer=PRIVACY_SAFE_IDENTITY_RESPONSE,
                sources=[],
                latency_ms=latency_ms,
                title=question.strip()[:60] if first_user_message else None,
            )
            return AnswerResult(
                answer=PRIVACY_SAFE_IDENTITY_RESPONSE,
                sources=[],
                latency_ms=latency_ms,
            )

        document = await self.supabase_repository.get_owned_document(session["document_id"], user_id)
        prior_messages = await self.supabase_repository.list_messages(session_id)

        question_embedding = await self.openai_client.embed_query(question)
        retrieved_chunks = await asyncio.to_thread(
            self._retrieve_chunks,
            document["chroma_collection_id"],
            question_embedding,
        )
        if not retrieved_chunks:
            raise LookupError("No indexed chunks found for this document.")

        retrieved_chunks = self._validate_retrieved_chunks(session_id, retrieved_chunks)
        answer = await self.openai_client.generate_answer(
            build_chat_messages(
                locked_plan=locked_plan,
                prior_messages=prior_messages,
                retrieved_chunks=retrieved_chunks,
                question=question,
            )
        )

        latency_ms = round((time.perf_counter() - started) * 1000)
        sources = build_sources(retrieved_chunks)

        first_user_message = not any(message["role"] == "user" for message in prior_messages)
        await self._persist_exchange(
            session_id=session_id,
            question=question,
            answer=answer,
            sources=sources,
            latency_ms=latency_ms,
            title=question.strip()[:60] if first_user_message else None,
        )

        return AnswerResult(answer=answer, sources=sources, latency_ms=latency_ms)

    async def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        sessions = await self.supabase_repository.list_sessions(user_id)
        return [format_session_summary(session) for session in sessions]

    async def list_messages(self, *, session_id: str, user_id: str) -> list[dict[str, Any]]:
        await self.supabase_repository.get_owned_session(session_id, user_id)
        return await self.supabase_repository.list_messages(session_id)

    def _retrieve_chunks(self, collection_name: str, question_embedding: list[float]) -> list[RetrievedChunk]:
        results = self.chroma_repository.query_chunks(
            collection_name=collection_name,
            query_embedding=question_embedding,
            result_count=self.settings.retrieval_result_count,
        )
        documents = _first_result_list(results, "documents")
        metadatas = _first_result_list(results, "metadatas")
        distances = _first_result_list(results, "distances")
        return [
            RetrievedChunk(text=document, metadata=metadata, distance=distance)
            for document, metadata, distance in zip(documents, metadatas, distances)
        ]

    def _validate_retrieved_chunks(self, session_id: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        clean_chunks: list[RetrievedChunk] = []
        leaked_entity_types: set[str] = set()
        for chunk in chunks:
            detected = scan_all_pii(chunk.text, threshold=0.35)
            if detected:
                leaked_entity_types.update(entity["entity_type"] for entity in detected)
                clean_text, _ = validate_no_pii_remains(chunk.text)
            else:
                clean_text = chunk.text
            clean_chunks.append(RetrievedChunk(text=clean_text, metadata=chunk.metadata, distance=chunk.distance))

        if leaked_entity_types:
            log_chunk_pii_detected_at_query_time(session_id, sorted(leaked_entity_types))
        return clean_chunks

    async def _persist_exchange(
        self,
        *,
        session_id: str,
        question: str,
        answer: str,
        sources: list[dict[str, Any]],
        latency_ms: int,
        title: str | None,
    ) -> None:
        await self.supabase_repository.add_message(
            session_id=session_id,
            role="user",
            content=question,
            sources=None,
            latency_ms=None,
        )
        await self.supabase_repository.add_message(
            session_id=session_id,
            role="assistant",
            content=answer,
            sources=sources,
            latency_ms=latency_ms,
        )
        await self.supabase_repository.update_session_activity(session_id=session_id, title=title)


def format_context(chunks: list[RetrievedChunk]) -> str:
    return format_untrusted_context(chunks)


def build_chat_messages(
    *,
    locked_plan: LockedAnswerPlan | None = None,
    prior_messages: list[dict[str, Any]],
    retrieved_chunks: list[RetrievedChunk] | None = None,
    question: str,
) -> list[dict[str, str]]:
    return build_guarded_chat_messages(
        locked_plan=locked_plan or get_locked_answer_plan(),
        prior_messages=prior_messages,
        retrieved_chunks=retrieved_chunks or [],
        question=question,
    )


def build_sources(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    return [
        {
            "page": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text.strip(),
            "text_snippet": chunk.text[:420].strip(),
            "similarity_score": round(similarity_from_distance(chunk.distance), 4),
        }
        for chunk in chunks
    ]


def similarity_from_distance(distance: float) -> float:
    return max(0.0, min(1.0, 1.0 - distance))


def _first_result_list(results: dict[str, Any], key: str) -> list[Any]:
    values = results.get(key) or [[]]
    return values[0] if values else []


def format_session_summary(session: dict[str, Any]) -> dict[str, Any]:
    document = session.get("documents") or {}
    return {
        "session_id": session["id"],
        "title": session.get("title"),
        "filename": document.get("filename", "Untitled document"),
        "page_count": document.get("page_count"),
        "chunk_count": document.get("chunk_count"),
        "last_active_at": session.get("last_active_at"),
        "message_count": None,
    }
