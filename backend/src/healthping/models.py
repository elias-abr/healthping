"""Domain models for healthping."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


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
    json_status_path: str | None = None
    json_expected_values: list[str] | None = None

    @model_validator(mode="after")
    def _json_fields_both_or_neither(self) -> "EndpointConfig":
        path_set = self.json_status_path is not None
        values_set = self.json_expected_values is not None
        if path_set != values_set:
            raise ValueError(
                "json_status_path and json_expected_values must both be set or both be None"
            )
        return self


class AlertPlatform(StrEnum):
    """Webhook target platform."""

    SLACK = "slack"
    DISCORD = "discord"


class AlertConfig(BaseModel):
    """Configuration for webhook alerts."""

    webhook_url: HttpUrl | None = None
    platform: AlertPlatform = AlertPlatform.SLACK


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
