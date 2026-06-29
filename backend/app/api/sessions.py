"""Chat session and document question endpoints."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.api.errors import to_http_exception
from app.schemas import CreateSessionRequest, SessionQueryRequest
from app.services.auth import get_user_id
from app.services.qa import QuestionAnsweringService


router = APIRouter()


@router.post("/sessions")
async def create_session(
    payload: CreateSessionRequest,
    current_user: Any = Depends(get_current_user),
) -> dict[str, str]:
    try:
        session_id = await QuestionAnsweringService().create_session(
            document_id=payload.document_id,
            user_id=get_user_id(current_user),
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc
    return {"session_id": session_id}


@router.post("/sessions/{session_id}/query")
async def query_session(
    session_id: str,
    payload: SessionQueryRequest,
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        result = await QuestionAnsweringService().answer_session_question(
            session_id=session_id,
            question=payload.question,
            user_id=get_user_id(current_user),
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc

    return {
        "answer": result.answer,
        "sources": result.sources,
        "session_id": session_id,
        "latency_ms": result.latency_ms,
    }


@router.get("/sessions")
async def list_sessions(current_user: Any = Depends(get_current_user)) -> list[dict[str, Any]]:
    try:
        return await QuestionAnsweringService().list_sessions(get_user_id(current_user))
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.get("/sessions/{session_id}/messages")
async def list_messages(
    session_id: str,
    current_user: Any = Depends(get_current_user),
) -> list[dict[str, Any]]:
    try:
        return await QuestionAnsweringService().list_messages(
            session_id=session_id,
            user_id=get_user_id(current_user),
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc

