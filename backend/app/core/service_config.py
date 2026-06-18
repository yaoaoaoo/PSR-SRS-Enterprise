"""Service-layer configuration with sensible defaults for a 500-item dataset."""

from __future__ import annotations

from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    """Typed service-layer config — separate from core app config."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="SERVICE_",
    )

    # Search defaults
    SEARCH_DEFAULT_MODE: str = "linear"
    SEARCH_DEFAULT_TOP_K: int = 10
    SEARCH_MAX_TOP_K: int = 100
    SEARCH_CANDIDATE_MULTIPLIER: int = 5
    SEARCH_MIN_CANDIDATES: int = 50
    SEARCH_STRICT_PERSONALIZATION: bool = False

    # Index / profile build on startup
    INDEX_BUILD_ON_STARTUP: bool = True
    PROFILE_BUILD_ON_STARTUP: bool = True
    INDEX_ALLOW_EMPTY: bool = True
    PROFILE_ALLOW_EMPTY: bool = True


# Module-level singleton
service_settings = ServiceSettings()
