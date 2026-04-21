"""Async HTTP health checker."""

from datetime import UTC, datetime
from typing import Any

import httpx

from healthping.models import CheckResult, CheckStatus, EndpointConfig


def _traverse_path(data: Any, path: str) -> str | None:
    """Walk a dot-separated path through a parsed JSON dict.

    Returns the string value at the leaf, or None if any step fails
    (missing key, non-dict intermediate, non-string leaf).
    """
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, str) else None


async def check_endpoint(
    client: httpx.AsyncClient,
    endpoint: EndpointConfig,
) -> CheckResult:
    """Perform a single health check against one endpoint.

    Args:
        client: Shared httpx async client.
        endpoint: Endpoint configuration to check.

    Returns:
        CheckResult describing the outcome. Never raises — any failure
        (timeout, DNS, connection refused, unexpected status) becomes
        a DOWN result with an explanatory error message.
    """
    started_at = datetime.now(UTC)

    try:
        response = await client.request(
            method=endpoint.method,
            url=str(endpoint.url),
            timeout=endpoint.timeout_seconds,
            follow_redirects=True,
        )
    except httpx.TimeoutException:
        return CheckResult(
            endpoint_name=endpoint.name,
            url=str(endpoint.url),
            status=CheckStatus.DOWN,
            error=f"Timeout after {endpoint.timeout_seconds}s",
            timestamp=started_at,
        )
    except httpx.HTTPError as exc:
        return CheckResult(
            endpoint_name=endpoint.name,
            url=str(endpoint.url),
            status=CheckStatus.DOWN,
            error=f"{type(exc).__name__}: {exc}",
            timestamp=started_at,
        )

    elapsed_ms = (datetime.now(UTC) - started_at).total_seconds() * 1000

    if response.status_code != endpoint.expected_status:
        return CheckResult(
            endpoint_name=endpoint.name,
            url=str(endpoint.url),
            status=CheckStatus.DOWN,
            response_time_ms=round(elapsed_ms, 2),
            http_status=response.status_code,
            error=f"Expected HTTP {endpoint.expected_status}, got {response.status_code}",
            timestamp=started_at,
        )

    if (
        endpoint.json_status_path is not None
        and endpoint.json_expected_values is not None
    ):
        try:
            body = response.json()
        except Exception:
            return CheckResult(
                endpoint_name=endpoint.name,
                url=str(endpoint.url),
                status=CheckStatus.DOWN,
                response_time_ms=round(elapsed_ms, 2),
                http_status=response.status_code,
                error="Response body is not valid JSON",
                timestamp=started_at,
            )

        value = _traverse_path(body, endpoint.json_status_path)
        if value is None:
            return CheckResult(
                endpoint_name=endpoint.name,
                url=str(endpoint.url),
                status=CheckStatus.DOWN,
                response_time_ms=round(elapsed_ms, 2),
                http_status=response.status_code,
                error=f"JSON path '{endpoint.json_status_path}' not found or not a string",
                timestamp=started_at,
            )
        if value not in endpoint.json_expected_values:
            return CheckResult(
                endpoint_name=endpoint.name,
                url=str(endpoint.url),
                status=CheckStatus.DOWN,
                response_time_ms=round(elapsed_ms, 2),
                http_status=response.status_code,
                error=f"JSON status '{value}' not in expected values {endpoint.json_expected_values}",
                timestamp=started_at,
            )

    return CheckResult(
        endpoint_name=endpoint.name,
        url=str(endpoint.url),
        status=CheckStatus.UP,
        response_time_ms=round(elapsed_ms, 2),
        http_status=response.status_code,
        timestamp=started_at,
    )
