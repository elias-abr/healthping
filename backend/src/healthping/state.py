"""Shared in-memory state for the monitor and HTTP API."""

from __future__ import annotations

from asyncio import Lock
from datetime import UTC, datetime

from healthping.models import CheckResult, CheckStatus


class MonitorState:
    """Thread/async-safe store for the latest check result per endpoint.

    The monitor writes here after every check. The HTTP API reads from
    here to serve the dashboard. An asyncio.Lock guards writes to keep
    readers from seeing torn state mid-update.
    """

    def __init__(self) -> None:
        self._results: dict[str, CheckResult] = {}
        self._statuses: dict[str, CheckStatus] = {}
        self._lock = Lock()
        self._started_at = datetime.now(UTC)

    @property
    def started_at(self) -> datetime:
        return self._started_at

    async def record(self, result: CheckResult) -> CheckStatus | None:
        """Record a new check result. Returns the previous status if any."""
        async with self._lock:
            previous = self._statuses.get(result.endpoint_name)
            self._results[result.endpoint_name] = result
            self._statuses[result.endpoint_name] = result.status
            return previous

    def snapshot(self) -> list[CheckResult]:
        """Return the latest result for every known endpoint."""
        return list(self._results.values())
