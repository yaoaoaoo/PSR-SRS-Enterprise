"""Application configuration loaded from environment variables and .env file.

Uses pydantic-settings for automatic .env loading and validation.
Relative SQLite paths are resolved against the project root directory
(``PSR-SRS-Enterprise/``), not the current working directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict

# _PROJECT_ROOT is derived from this file's location:
#   backend/app/core/config.py → backend/ → PSR-SRS-Enterprise/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_db_url(raw: str) -> str:
    """Resolve a relative SQLite path against the project root.

    ``sqlite:///./data/foo.db`` or ``sqlite:///../data/foo.db`` →
    ``sqlite:///<project_root>/data/foo.db``

    Absolute paths and non-SQLite URLs are returned unchanged.
    """
    if not raw.startswith("sqlite:///"):
        return raw

    # Strip the sqlite:/// prefix to get the path part
    path_part = raw[len("sqlite:///"):]

    # If it's already absolute (starts with / or drive letter), leave it
    p = Path(path_part)
    if p.is_absolute():
        return raw

    # Resolve relative to project root, then normalise
    resolved = (_PROJECT_ROOT / p).resolve()
    return f"sqlite:///{resolved.as_posix()}"


class Settings(BaseSettings):
    """Typed application settings with .env and env-var overrides."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "PSR-SRS Enterprise"
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # ---- Database ----
    # Relative paths (./data/...) are resolved against the project root.
    # Absolute paths and non-SQLite URLs are left as-is.
    # For in-memory SQLite use: sqlite:///:memory:
    DATABASE_URL: str = "sqlite:///./data/psr_srs_enterprise.db"

    # Resolved at access time so env-var overrides take effect
    @property
    def resolved_database_url(self) -> str:
        return _resolve_db_url(self.DATABASE_URL)

    # ---- Logging ----
    LOG_LEVEL: str = "INFO"

    # ---- CORS ----
    CORS_ORIGINS: str = "http://localhost:5173"

    # ---- Computed ----
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() in ("development", "dev", "local")

    @property
    def project_root(self) -> Path:
        return _PROJECT_ROOT


def get_settings() -> Settings:
    """Build settings from env vars and .env file."""
    return Settings()


# Module-level singleton — created once at import time.
settings = get_settings()
