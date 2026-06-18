"""Shared test fixtures for the backend test suite."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base


@pytest.fixture
def temp_db_path():
    """Return a temp-file path for SQLite and clean up afterwards."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_psr_srs_")
    os.close(fd)
    yield path
    for suffix in ("", "-journal", "-wal", "-shm"):
        p = Path(f"{path}{suffix}")
        if p.exists():
            p.unlink()


@pytest.fixture
def db_session_factory(temp_db_path):
    """Create a session factory connected to a temp SQLite database
    with foreign keys enabled and all tables created."""
    db_url = f"sqlite:///{temp_db_path}"
    os.environ["DATABASE_URL"] = db_url

    engine = create_engine(db_url, echo=False)

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    Base.metadata.create_all(engine)

    import app.db.session as sess_mod
    sess_mod._engine = None
    sess_mod._SessionLocal = None

    factory = sessionmaker(bind=engine)
    yield factory
    engine.dispose()
    sess_mod._engine = None
    sess_mod._SessionLocal = None


@pytest.fixture
def db_session(db_session_factory) -> Session:
    """A single-use database session (data rolled back after test)."""
    session = db_session_factory()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(temp_db_path):
    """Create a FastAPI TestClient backed by a temp DB with tables."""
    os.environ["DATABASE_URL"] = f"sqlite:///{temp_db_path}"
    os.environ["APP_ENV"] = "testing"
    # Disable startup builds for test speed
    os.environ["SERVICE_INDEX_BUILD_ON_STARTUP"] = "false"
    os.environ["SERVICE_PROFILE_BUILD_ON_STARTUP"] = "false"

    # Create tables in temp DB
    engine = create_engine(f"sqlite:///{temp_db_path}", echo=False)

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    Base.metadata.create_all(engine)
    engine.dispose()

    import app.db.session as sess_mod
    sess_mod._engine = None
    sess_mod._SessionLocal = None

    from app.main import create_app

    app = create_app()
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def client_with_data():
    """Module-scoped TestClient with sample data imported and services built."""
    import os
    import tempfile
    from pathlib import Path

    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_api_data_")
    os.close(fd)
    db_url = f"sqlite:///{path}"
    os.environ["DATABASE_URL"] = db_url
    os.environ["APP_ENV"] = "testing"

    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    from app.db.base import Base

    engine = create_engine(db_url, echo=False)
    @event.listens_for(engine, "connect")
    def _pragma(c, r): c.cursor().execute("PRAGMA foreign_keys = ON").close()  # noqa: ARG001
    Base.metadata.create_all(engine)

    import app.db.session as sm
    sm._engine = engine
    sm._SessionLocal = None

    factory = sessionmaker(bind=engine)

    # Import sample
    from app.db.seed.importer import import_dataset
    from tests.path_helpers import SAMPLE_DIR
    import_dataset(factory, SAMPLE_DIR)

    from app.main import create_app
    app = create_app()
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c

    c.app.state.service_container.shutdown()
    engine.dispose()
    sm._engine = None
    sm._SessionLocal = None
    import time
    for s in ("", "-journal", "-wal", "-shm"):
        p = Path(f"{path}{s}")
        for _ in range(5):
            try:
                if p.exists():
                    p.unlink()
                break
            except PermissionError:
                time.sleep(0.1)

