"""Tests for database URL resolution."""

from __future__ import annotations

from app.core.config import _resolve_db_url


class TestDatabaseURL:
    def test_relative_sqlite_resolves_to_absolute(self):
        url = _resolve_db_url("sqlite:///./data/test.db")
        assert "sqlite:///" in url
        assert url.endswith("data/test.db")
        # Should be absolute — no '.' in path after resolution
        path_part = url[len("sqlite:///"):]
        assert "." not in path_part.split("/")[-3:]

    def test_absolute_sqlite_unchanged(self):
        # On Windows, sqlite:////absolute/path gets resolved as a Path
        # which may prepend the drive letter. Either the original or
        # resolved form is acceptable for absolute paths.
        url = _resolve_db_url("sqlite:////absolute/path/db.db")
        assert "/absolute/path/db.db" in url
        assert url.startswith("sqlite:///")

    def test_postgresql_unchanged(self):
        url = _resolve_db_url("postgresql://user:pass@localhost/db")
        assert url == "postgresql://user:pass@localhost/db"

    def test_memory_sqlite_unchanged(self):
        resolved = _resolve_db_url("sqlite:///:memory:")
        assert ":memory:" in resolved

    def test_non_sqlite_unchanged(self):
        url = _resolve_db_url("mysql://localhost/test")
        assert url == "mysql://localhost/test"
