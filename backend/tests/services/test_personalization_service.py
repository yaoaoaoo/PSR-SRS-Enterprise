"""PersonalizationService tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.event import Event
from app.models.item import Item
from app.models.user import User
from app.services.container import ServiceContainer
from app.services.types import SearchHit


@pytest.fixture
def _pers_data(db_session):
    from datetime import UTC, datetime

    users = [
        User(user_id="u_warm"), User(user_id="u_cold", is_cold_start=True),
    ]
    items = [
        Item(item_id=f"i{j}", title=f"Item {j}", description="", category="Electronics",
             subcategory="S", brand="B", price=Decimal("100"),
             quality_score=0.5, popularity_score=0.5)
        for j in range(5)
    ]
    db_session.add_all(users + items)
    db_session.flush()

    events = [
        Event(event_id=f"ev_{j}", event_type="click", request_id="r", session_id="s",
              user_id="u_warm", item_id="i0", position=1,
              timestamp=datetime(2026, 3, j + 1, tzinfo=UTC))
        for j in range(3)
    ]
    db_session.add_all(events)
    db_session.commit()


@pytest.fixture
def container(db_session_factory, _pers_data):
    c = ServiceContainer(db_session_factory)
    c.initialize()
    return c


def _make_hits(*ids: str) -> list[SearchHit]:
    return [
        SearchHit(item_id=iid, score=1.0, rank=j + 1, source="linear",
                  fusion_score=1.0, metadata={})
        for j, iid in enumerate(ids)
    ]


class TestPersonalizationService:
    def test_warm_user_reranks(self, container):
        snap = container.index_manager.get_snapshot()
        hits = _make_hits("i0", "i1", "i2")
        result = container.personalization_service.rerank(
            hits, user_id="u_warm", top_k=3, index_snapshot=snap,
        )
        assert len(result.hits) == 3

    def test_cold_start_fallback(self, container):
        snap = container.index_manager.get_snapshot()
        hits = _make_hits("i0", "i1", "i2")
        result = container.personalization_service.rerank(
            hits, user_id="u_cold", top_k=3, index_snapshot=snap,
        )
        assert result.applied is False
        assert result.fallback_reason == "cold_start_user"

    def test_unknown_user_fallback(self, container):
        snap = container.index_manager.get_snapshot()
        hits = _make_hits("i0", "i1")
        result = container.personalization_service.rerank(
            hits, user_id="unknown_user", top_k=2, index_snapshot=snap,
        )
        assert result.applied is False
        assert result.fallback_reason == "unknown_user"

    def test_empty_candidates(self, container):
        snap = container.index_manager.get_snapshot()
        result = container.personalization_service.rerank(
            [], user_id="u_warm", top_k=5, index_snapshot=snap,
        )
        assert result.hits == []
        assert result.applied is False

    def test_input_not_modified(self, container):
        snap = container.index_manager.get_snapshot()
        hits = _make_hits("i0", "i1")
        before = [h.item_id for h in hits]
        container.personalization_service.rerank(
            hits, user_id="u_warm", top_k=2, index_snapshot=snap,
        )
        assert [h.item_id for h in hits] == before

    def test_original_rank_preserved(self, container):
        snap = container.index_manager.get_snapshot()
        hits = _make_hits("i0", "i1")
        result = container.personalization_service.rerank(
            hits, user_id="u_warm", top_k=2, index_snapshot=snap,
        )
        for h in result.hits:
            assert h.original_rank is not None
