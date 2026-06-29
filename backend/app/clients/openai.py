"""Small OpenAI HTTP client used by ingestion and Q&A services."""

from __future__ import annotations

import asyncio
from typing import Iterable

import httpx

from app.config import Settings, get_settings
from app.exceptions import ExternalServiceError


class OpenAIClient:
    """Wraps the OpenAI endpoints this backend depends on.

    The code uses direct HTTP requests instead of an SDK so dependency weight
    stays unchanged and existing ``requirements.txt`` remains compatible.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.require_openai_api_key()}",
            "Content-Type": "application/json",
        }

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings in the same order as the provided texts."""

        if not texts:
            return []

        batches = list(_batch(texts, self.settings.embedding_batch_size))
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        async with httpx.AsyncClient(limits=limits) as client:
            results = await asyncio.gather(*(self._embed_batch(client, batch) for batch in batches))

        return [embedding for batch_result in results for embedding in batch_result]

    async def embed_query(self, query: str) -> list[float]:
        async with httpx.AsyncClient() as client:
            embeddings = await self._embed_batch(client, [query], timeout=30)
        return embeddings[0]

    async def generate_answer(self, messages: list[dict[str, str]]) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.settings.openai_chat_url,
                headers=self._headers(),
                json={
                    "model": self.settings.require_answer_model(),
                    "messages": messages,
                    "temperature": 0.2,
                },
                timeout=60,
            )

        if response.status_code >= 400:
            raise ExternalServiceError(f"OpenAI chat request failed: {response.text}")

        try:
            return response.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ExternalServiceError("OpenAI chat response was missing answer content.") from exc

    async def _embed_batch(
        self,
        client: httpx.AsyncClient,
        texts: list[str],
        timeout: int = 60,
    ) -> list[list[float]]:
        response = await client.post(
            self.settings.openai_embedding_url,
            headers=self._headers(),
            json={"model": self.settings.require_embedding_model(), "input": texts},
            timeout=timeout,
        )

        if response.status_code >= 400:
            raise ExternalServiceError(f"OpenAI embedding request failed: {response.text}")

        try:
            payload = response.json()
            ordered = sorted(payload["data"], key=lambda item: item["index"])
            return [item["embedding"] for item in ordered]
        except (KeyError, TypeError) as exc:
            raise ExternalServiceError("OpenAI embedding response was malformed.") from exc


def _batch(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]
