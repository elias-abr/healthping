"""Tests for MonitorState."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from healthping.models import CheckResult, CheckStatus
from healthping.state import MonitorState


def _make_result(
    name: str, status: CheckStatus, timestamp: datetime | None = None
) -> CheckResult:
    return CheckResult(
        endpoint_name=name,
        url="https://example.com/",
        status=status,
        response_time_ms=100.0,
        http_status=200 if status == CheckStatus.UP else 500,
        error=None if status == CheckStatus.UP else "boom",
        timestamp=timestamp or datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_record_returns_none_for_first_observation() -> None:
    """The first recorded result has no previous status."""
    state = MonitorState()
    result = _make_result("api", CheckStatus.UP)

    previous = await state.record(result)

    assert previous is None


@pytest.mark.asyncio
async def test_record_returns_previous_status_on_subsequent_calls() -> None:
    """The second record returns the first status."""
    state = MonitorState()
    first = _make_result("api", CheckStatus.UP)
    second = _make_result("api", CheckStatus.DOWN)

    await state.record(first)
    previous = await state.record(second)

    assert previous == CheckStatus.UP


@pytest.mark.asyncio
async def test_snapshot_returns_latest_results_only() -> None:
    """Snapshot reflects the most recent result per endpoint."""
    state = MonitorState()
    await state.record(_make_result("api", CheckStatus.UP))
    await state.record(_make_result("api", CheckStatus.DOWN))
    await state.record(_make_result("other", CheckStatus.UP))

    snapshot = state.snapshot()

    assert len(snapshot) == 2
    by_name = {r.endpoint_name: r for r in snapshot}
    assert by_name["api"].status == CheckStatus.DOWN
    assert by_name["other"].status == CheckStatus.UP


@pytest.mark.asyncio
async def test_snapshot_is_empty_before_any_records() -> None:
    """Fresh state has no endpoints in its snapshot."""
    state = MonitorState()

    assert state.snapshot() == []


def test_started_at_is_set_at_construction() -> None:
    """started_at is a UTC timestamp fixed at construction time."""
    state = MonitorState()

    assert isinstance(state.started_at, datetime)
    assert state.started_at.tzinfo == UTC
