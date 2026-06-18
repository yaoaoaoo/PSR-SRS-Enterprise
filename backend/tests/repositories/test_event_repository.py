"""Tests for EventRepository."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models.event import Event
from app.models.item import Item
from app.models.query import Query
from app.models.user import User
from app.repositories.event_repository import EventRepository


@pytest.fixture
def _event_data(db_session):
    u = User(user_id="u1")
    i = Item(item_id="i1", title="X", description="", category="C", subcategory="S",
             brand="B", price=10, quality_score=0.5, popularity_score=0.5)
    q = Query(query_id="q1", query_text="test")
    db_session.add_all([u, i, q])
    db_session.commit()

    events = [
        Event(event_id=f"e{j}", event_type="click" if j % 2 == 0 else "impression",
              request_id="r1", session_id="s1", user_id="u1", query_id="q1",
              item_id="i1", position=j + 1,
              timestamp=datetime(2026, 3, j + 1, tzinfo=UTC))
        for j in range(5)
    ]
    db_session.add_all(events)
    db_session.commit()


class TestEventRepository:
    def test_count(self, db_session, _event_data):
        repo = EventRepository(db_session)
        assert repo.count() == 5

    def test_count_by_type(self, db_session, _event_data):
        repo = EventRepository(db_session)
        counts = repo.count_by_type()
        assert counts["click"] == 3
        assert counts["impression"] == 2

    def test_list_for_user(self, db_session, _event_data):
        repo = EventRepository(db_session)
        events = repo.list_for_user("u1")
        assert len(events) == 5

    def test_list_for_user_type_filter(self, db_session, _event_data):
        repo = EventRepository(db_session)
        events = repo.list_for_user("u1", event_type="click")
        assert len(events) == 3

    def test_list_for_user_limit(self, db_session, _event_data):
        repo = EventRepository(db_session)
        events = repo.list_for_user("u1", limit=2)
        assert len(events) == 2

    def test_list_for_query(self, db_session, _event_data):
        repo = EventRepository(db_session)
        events = repo.list_for_query("q1")
        assert len(events) == 5

    def test_list_training_events(self, db_session, _event_data):
        repo = EventRepository(db_session)
        events = repo.list_training_events()
        assert len(events) == 5
        assert events[0]["user_id"] == "u1"
        assert "timestamp" in events[0]

    def test_time_filter(self, db_session, _event_data):
        repo = EventRepository(db_session)
        after = datetime(2026, 3, 3, tzinfo=UTC)
        events = repo.list_for_user("u1", after=after)
        assert len(events) == 3  # events on days 3,4,5
