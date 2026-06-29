"""FastAPI dependencies shared by route modules."""

from __future__ import annotations

from typing import Any

from fastapi import Header, HTTPException

from app.services.auth import InvalidSessionError, get_user_from_bearer_token


async def get_current_user(authorization: str = Header(...)) -> Any:
    try:
        return await get_user_from_bearer_token(authorization)
    except InvalidSessionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

