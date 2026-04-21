"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration read from environment variables."""

    jwt_secret: str  # required — startup fails loudly if missing
    db_path: str = "./healthping.db"
    jwt_algorithm: str = "HS256"
    jwt_expiry_days: int = 7
    allowed_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_prefix="HEALTHPING_")
