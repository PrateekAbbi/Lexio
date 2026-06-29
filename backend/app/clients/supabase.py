"""Supabase service-role client factory."""

from functools import lru_cache
from typing import Any

from supabase import create_client

from app.config import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Any:
    """Create the service-role Supabase client once per process."""

    url, service_role_key = get_settings().require_supabase_credentials()
    return create_client(url, service_role_key)

