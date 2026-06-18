"""Database session management — SQLAlchemy 2.x engine and session factory.

The engine is lazily created so tests can override ``DATABASE_URL``
before the first connection.  SQLite pragmas (foreign keys, WAL, busy
timeout) are set automatically.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _create_engine() -> Engine:
    """Create a new SQLAlchemy engine from current settings."""
    url = settings.resolved_database_url
    connect_args: dict = {}

    if "sqlite" in url:
        connect_args["check_same_thread"] = False
        engine = create_engine(url, echo=False, connect_args=connect_args)

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, connection_record):  # noqa: ARG001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA busy_timeout = 5000")
            cursor.close()

        return engine

    return create_engine(url, echo=False)


def get_engine() -> Engine:
    """Return the SQLAlchemy engine, creating it lazily if needed."""
    global _engine
    if _engine is None:
        _engine = _create_engine()
        logger.info("Database engine created | url=%s", _engine.url)
    return _engine


def _get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            bind=get_engine(),
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a database session, closing it after use (FastAPI dependency).

    The session does NOT auto-commit.  The caller is responsible for
    committing or rolling back.
    """
    factory = _get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Verify the database is reachable by executing ``SELECT 1``."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database connection check failed")
        return False


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context-manager-style session that commits on success and rolls
    back on exception.

    Usage::

        with session_scope() as session:
            session.add(item)
    """
    factory = _get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
