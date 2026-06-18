"""Integration test: services with the full sample dataset."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.db.seed.importer import import_dataset
from app.services.container import ServiceContainer
from app.services.types import SearchMode

SAMPLE_DIR = Path("D:/project/PSR-SRS-Enterprise/data/sample")


@pytest.fixture(scope="module")
def _sample_db_session_factory():
    """Module-scoped: create DB, import sample, return session factory."""
    import os
    import tempfile

    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    from app.db.base import Base

    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_sample_svc_")
    os.close(fd)
    db_url = f"sqlite:///{path}"
    os.environ["DATABASE_URL"] = db_url

    engine = create_engine(db_url, echo=False)
    @event.listens_for(engine, "connect")
    def _pragma(dbapi_conn, rec):  # noqa: ARG001
        dbapi_conn.cursor().execute("PRAGMA foreign_keys = ON").close()
    Base.metadata.create_all(engine)

    import app.db.session as sm
    sm._engine = engine
    sm._SessionLocal = None

    factory = sessionmaker(bind=engine)

    # Import sample
    import_dataset(factory, SAMPLE_DIR)

    yield factory
    engine.dispose()
    sm._engine = None
    sm._SessionLocal = None
    for s in ("", "-journal", "-wal", "-shm"):
        p = Path(f"{path}{s}")
        if p.exists():
            p.unlink()


@pytest.fixture
def container(_sample_db_session_factory):
    c = ServiceContainer(_sample_db_session_factory)
    c.initialize()
    return c


class TestServicesWithSampleDB:
    def test_item_count(self, container):
        assert container.index_manager.get_status().item_count == 500

    def test_bm25_search(self, container):
        resp = container.search_service.search("electronics", mode=SearchMode.BM25, top_k=5)
        assert len(resp.hits) > 0

    def test_semantic_search(self, container):
        resp = container.search_service.search("laptop", mode=SearchMode.SEMANTIC, top_k=5)
        assert len(resp.hits) > 0

    def test_rrf_search(self, container):
        resp = container.search_service.search("computer", mode=SearchMode.RRF, top_k=5)
        assert len(resp.hits) > 0

    def test_linear_search(self, container):
        resp = container.search_service.search("gaming", mode=SearchMode.LINEAR, top_k=5)
        assert len(resp.hits) > 0

    def test_personalized_search(self, container):
        resp = container.search_service.search(
            "electronics", mode=SearchMode.LINEAR, top_k=5,
            user_id="user_000001", personalize=True,
        )
        assert len(resp.hits) > 0

    def test_cold_start_or_unknown_fallback(self, container):
        # Use a non-existent user to trigger fallback
        resp = container.search_service.search(
            "electronics", mode=SearchMode.LINEAR, top_k=5,
            user_id="nonexistent_user_999", personalize=True,
        )
        assert not resp.personalized
        assert resp.fallback_reason is not None

    def test_evaluation(self, container):
        report = container.evaluation_service.evaluate_queries(["query_000001", "query_000002"])
        assert report.query_count == 2

    def test_shutdown(self, container):
        container.shutdown()
