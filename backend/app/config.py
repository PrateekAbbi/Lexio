"""Centralized runtime configuration.

Keeping all environment reads in one module gives the rest of the backend a
stable, typed object instead of scattering ``os.getenv`` calls through route
handlers and service code.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv

from app.exceptions import ConfigurationError


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    """Configuration values used by the backend.

    Defaults preserve the existing local developer setup. Values that are
    required for live requests are validated by the client/service that needs
    them so the app can still import for tooling and health checks.
    """

    app_name: str = "Legal Document Intake Pipeline"
    app_description: str = "PDF ingestion, vector search, and cited legal Q&A demo."
    app_version: str = "1.0.0"
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")

    openai_api_key: str | None = None
    openai_embedding_url: str = "https://api.openai.com/v1/embeddings"
    openai_chat_url: str = "https://api.openai.com/v1/chat/completions"
    embedding_model: str | None = None
    answer_model: str | None = None
    embedding_batch_size: int = 20

    supabase_url: str | None = None
    supabase_service_role_key: str | None = None

    chunk_token_target: int = 500
    chunk_token_overlap: int = 50
    retrieval_result_count: int = 5
    chroma_mode: str = "local"
    chroma_path: Path = BASE_DIR / "chroma_store"
    chroma_tenant: str | None = None
    chroma_database: str | None = None
    chroma_api_key: str | None = None
    chroma_cloud_host: str = "api.trychroma.com"
    chroma_cloud_port: int = 443
    chroma_cloud_ssl: bool = True

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
            embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL"),
            answer_model=os.getenv("OPENAI_ANSWER_MODEL"),
            chroma_mode=os.getenv("CHROMA_MODE", "local").strip().lower(),
            chroma_path=_parse_path(os.getenv("CHROMA_PATH"), default=BASE_DIR / "chroma_store"),
            chroma_tenant=os.getenv("CHROMA_TENANT"),
            chroma_database=os.getenv("CHROMA_DATABASE"),
            chroma_api_key=os.getenv("CHROMA_API_KEY"),
            chroma_cloud_host=os.getenv("CHROMA_CLOUD_HOST", "api.trychroma.com"),
            chroma_cloud_port=int(os.getenv("CHROMA_CLOUD_PORT", "443")),
            chroma_cloud_ssl=_parse_bool(os.getenv("CHROMA_CLOUD_SSL"), default=True),
        )

    def require_openai_api_key(self) -> str:
        if not self.openai_api_key:
            raise ConfigurationError("OPENAI_API_KEY is not configured.")
        return self.openai_api_key

    def require_embedding_model(self) -> str:
        if not self.embedding_model:
            raise ConfigurationError("OPENAI_EMBEDDING_MODEL is not configured.")
        return self.embedding_model

    def require_answer_model(self) -> str:
        if not self.answer_model:
            raise ConfigurationError("OPENAI_ANSWER_MODEL is not configured.")
        return self.answer_model

    def require_supabase_credentials(self) -> tuple[str, str]:
        if not self.supabase_url or not self.supabase_service_role_key:
            raise ConfigurationError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")
        return self.supabase_url, self.supabase_service_role_key

    def require_chroma_cloud_credentials(self) -> tuple[str, str, str]:
        if not self.chroma_tenant or not self.chroma_database or not self.chroma_api_key:
            raise ConfigurationError(
                "CHROMA_TENANT, CHROMA_DATABASE, and CHROMA_API_KEY are required when CHROMA_MODE=cloud."
            )
        return self.chroma_tenant, self.chroma_database, self.chroma_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_environment()


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_path(value: str | None, *, default: Path) -> Path:
    if not value:
        return default
    path = Path(value)
    if path.is_absolute():
        return path
    return BASE_DIR / path
