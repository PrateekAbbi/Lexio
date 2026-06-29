"""Authentication helpers for Supabase bearer tokens."""

from __future__ import annotations

import asyncio
from typing import Any

from app.clients.supabase import get_supabase_client


class InvalidSessionError(PermissionError):
    """Raised when a Supabase access token is missing, invalid, or expired."""


def read_attr(value: Any, name: str) -> Any:
    """Read attributes from SDK objects and dictionaries uniformly."""

    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


async def get_user_from_bearer_token(authorization: str) -> Any:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise InvalidSessionError("Missing or invalid Authorization header.")

    try:
        response = await asyncio.to_thread(get_supabase_client().auth.get_user, token)
    except Exception as exc:
        raise InvalidSessionError("Invalid or expired Supabase session.") from exc

    user = read_attr(response, "user")
    if not user or not read_attr(user, "id"):
        raise InvalidSessionError("Invalid or expired Supabase session.")

    return user


def get_user_id(user: Any) -> str:
    user_id = read_attr(user, "id")
    if not user_id:
        raise InvalidSessionError("Invalid Supabase user.")
    return str(user_id)

