"""Domain models for healthping."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class CheckStatus(StrEnum):
    """Result of a single health check."""

    UP = "up"
    DOWN = "down"


class EndpointConfig(BaseModel):
    """User-defined configuration for a single endpoint."""

    name: str = Field(..., min_length=1, max_length=100)
    url: HttpUrl
    method: Literal["GET", "POST", "HEAD"] = "GET"
    timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    expected_status: int = Field(default=200, ge=100, le=599)
    interval_seconds: int = Field(default=30, ge=5)


class AlertConfig(BaseModel):
    """Configuration for webhook alerts."""

    webhook_url: HttpUrl | None = None


class AppConfig(BaseModel):
    """Root configuration loaded from YAML."""

    endpoints: list[EndpointConfig] = Field(..., min_length=1)
    alerts: AlertConfig = Field(default_factory=AlertConfig)


class CheckResult(BaseModel):
    """The result of a single health check at a point in time."""

    endpoint_name: str
    url: str
    status: CheckStatus
    response_time_ms: float | None = None
    http_status: int | None = None
    error: str | None = None
    timestamp: datetime
