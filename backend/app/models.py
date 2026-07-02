"""Shared data models used inside the backend.

These dataclasses describe business data passed between services. FastAPI
request bodies stay in ``schemas.py`` so API validation remains separate from
internal processing.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PdfPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class TextChunk:
    text: str
    page_number: int
    chunk_index: int
    char_start: int
    char_end: int


@dataclass(frozen=True)
class IndexedDocument:
    document_id: str
    filename: str
    collection_name: str
    page_count: int
    chunk_count: int
    doc_type: str
    roles_detected: list[str]
    total_redactions: int
    embed_time_ms: int
    ingest_time_ms: int


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    metadata: dict[str, Any]
    distance: float

    @property
    def page_number(self) -> int:
        return int(self.metadata["page_number"])

    @property
    def chunk_index(self) -> int:
        return int(self.metadata["chunk_index"])


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    sources: list[dict[str, Any]]
    latency_ms: int
