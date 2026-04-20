"""Command-line interface for healthping."""

from __future__ import annotations

import asyncio
import json
import signal
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any

import click
import httpx
import structlog

from healthping.alerts import send_alert
from healthping.config import ConfigError, load_config
from healthping.models import AppConfig, CheckResult, CheckStatus, EndpointConfig
from healthping.monitor import check_endpoint


def _configure_logging(log_file: Path | None) -> None:
    """Configure structlog for console + optional JSON file output."""
    processors: list[Any] = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer(),
    ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
        cache_logger_on_first_use=True,
    )

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        # Tee stdout to a file as well.
        sys.stdout = _Tee(sys.stdout, log_file.open("a", encoding="utf-8"))  # type: ignore[assignment]


class _Tee:
    """Write to two streams at once (stdout + log file)."""

    def __init__(self, *streams: Any) -> None:
        self._streams = streams

    def write(self, data: str) -> int:
        for stream in self._streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()


async def _run_endpoint_loop(
    endpoint: EndpointConfig,
    client: httpx.AsyncClient,
    config: AppConfig,
    state: dict[str, CheckStatus],
    stop_event: asyncio.Event,
) -> None:
    """Run an indefinite check loop for one endpoint."""
    log = structlog.get_logger()

    while not stop_event.is_set():
        result = await check_endpoint(client, endpoint)
        _emit_result(log, result)

        previous = state.get(endpoint.name)
        should_alert = config.alerts.webhook_url is not None and (
            (previous is None and result.status == CheckStatus.DOWN)
            or (previous is not None and previous != result.status)
        )
        if should_alert and config.alerts.webhook_url is not None:
            await send_alert(
                client=client,
                webhook_url=str(config.alerts.webhook_url),
                platform=config.alerts.platform,
                previous=previous if previous is not None else CheckStatus.UP,
                current=result,
            )
        state[endpoint.name] = result.status

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=endpoint.interval_seconds)
        except TimeoutError:
            continue


def _emit_result(log: structlog.stdlib.BoundLogger, result: CheckResult) -> None:
    """Log a single check result as structured JSON."""
    payload = json.loads(result.model_dump_json())
    log.info("check_result", **payload)


async def _main_async(config: AppConfig) -> None:
    """Start concurrent check loops for all configured endpoints."""
    state: dict[str, CheckStatus] = {}
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    async with httpx.AsyncClient() as client:
        tasks = [
            asyncio.create_task(
                _run_endpoint_loop(endpoint, client, config, state, stop_event)
            )
            for endpoint in config.endpoints
        ]
        await stop_event.wait()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


@click.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the YAML config file.",
)
@click.option(
    "--log-file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Optional path to also write JSON logs to.",
)
def main(config_path: Path, log_file: Path | None) -> None:
    """healthping — a lightweight async HTTP health monitor."""
    _configure_logging(log_file)

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(1)

    with suppress(KeyboardInterrupt):
        asyncio.run(_main_async(config))


if __name__ == "__main__":
    main()
