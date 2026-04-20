"""Webhook alert dispatching."""

import httpx
import structlog

from healthping.models import AlertPlatform, CheckResult, CheckStatus

log = structlog.get_logger()


def _build_payload(
    platform: AlertPlatform,
    previous: CheckStatus,
    current: CheckResult,
) -> dict[str, str]:
    """Build a platform-specific webhook payload."""
    emoji = "🔴" if current.status == CheckStatus.DOWN else "🟢"
    transition = f"{previous.value.upper()} → {current.status.value.upper()}"

    lines = [
        f"{emoji} **{current.endpoint_name}** {transition}",
        f"URL: `{current.url}`",
    ]
    if current.error:
        lines.append(f"Error: `{current.error}`")
    if current.response_time_ms is not None:
        lines.append(f"Response time: `{current.response_time_ms}ms`")

    message = "\n".join(lines)

    if platform == AlertPlatform.DISCORD:
        return {"content": message}
    return {"text": message}


async def send_alert(
    client: httpx.AsyncClient,
    webhook_url: str,
    platform: AlertPlatform,
    previous: CheckStatus,
    current: CheckResult,
) -> None:
    """Send a webhook alert about a status transition.

    Args:
        client: Shared httpx async client.
        webhook_url: Target webhook URL.
        platform: Which platform format to use (Slack or Discord).
        previous: The previous known status of the endpoint.
        current: The latest check result triggering this alert.

    Never raises. Failures are logged, not propagated — a broken alerting
    channel should not bring down the monitor itself.
    """
    payload = _build_payload(platform, previous, current)

    try:
        response = await client.post(webhook_url, json=payload, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning(
            "alert_delivery_failed",
            endpoint=current.endpoint_name,
            error=str(exc),
        )
