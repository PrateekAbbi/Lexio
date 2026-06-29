"""Text chunking optimized for citation-friendly document retrieval."""

from __future__ import annotations

import re

from app.config import Settings, get_settings
from app.models import TextChunk


SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")
WORD_PATTERN = re.compile(r"\S+")


def estimate_tokens(text: str) -> int:
    """Cheap token estimate good enough for stable chunk sizing.

    The previous implementation used word count * 1.33; keeping that heuristic
    avoids changing chunk shapes unexpectedly while still avoiding a tokenizer
    dependency.
    """

    return max(1, int(len(WORD_PATTERN.findall(text)) * 1.33))


def split_sentences(text: str) -> list[tuple[str, int, int]]:
    """Split text into sentence-like units while preserving character offsets."""

    normalized = re.sub(r"[ \t]+", " ", text)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)

    sentences: list[tuple[str, int, int]] = []
    cursor = 0
    for part in SENTENCE_BOUNDARY.split(normalized):
        sentence = part.strip()
        if not sentence:
            cursor += len(part)
            continue

        start = normalized.find(sentence, cursor)
        if start == -1:
            start = cursor
        end = start + len(sentence)
        sentences.append((sentence, start, end))
        cursor = end

    if not sentences and normalized.strip():
        stripped = normalized.strip()
        start = normalized.find(stripped)
        sentences.append((stripped, start, start + len(stripped)))

    return sentences


def build_chunks_for_page(
    page_text: str,
    page_number: int,
    settings: Settings | None = None,
) -> list[TextChunk]:
    """Build overlapping chunks for one page of text.

    Chunks target a readable amount of evidence per retrieval result. A small
    overlap reduces the chance that clauses split across sentence boundaries
    lose necessary context.
    """

    settings = settings or get_settings()
    sentences = split_sentences(page_text)
    chunks: list[TextChunk] = []
    current: list[tuple[str, int, int]] = []
    current_tokens = 0

    def append_current_chunk() -> None:
        if not current:
            return
        chunk_text = " ".join(sentence for sentence, _, _ in current).strip()
        if not chunk_text:
            return
        if chunks and chunk_text == chunks[-1].text:
            return
        chunks.append(
            TextChunk(
                text=chunk_text,
                page_number=page_number,
                chunk_index=len(chunks),
                char_start=current[0][1],
                char_end=current[-1][2],
            )
        )

    def keep_overlap() -> tuple[list[tuple[str, int, int]], int]:
        overlap: list[tuple[str, int, int]] = []
        overlap_tokens = 0
        for item in reversed(current):
            item_tokens = estimate_tokens(item[0])
            if item_tokens > settings.chunk_token_overlap and not overlap:
                break
            if overlap and overlap_tokens + item_tokens > settings.chunk_token_overlap:
                break
            overlap.insert(0, item)
            overlap_tokens += item_tokens
            if overlap_tokens >= settings.chunk_token_overlap:
                break
        return overlap, overlap_tokens

    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence[0])
        if current and current_tokens + sentence_tokens > settings.chunk_token_target:
            append_current_chunk()
            current, current_tokens = keep_overlap()

        current.append(sentence)
        current_tokens += sentence_tokens

    append_current_chunk()
    return chunks

