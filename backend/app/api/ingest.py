"""Document upload endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.dependencies import get_current_user
from app.api.errors import to_http_exception
from app.services.auth import get_user_id
from app.services.ingestion import DocumentIngestionService


router = APIRouter()


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Ingest a PDF and return the existing response shape expected by the UI."""

    try:
        document = await DocumentIngestionService().ingest_pdf(
            filename=file.filename,
            pdf_bytes=await file.read(),
            user_id=get_user_id(current_user),
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc

    return {
        "doc_id": document.document_id,
        "filename": document.filename,
        "total_chunks": document.chunk_count,
        "page_count": document.page_count,
        "pages": document.page_count,
        "doc_type": document.doc_type,
        "roles_detected": document.roles_detected,
        "total_redactions": document.total_redactions,
        "embed_time_ms": document.embed_time_ms,
        "ingest_time_ms": document.ingest_time_ms,
    }
