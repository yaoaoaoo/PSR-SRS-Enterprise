"""Tests for algorithm input adapters."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.item import Item
from app.models.user import User
from app.repositories.algorithm_inputs import (
    build_evaluation_input,
    build_indexing_input,
    build_profile_input,
    build_rerank_input,
)
from app.repositories.event_repository import EventRepository
from app.repositories.item_repository import ItemRepository
from app.repositories.qrel_repository import QrelRepository
from app.repositories.user_repository import UserRepository


@pytest.fixture
def _populated_db(db_session):
    items = [
        Item(item_id=f"i{j}", title=f"Item {j}", description="Desc",
             category="Electronics", subcategory="S", brand="B",
             price=Decimal("100"), quality_score=0.5, popularity_score=0.5)
        for j in range(3)
    ]
    users = [User(user_id=f"u{j}") for j in range(2)]
    db_session.add_all(items + users)
    db_session.commit()


class TestAlgorithmInputs:
    def test_build_indexing_input(self, db_session, _populated_db):
        repo = ItemRepository(db_session)
        pairs = build_indexing_input(repo)
        assert len(pairs) == 3
        assert all(isinstance(p[0], str) for p in pairs)
        assert all(isinstance(p[1], str) for p in pairs)

    def test_build_profile_input(self, db_session, _populated_db):
        user_repo = UserRepository(db_session)
        item_repo = ItemRepository(db_session)
        event_repo = EventRepository(db_session)
        events, items_map, users_map = build_profile_input(event_repo, item_repo, user_repo)
        assert isinstance(events, list)
        assert isinstance(items_map, dict)
        assert isinstance(users_map, dict)
        assert len(users_map) == 2

    def test_build_rerank_input(self, db_session, _populated_db):
        repo = ItemRepository(db_session)
        items_map = build_rerank_input(repo)
        assert len(items_map) == 3
        assert "category" in items_map["i0"]

    def test_build_evaluation_input(self, db_session, _populated_db):
        from app.models.qrel import Qrel
        from app.models.query import Query

        q = Query(query_id="q1", query_text="test")
        db_session.add(q)
        db_session.flush()  # ensure FK target exists before Qrel insert
        qrel = Qrel(query_id="q1", item_id="i0", relevance_grade=3)
        db_session.add(qrel)
        db_session.commit()

        repo = QrelRepository(db_session)
        qrels_map = build_evaluation_input(repo)
        assert "q1" in qrels_map
        assert qrels_map["q1"]["i0"] == 3
