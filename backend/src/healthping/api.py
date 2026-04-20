"""HTTP API exposing the current monitor state."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from healthping.models import CheckResult
from healthping.state import MonitorState


class StatusResponse(BaseModel):
    """Payload returned by GET /api/status."""

    started_at: datetime
    now: datetime
    endpoints: list[CheckResult]


class HealthResponse(BaseModel):
    """Payload returned by GET /api/health."""

    status: str


def create_app(state: MonitorState, allowed_origins: list[str]) -> FastAPI:
    """Build a FastAPI app backed by a shared MonitorState.

    Args:
        state: The MonitorState instance the monitor writes into.
        allowed_origins: CORS origins permitted to call the API. Use
            ["*"] only for public read-only deployments.
    """
    app = FastAPI(
        title="healthping API",
        description="Read-only status API for the healthping monitor.",
        version="0.1.5",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET"],
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

    return app
