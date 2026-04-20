"""YAML config loader."""

from pathlib import Path

import yaml

from healthping.models import AppConfig


class ConfigError(Exception):
    """Raised when a config file cannot be loaded or is invalid."""


def load_config(path: Path) -> AppConfig:
    """Load and validate a YAML config file.

    Args:
        path: Path to the YAML config file.

    Returns:
        Validated AppConfig instance.

    Raises:
        ConfigError: If the file doesn't exist, is unreadable, or invalid.
    """
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc}") from exc

    try:
        raw_data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw_data, dict):
        raise ConfigError(
            f"Config root must be a mapping, got {type(raw_data).__name__}"
        )

    try:
        return AppConfig.model_validate(raw_data)
    except ValueError as exc:
        raise ConfigError(f"Invalid config: {exc}") from exc
