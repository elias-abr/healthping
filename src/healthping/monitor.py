"""Async HTTP health checker."""

from datetime import UTC, datetime

import httpx

from healthping.models import CheckResult, CheckStatus, EndpointConfig


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

    return CheckResult(
        endpoint_name=endpoint.name,
        url=str(endpoint.url),
        status=CheckStatus.UP,
        response_time_ms=round(elapsed_ms, 2),
        http_status=response.status_code,
        timestamp=started_at,
    )
