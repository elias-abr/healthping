"""HTTP API exposing the current monitor state."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from healthping.auth.dependencies import make_get_current_user
from healthping.auth.routes import create_auth_router
from healthping.models import CheckResult
from healthping.settings import Settings
from healthping.state import MonitorState


class StatusResponse(BaseModel):
    """Payload returned by GET /api/status."""

    started_at: datetime
    now: datetime
    endpoints: list[CheckResult]


class HealthResponse(BaseModel):
    """Payload returned by GET /api/health."""

    status: str


def create_app(
    state: MonitorState,
    allowed_origins: list[str],
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Build a FastAPI app backed by a shared MonitorState.

    Args:
        state: The MonitorState instance the monitor writes into.
        allowed_origins: CORS origins permitted to call the API.
        session_factory: Async SQLAlchemy session factory (required for auth).
        settings: App settings (required for auth).
    """
    app = FastAPI(
        title="healthping API",
        description="Status and auth API for the healthping monitor.",
        version="0.2.1",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse, tags=["meta"])
    async def health() -> HealthResponse:  # pyright: ignore[reportUnusedFunction]
        """Liveness check for the API itself."""
        return HealthResponse(status="ok")

    @app.get("/api/status", response_model=StatusResponse, tags=["monitor"])
    async def status() -> StatusResponse:  # pyright: ignore[reportUnusedFunction]
        """Return the latest known check result for every endpoint."""
        return StatusResponse(
            started_at=state.started_at,
            now=datetime.now(UTC),
            endpoints=state.snapshot(),
        )

    if session_factory is not None and settings is not None:
        get_current_user = make_get_current_user(session_factory, settings)
        auth_router = create_auth_router(session_factory, settings, get_current_user)  # type: ignore[arg-type]
        app.include_router(auth_router)

    return app
