"""SearchService tests — all modes, validation, personalization path."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.item import Item
from app.services.container import ServiceContainer
from app.services.errors import InvalidSearchRequestError
from app.services.types import SearchMode


@pytest.fixture
def _search_data(db_session):
    for j in range(20):
        db_session.add(Item(
            item_id=f"i{j:03d}", title=f"Test Item {j}", description="desc",
            category="Electronics" if j % 2 == 0 else "Books",
            subcategory="Sub", brand="Brand", price=Decimal("10"),
            quality_score=0.5, popularity_score=0.5,
        ))
    db_session.commit()


@pytest.fixture
def container(db_session_factory, _search_data):
    c = ServiceContainer(db_session_factory)
    c.initialize()
    return c


class TestSearchValidation:
    def test_empty_query_rejected(self, container):
        with pytest.raises(InvalidSearchRequestError, match="empty"):
            container.search_service.search("")

    def test_whitespace_only_rejected(self, container):
        with pytest.raises(InvalidSearchRequestError):
            container.search_service.search("   ")

    def test_top_k_zero_rejected(self, container):
        with pytest.raises(InvalidSearchRequestError, match="top_k"):
            container.search_service.search("test", top_k=0)

    def test_top_k_negative_rejected(self, container):
        with pytest.raises(InvalidSearchRequestError, match="top_k"):
            container.search_service.search("test", top_k=-1)

    def test_personalize_requires_user_id(self, container):
        with pytest.raises(InvalidSearchRequestError, match="user_id"):
            container.search_service.search("test", personalize=True)


class TestSearchModes:
    def test_bm25_mode(self, container):
        resp = container.search_service.search("Test Item", mode=SearchMode.BM25, top_k=5)
        assert resp.mode == "bm25"
        assert len(resp.hits) > 0
        assert resp.hits[0].rank == 1

    def test_semantic_mode(self, container):
        resp = container.search_service.search("Test", mode=SearchMode.SEMANTIC, top_k=5)
        assert resp.mode == "semantic"
        assert len(resp.hits) > 0

    def test_rrf_mode(self, container):
        resp = container.search_service.search("Test", mode=SearchMode.RRF, top_k=5)
        assert resp.mode == "rrf"
        assert len(resp.hits) > 0

    def test_linear_mode(self, container):
        resp = container.search_service.search("Test Item", mode=SearchMode.LINEAR, top_k=5)
        assert resp.mode == "linear"
        assert len(resp.hits) > 0

    def test_response_fields(self, container):
        resp = container.search_service.search("Test", mode=SearchMode.LINEAR, top_k=5)
        assert resp.query_text == "Test"
        assert resp.returned_count <= 5
        assert resp.index_generation >= 1
        assert resp.took_ms >= 0
        assert resp.total_candidates >= 5

    def test_top_k_truncation(self, container):
        resp = container.search_service.search("Test", mode=SearchMode.LINEAR, top_k=2)
        assert len(resp.hits) <= 2

    def test_metadata_on_hits(self, container):
        resp = container.search_service.search("Test", mode=SearchMode.LINEAR, top_k=3)
        for hit in resp.hits:
            assert "category" in hit.metadata or hit.metadata == {}

    def test_deterministic_same_query(self, container):
        r1 = container.search_service.search("Test", mode=SearchMode.BM25, top_k=5)
        r2 = container.search_service.search("Test", mode=SearchMode.BM25, top_k=5)
        assert [h.item_id for h in r1.hits] == [h.item_id for h in r2.hits]
