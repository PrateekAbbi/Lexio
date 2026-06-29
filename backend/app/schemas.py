"""Pydantic schemas for HTTP request validation."""

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    document_id: str = Field(..., min_length=1)


class SessionQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)

