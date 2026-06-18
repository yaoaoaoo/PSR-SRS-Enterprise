"""Tests for database session and connection."""

from __future__ import annotations


class TestDatabaseConnection:
    """Verify SQLite database connectivity."""

    def test_check_db_connection_succeeds(self, client):
        """With a temp SQLite database (set up by the client fixture),
        check_db_connection should return True."""
        # The client fixture already sets DATABASE_URL to a temp SQLite DB
        from app.db.session import check_db_connection

        result = check_db_connection()
        assert result is True

    def test_engine_creation(self, client):
        """Engine should be creatable and identify as sqlite."""
        from app.db.session import get_engine

        engine = get_engine()
        assert engine is not None
        assert "sqlite" in str(engine.url)

    def test_get_db_yields_session(self, client):
        """get_db should yield a valid SQLAlchemy session."""
        from sqlalchemy import text

        from app.db.session import get_db

        session = next(get_db())
        try:
            assert session is not None
            # Should be able to execute a simple query
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        finally:
            session.close()
