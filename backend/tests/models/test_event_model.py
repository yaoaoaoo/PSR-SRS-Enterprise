"""Tests for Event ORM model — constraints, foreign keys, indexes."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.event import Event
from app.models.item import Item
from app.models.query import Query
from app.models.user import User


@pytest.fixture
def _setup_refs(db_session):
    """Create referenced rows for foreign key tests."""
    u = User(user_id="u1")
    i = Item(
        item_id="i1", title="T", description="", category="C",
        subcategory="S", brand="B", price=10, quality_score=0.5, popularity_score=0.5,
    )
    q = Query(query_id="q1", query_text="test")
    db_session.add_all([u, i, q])
    db_session.commit()


class TestEventModel:
    def test_create_valid_event(self, db_session, _setup_refs):
        e = Event(
            event_id="e1", event_type="click", request_id="r1", session_id="s1",
            user_id="u1", query_id="q1", item_id="i1", position=1,
            timestamp=datetime.now(UTC),
        )
        db_session.add(e)
        db_session.commit()
        assert db_session.get(Event, "e1") is not None

    def test_invalid_event_type_rejected(self, db_session, _setup_refs):
        e = Event(
            event_id="e1", event_type="INVALID", request_id="r1", session_id="s1",
            user_id="u1", item_id="i1",
            timestamp=datetime.now(UTC),
        )
        db_session.add(e)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_missing_user_rejected(self, db_session, _setup_refs):
        e = Event(
            event_id="e1", event_type="click", request_id="r1", session_id="s1",
            user_id="nonexistent", item_id="i1",
            timestamp=datetime.now(UTC),
        )
        db_session.add(e)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_missing_item_rejected(self, db_session, _setup_refs):
        e = Event(
            event_id="e1", event_type="click", request_id="r1", session_id="s1",
            user_id="u1", item_id="nonexistent",
            timestamp=datetime.now(UTC),
        )
        db_session.add(e)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_position_negative_rejected(self, db_session, _setup_refs):
        e = Event(
            event_id="e1", event_type="click", request_id="r1", session_id="s1",
            user_id="u1", item_id="i1", position=-1,
            timestamp=datetime.now(UTC),
        )
        db_session.add(e)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_null_query_id_allowed(self, db_session, _setup_refs):
        e = Event(
            event_id="e2", event_type="impression", request_id="r1", session_id="s1",
            user_id="u1", item_id="i1", query_id=None,
            timestamp=datetime.now(UTC),
        )
        db_session.add(e)
        db_session.commit()
        assert db_session.get(Event, "e2").query_id is None
