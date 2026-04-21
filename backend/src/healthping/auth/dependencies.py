"""FastAPI dependencies for authentication."""

from __future__ import annotations

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from healthping.auth.tokens import decode_access_token
from healthping.db.models.user import User
from healthping.settings import Settings


def _extract_token(request: Request) -> str | None:
    """Pull JWT from cookie or Authorization header."""
    cookie = request.cookies.get("healthping_session")
    if cookie:
        return cookie
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer "):]
    return None


def make_get_current_user(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> object:
    async def get_current_user(request: Request) -> User:
        token = _extract_token(request)
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        payload = decode_access_token(token, settings.jwt_secret, settings.jwt_algorithm)
        if payload is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        user_id = payload.get("sub")
        if not isinstance(user_id, str):
            raise HTTPException(status_code=401, detail="Invalid token payload")
        async with session_factory() as session:
            user = await session.get(User, int(user_id))
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    return get_current_user


def make_get_optional_user(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> object:
    async def get_optional_user(request: Request) -> User | None:
        token = _extract_token(request)
        if not token:
            return None
        payload = decode_access_token(token, settings.jwt_secret, settings.jwt_algorithm)
        if payload is None:
            return None
        user_id = payload.get("sub")
        if not isinstance(user_id, str):
            return None
        async with session_factory() as session:
            return await session.get(User, int(user_id))

    return get_optional_user
