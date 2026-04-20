"""Tests for the FastAPI app."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from healthping.api import create_app
from healthping.models import CheckResult, CheckStatus
from healthping.state import MonitorState


@pytest.fixture
def state() -> MonitorState:
    return MonitorState()


@pytest.fixture
def client(state: MonitorState) -> TestClient:
    app = create_app(state, allowed_origins=["*"])
    return TestClient(app)


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    """GET /api/health returns status ok."""
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_status_returns_empty_endpoints_before_any_checks(
    client: TestClient,
) -> None:
    """GET /api/status returns empty endpoints before any check is recorded."""
    response = client.get("/api/status")

    assert response.status_code == 200
    body = response.json()
    assert body["endpoints"] == []
    assert "started_at" in body
    assert "now" in body


@pytest.mark.asyncio
async def test_status_reflects_recorded_results(
    state: MonitorState, client: TestClient
) -> None:
    """GET /api/status returns the latest recorded results."""
    await state.record(
        CheckResult(
            endpoint_name="api",
            url="https://example.com/",
            status=CheckStatus.UP,
            response_time_ms=142.5,
            http_status=200,
            error=None,
            timestamp=datetime.now(UTC),
        )
    )

    response = client.get("/api/status")

    assert response.status_code == 200
    body = response.json()
    assert len(body["endpoints"]) == 1
    assert body["endpoints"][0]["endpoint_name"] == "api"
    assert body["endpoints"][0]["status"] == "up"
    assert body["endpoints"][0]["response_time_ms"] == 142.5
