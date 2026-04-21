"""SQLAlchemy engine, declarative base, and async session factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def build_engine_and_factory(
    db_path: str,
) -> tuple[object, async_sessionmaker[AsyncSession]]:
    """Create an async SQLAlchemy engine and session factory for the given DB path."""
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a single async DB session (for use in FastAPI dependencies)."""
    async with session_factory() as session:
        yield session
