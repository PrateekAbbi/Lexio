"""HTTP exception translation for application service errors."""

import logging

from fastapi import HTTPException

from app.exceptions import (
    ConfigurationError,
    EmptyDocumentError,
    ExternalServiceError,
    UnsupportedDocumentError,
)
from app.services.auth import InvalidSessionError


logger = logging.getLogger("legal-pipeline.api")


def to_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, InvalidSessionError):
        return HTTPException(status_code=401, detail=str(exc))
    if isinstance(exc, ConfigurationError):
        return HTTPException(
            status_code=500,
            detail=f"{exc} Add the missing value to backend/.env and restart the API.",
        )
    if isinstance(exc, UnsupportedDocumentError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, EmptyDocumentError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ExternalServiceError):
        return HTTPException(status_code=502, detail=str(exc))
    logger.exception("Unhandled backend error: %s", exc)
    return HTTPException(status_code=500, detail="Unexpected backend error.")
