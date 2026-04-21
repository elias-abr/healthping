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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from healthping.alerts import send_alert
from healthping.config import ConfigError, load_config
from healthping.db.base import build_engine_and_factory
from healthping.models import AppConfig, CheckResult, CheckStatus, EndpointConfig
from healthping.monitor import check_endpoint
from healthping.settings import Settings
from healthping.state import MonitorState


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
        sys.stdout = _Tee(sys.stdout, log_file.open("a", encoding="utf-8"))


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
    state: MonitorState,
    stop_event: asyncio.Event,
) -> None:
    """Run an indefinite check loop for one endpoint."""
    log = structlog.get_logger()

    while not stop_event.is_set():
        result = await check_endpoint(client, endpoint)
        _emit_result(log, result)

        previous = await state.record(result)

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

        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=endpoint.interval_seconds)


def _emit_result(log: structlog.stdlib.BoundLogger, result: CheckResult) -> None:
    """Log a single check result as structured JSON."""
    payload = json.loads(result.model_dump_json())
    log.info("check_result", **payload)


async def run_monitor(
    config: AppConfig, state: MonitorState, stop_event: asyncio.Event
) -> None:
    """Start concurrent check loops for all configured endpoints."""
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


async def _main_async(config: AppConfig) -> None:
    """Main entry: run the monitor until signalled to stop."""
    state = MonitorState()
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await run_monitor(config, state, stop_event)


def _run_migrations_sync(db_path: str) -> None:
    """Apply pending Alembic migrations synchronously before the event loop starts."""
    import os
    from pathlib import Path as _Path

    from alembic import command
    from alembic.config import Config as AlembicConfig

    # Ensure the DB directory exists (SQLite can create the file but not its parent dir)
    db_file = _Path(db_path)
    if not db_file.is_absolute() or db_path != ":memory:":
        db_file.parent.mkdir(parents=True, exist_ok=True)

    # Locate alembic.ini — cwd works in Docker (/app) and in dev (backend/)
    here = _Path(__file__).resolve().parent
    candidates = [
        _Path.cwd() / "alembic.ini",
        here.parent.parent.parent / "alembic.ini",  # dev: backend/src/healthping → backend/
    ]
    ini_path = next((p for p in candidates if p.exists()), None)
    if ini_path is None:
        raise RuntimeError(
            "alembic.ini not found; expected alongside migrations/ directory"
        )

    os.environ.setdefault("HEALTHPING_DB_PATH", db_path)
    alembic_cfg = AlembicConfig(str(ini_path))
    command.upgrade(alembic_cfg, "head")


async def _serve_async(
    config: AppConfig,
    host: str,
    port: int,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Run the monitor and HTTP API concurrently in one process."""
    import uvicorn

    from healthping.api import create_app

    state = MonitorState()
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    app = create_app(
        state,
        allowed_origins=settings.allowed_origins,
        session_factory=session_factory,
        settings=settings,
    )
    uvicorn_config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",  # don't fight with our structlog output
        access_log=False,
    )
    server = uvicorn.Server(uvicorn_config)

    monitor_task = asyncio.create_task(run_monitor(config, state, stop_event))
    server_task = asyncio.create_task(server.serve())

    await stop_event.wait()
    server.should_exit = True
    await asyncio.gather(monitor_task, server_task, return_exceptions=True)


@click.group()
def main() -> None:
    """healthping — a lightweight async HTTP health monitor."""


@main.command()
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
def monitor(config_path: Path, log_file: Path | None) -> None:
    """Run the monitor only (alerts + logs, no HTTP API)."""
    _configure_logging(log_file)

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(1)

    with suppress(KeyboardInterrupt):
        asyncio.run(_main_async(config))


@main.command()
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
@click.option(
    "--host",
    default="0.0.0.0",
    show_default=True,
    help="HTTP API bind host.",
)
@click.option(
    "--port",
    default=8000,
    show_default=True,
    type=int,
    help="HTTP API bind port.",
)
def serve(
    config_path: Path,
    log_file: Path | None,
    host: str,
    port: int,
) -> None:
    """Run the monitor and the HTTP API together."""
    _configure_logging(log_file)

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(1)

    try:
        settings = Settings()  # type: ignore[call-arg]
    except Exception as exc:
        click.echo(f"Configuration error: {exc}", err=True)
        sys.exit(1)

    try:
        _run_migrations_sync(settings.db_path)
    except Exception as exc:
        click.echo(f"Migration error: {exc}", err=True)
        sys.exit(1)

    _engine, session_factory = build_engine_and_factory(settings.db_path)

    with suppress(KeyboardInterrupt):
        asyncio.run(_serve_async(config, host, port, session_factory, settings))


if __name__ == "__main__":
    main()
