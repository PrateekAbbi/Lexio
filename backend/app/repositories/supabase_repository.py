"""Supabase persistence operations for documents, sessions, and messages."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from app.clients.supabase import get_supabase_client
from app.exceptions import ExternalServiceError


logger = logging.getLogger("legal-pipeline.supabase")


class SupabaseRepository:
    """Typed facade over the Supabase Python query builder.

    Supabase's SDK is synchronous, while FastAPI handlers are async. Every SDK
    call is executed in a worker thread so slow network I/O does not block the
    event loop.
    """

    def __init__(self, client: Any | None = None) -> None:
        self.client = client or get_supabase_client()

    async def create_document(
        self,
        *,
        document_id: str,
        user_id: str,
        filename: str,
        page_count: int,
        chunk_count: int,
        collection_name: str,
    ) -> dict[str, Any]:
        response = await self._execute(
            lambda: self.client.table("documents").insert(
                {
                    "id": document_id,
                    "user_id": user_id,
                    "filename": filename,
                    "page_count": page_count,
                    "chunk_count": chunk_count,
                    "chroma_collection_id": collection_name,
                }
            ),
            "document metadata insert",
        )
        return _first_row(response, "Failed to save document metadata.")

    async def get_owned_document(self, document_id: str, user_id: str) -> dict[str, Any]:
        response = await self._execute(
            lambda: self.client.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("user_id", user_id)
            .limit(1),
            "document ownership check",
        )
        row = _optional_first_row(response)
        if not row:
            raise LookupError("Document not found.")
        return row

    async def create_session(self, user_id: str, document_id: str) -> dict[str, Any]:
        response = await self._execute(
            lambda: self.client.table("sessions").insert(
                {"user_id": user_id, "document_id": document_id, "title": None}
            ),
            "session creation",
        )
        return _first_row(response, "Failed to create session.")

    async def get_owned_session(self, session_id: str, user_id: str) -> dict[str, Any]:
        response = await self._execute(
            lambda: self.client.table("sessions")
            .select("*")
            .eq("id", session_id)
            .eq("user_id", user_id)
            .limit(1),
            "session ownership check",
        )
        row = _optional_first_row(response)
        if not row:
            raise LookupError("Session not found.")
        return row

    async def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        response = await self._execute(
            lambda: self.client.table("sessions")
            .select("id, document_id, title, last_active_at, documents(filename,page_count,chunk_count)")
            .eq("user_id", user_id)
            .order("last_active_at", desc=True),
            "session list fetch",
        )
        return response.data or []

    async def list_messages(self, session_id: str) -> list[dict[str, Any]]:
        response = await self._execute(
            lambda: self.client.table("messages")
            .select("id, role, content, sources, latency_ms, created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=False),
            "message history fetch",
        )
        return response.data or []

    async def add_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
        latency_ms: int | None = None,
    ) -> dict[str, Any]:
        response = await self._execute(
            lambda: self.client.table("messages").insert(
                {
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "sources": sources,
                    "latency_ms": latency_ms,
                }
            ),
            f"{role} message insert",
        )
        return _first_row(response, "Failed to save message.")

    async def update_session_activity(
        self,
        *,
        session_id: str,
        title: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {"last_active_at": _utc_now_iso()}
        if title is not None:
            payload["title"] = title

        await self._execute(
            lambda: self.client.table("sessions").update(payload).eq("id", session_id),
            "session activity update",
        )

    async def _execute(self, operation: Callable[[], Any], label: str) -> Any:
        try:
            return await asyncio.to_thread(lambda: operation().execute())
        except Exception as exc:
            message = _supabase_error_message(exc)
            logger.exception("Supabase request failed during %s: %s", label, message)
            raise ExternalServiceError(f"Supabase request failed during {label}: {message}") from exc


def _optional_first_row(response: Any) -> dict[str, Any] | None:
    data = getattr(response, "data", None) or []
    return data[0] if data else None


def _first_row(response: Any, fallback_message: str) -> dict[str, Any]:
    row = _optional_first_row(response)
    if not row:
        raise ExternalServiceError(fallback_message)
    return row


def _supabase_error_message(exc: Exception) -> str:
    for attr in ("message", "details", "hint", "code"):
        value = getattr(exc, attr, None)
        if value:
            return str(value)
    return str(exc) or exc.__class__.__name__


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

