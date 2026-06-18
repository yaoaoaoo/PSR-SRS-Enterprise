"""Tests for application configuration."""

from __future__ import annotations

import pytest


# Prevent .env file from being loaded during config tests
@pytest.fixture(autouse=True)
def block_env_file(monkeypatch):
    """Prevent pydantic-settings from searching for .env files."""
    monkeypatch.setenv("APP_ENV", "testing")


class TestSettingsDefaults:
    """Verify that default values are sensible."""

    def test_default_app_name(self):
        from app.core.config import Settings

        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.APP_NAME == "PSR-SRS Enterprise"

    def test_default_api_prefix(self):
        from app.core.config import Settings

        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.API_V1_PREFIX == "/api/v1"

    def test_default_app_version(self):
        from app.core.config import Settings

        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.APP_VERSION == "0.1.0"

    def test_default_log_level(self):
        from app.core.config import Settings

        s = Settings(_env_file=None)  # type: ignore[call-arg]
        assert s.LOG_LEVEL == "INFO"

    def test_development_flag(self):
        from app.core.config import Settings

        s = Settings(_env_file=None, APP_ENV="development")  # type: ignore[call-arg]
        assert s.is_development is True

    def test_production_flag(self):
        from app.core.config import Settings

        s = Settings(_env_file=None, APP_ENV="production")  # type: ignore[call-arg]
        assert s.is_development is False

    def test_cors_origins_list_multiple(self):
        from app.core.config import Settings

        s = Settings(
            _env_file=None,  # type: ignore[call-arg]
            CORS_ORIGINS="http://localhost:5173,http://localhost:3000",
        )
        assert len(s.cors_origins_list) == 2
        assert "http://localhost:5173" in s.cors_origins_list
        assert "http://localhost:3000" in s.cors_origins_list

    def test_single_cors_origin(self):
        from app.core.config import Settings

        s = Settings(_env_file=None, CORS_ORIGINS="http://localhost:5173")  # type: ignore[call-arg]
        assert s.cors_origins_list == ["http://localhost:5173"]


class TestSettingsFromEnv:
    """Verify that env vars override defaults."""

    def test_override_from_env(self):
        from app.core.config import Settings

        s = Settings(_env_file=None, APP_NAME="TestApp", APP_VERSION="9.9.9")  # type: ignore[call-arg]
        assert s.APP_NAME == "TestApp"
        assert s.APP_VERSION == "9.9.9"

    def test_database_url_override(self):
        from app.core.config import Settings

        s = Settings(_env_file=None, DATABASE_URL="sqlite:///./data/test_custom.db")  # type: ignore[call-arg]
        assert "test_custom.db" in s.DATABASE_URL
