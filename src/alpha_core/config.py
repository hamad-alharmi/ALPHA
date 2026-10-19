"""Read only documented, non-secret settings from the environment."""

import os
from collections.abc import Mapping
from dataclasses import dataclass

from alpha_core.errors import ConfigurationError


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    log_level: str = "INFO"


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    source = os.environ if environ is None else environ
    environment = source.get("ALPHA_ENV", "development").strip().lower()
    level = source.get("ALPHA_LOG_LEVEL", "INFO").strip().upper()
    if environment not in {"development", "test", "production"}:
        raise ConfigurationError(
            "ALPHA_ENV must be development, test, or production"
        )
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfigurationError(
            "ALPHA_LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL"
        )
    return Settings(environment=environment, log_level=level)
