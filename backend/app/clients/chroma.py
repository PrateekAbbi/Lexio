"""ChromaDB client and collection helpers."""

from functools import lru_cache
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    settings = get_settings()
    return chromadb.PersistentClient(
        path=str(settings.chroma_path),
        settings=ChromaSettings(anonymized_telemetry=False),
    )


class ChromaRepository:
    """Persistence adapter for document vectors."""

    def __init__(self, client: chromadb.PersistentClient | None = None) -> None:
        self.client = client or get_chroma_client()

    def get_or_create_document_collection(self, collection_name: str) -> Any:
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        collection_name: str,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        collection = self.get_or_create_document_collection(collection_name)
        collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

    def query_chunks(
        self,
        collection_name: str,
        query_embedding: list[float],
        result_count: int,
    ) -> dict[str, Any]:
        collection = self.client.get_collection(name=collection_name)
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=result_count,
            include=["documents", "metadatas", "distances"],
        )

    def delete_collection_if_exists(self, collection_name: str) -> None:
        try:
            self.client.delete_collection(name=collection_name)
        except Exception:
            # Chroma raises if the collection is already absent. Cleanup is a
            # best-effort compensation path, so absence is not an application
            # error.
            return

