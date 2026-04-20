"""Smoke tests for core modules."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from pydantic import HttpUrl

from healthping.config import ConfigError, load_config
from healthping.models import AppConfig, CheckStatus, EndpointConfig
from healthping.monitor import check_endpoint


def test_load_config_valid(tmp_path: Path) -> None:
    """A well-formed YAML config loads into an AppConfig."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
        endpoints:
          - name: example
            url: https://example.com
            interval_seconds: 30
        """
    )

    config = load_config(config_file)

    assert isinstance(config, AppConfig)
    assert len(config.endpoints) == 1
    assert config.endpoints[0].name == "example"


def test_load_config_missing_file(tmp_path: Path) -> None:
    """A missing config file raises ConfigError."""
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "does_not_exist.yaml")


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    """Malformed YAML raises ConfigError."""
    config_file = tmp_path / "bad.yaml"
    config_file.write_text("endpoints: [unterminated")

    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_config(config_file)


def test_load_config_missing_endpoints(tmp_path: Path) -> None:
    """A config without endpoints raises ConfigError."""
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("alerts: {}")

    with pytest.raises(ConfigError):
        load_config(config_file)


@pytest.mark.asyncio
async def test_check_endpoint_success() -> None:
    """A 200 response produces an UP result with response time."""
    endpoint = EndpointConfig(
        name="mock",
        url=HttpUrl("http://mock.test/"),
        timeout_seconds=5.0,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await check_endpoint(client, endpoint)

    assert result.status == CheckStatus.UP
    assert result.http_status == 200
    assert result.response_time_ms is not None
    assert result.response_time_ms >= 0
    assert isinstance(result.timestamp, datetime)
    assert result.timestamp.tzinfo == UTC


@pytest.mark.asyncio
async def test_check_endpoint_unexpected_status() -> None:
    """A non-expected status produces a DOWN result."""
    endpoint = EndpointConfig(
        name="mock",
        url=HttpUrl("http://mock.test/"),
        expected_status=200,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await check_endpoint(client, endpoint)

    assert result.status == CheckStatus.DOWN
    assert result.http_status == 500
    assert result.error is not None
    assert "Expected HTTP 200" in result.error


@pytest.mark.asyncio
async def test_check_endpoint_timeout() -> None:
    """A timeout produces a DOWN result with timeout error message."""
    endpoint = EndpointConfig(
        name="mock",
        url=HttpUrl("http://mock.test/"),
        timeout_seconds=0.1,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await check_endpoint(client, endpoint)

    assert result.status == CheckStatus.DOWN
    assert result.error is not None
    assert "Timeout" in result.error
