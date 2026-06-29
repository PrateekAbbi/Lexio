"""ChromaDB client and collection helpers."""

from functools import lru_cache
from typing import Any

import chromadb
from chromadb.errors import ChromaError, NotFoundError
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.exceptions import ConfigurationError, ExternalServiceError


@lru_cache(maxsize=1)
def get_chroma_client() -> Any:
    settings = get_settings()
    if settings.chroma_mode == "cloud":
        tenant, database, api_key = settings.require_chroma_cloud_credentials()
        return chromadb.CloudClient(
            tenant=tenant,
            database=database,
            api_key=api_key,
            cloud_host=settings.chroma_cloud_host,
            cloud_port=settings.chroma_cloud_port,
            enable_ssl=settings.chroma_cloud_ssl,
        )

    if settings.chroma_mode != "local":
        raise ConfigurationError("CHROMA_MODE must be either 'local' or 'cloud'.")

    return chromadb.PersistentClient(
        path=str(settings.chroma_path),
        settings=ChromaSettings(anonymized_telemetry=False),
    )


class ChromaRepository:
    """Persistence adapter for document vectors."""

    def __init__(self, client: Any | None = None) -> None:
        self.client = client or get_chroma_client()

    def get_or_create_document_collection(self, collection_name: str) -> Any:
        try:
            return self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except NotFoundError as exc:
            raise ExternalServiceError(
                "Chroma collection request returned 404. Check CHROMA_TENANT, CHROMA_DATABASE, and CHROMA_API_KEY."
            ) from exc
        except ChromaError as exc:
            raise ExternalServiceError(f"Chroma collection request failed: {exc}") from exc

    def add_chunks(
        self,
        collection_name: str,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        collection = self.get_or_create_document_collection(collection_name)
        try:
            collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
        except ChromaError as exc:
            raise ExternalServiceError(f"Chroma vector insert failed: {exc}") from exc

    def query_chunks(
        self,
        collection_name: str,
        query_embedding: list[float],
        result_count: int,
    ) -> dict[str, Any]:
        try:
            collection = self.client.get_collection(name=collection_name)
            return collection.query(
                query_embeddings=[query_embedding],
                n_results=result_count,
                include=["documents", "metadatas", "distances"],
            )
        except NotFoundError as exc:
            raise LookupError("No indexed chunks found for this document.") from exc
        except ChromaError as exc:
            raise ExternalServiceError(f"Chroma vector query failed: {exc}") from exc

    def delete_collection_if_exists(self, collection_name: str) -> None:
        try:
            self.client.delete_collection(name=collection_name)
        except (ChromaError, ValueError):
            # Chroma raises if the collection is already absent. Cleanup is a
            # best-effort compensation path, so absence is not an application
            # error.
            return
