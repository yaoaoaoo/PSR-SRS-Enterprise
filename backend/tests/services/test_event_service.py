"""Tests for EventService — create, idempotency, stats, recent."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.services.event_service import EventService


@pytest.fixture
def _setup_users_items(db_session):
    from decimal import Decimal

    from app.models.item import Item
    from app.models.user import User
    u = User(user_id="u1")
    i = Item(item_id="i1", title="T", description="", category="C", subcategory="S",
             brand="B", price=Decimal("10"), quality_score=0.5, popularity_score=0.5)
    db_session.add_all([u, i])
    db_session.commit()


class TestCreateEvent:
    def test_create_impression(self, db_session, _setup_users_items):
        svc = EventService(db_session)
        e = svc.create_event(event_id="ev1", event_type="impression", request_id="r1",
                             user_id="u1", item_id="i1", position=1)
        db_session.commit()
        assert e.event_id == "ev1"
        assert e.event_type == "impression"

    def test_create_click(self, db_session, _setup_users_items):
        svc = EventService(db_session)
        e = svc.create_event(event_id="ev_click", event_type="click", request_id="r1",
                             user_id="u1", item_id="i1", position=2, click_duration_ms=500)
        db_session.commit()
        assert e.event_type == "click"
        assert e.click_duration_ms == 500

    def test_create_favorite(self, db_session, _setup_users_items):
        svc = EventService(db_session)
        e = svc.create_event(event_id="ev_fav", event_type="favorite", request_id="r1",
                             user_id="u1", item_id="i1")
        db_session.commit()
        assert e.event_type == "favorite"

    def test_create_add_to_cart(self, db_session, _setup_users_items):
        svc = EventService(db_session)
        e = svc.create_event(event_id="ev_atc", event_type="add_to_cart", request_id="r1",
                             user_id="u1", item_id="i1", add_to_cart_quantity=2)
        db_session.commit()
        assert e.event_type == "add_to_cart"
        assert e.add_to_cart_quantity == 2

    def test_create_purchase(self, db_session, _setup_users_items):
        svc = EventService(db_session)
        e = svc.create_event(event_id="ev_purch", event_type="purchase", request_id="r1",
                             user_id="u1", item_id="i1", purchase_amount=99.99)
        db_session.commit()
        assert e.event_type == "purchase"
        assert float(e.purchase_amount) == pytest.approx(99.99)

    def test_invalid_event_type_rejected(self, db_session):
        svc = EventService(db_session)
        with pytest.raises(ValueError, match="Invalid event_type"):
            svc.create_event(event_id="ev1", event_type="INVALID", request_id="r1")

    def test_missing_item_fails(self, db_session, _setup_users_items):
        svc = EventService(db_session)
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            svc.create_event(event_id="ev1", event_type="click", request_id="r1",
                             user_id="u1", item_id="nonexistent")
            db_session.commit()

    def test_idempotent_client_event_id(self, db_session, _setup_users_items):
        svc = EventService(db_session)
        e1 = svc.create_event(event_id="ev_idem", event_type="click", request_id="r1",
                              user_id="u1", item_id="i1", client_event_id="cei_001")
        db_session.commit()
        e2 = svc.create_event(event_id="ev_idem_dup", event_type="click", request_id="r2",
                              user_id="u1", item_id="i1", client_event_id="cei_001")
        assert e1.event_id == e2.event_id
        # Count should be 1 not 2
        count = db_session.query(type(e1)).filter(
            type(e1).client_event_id == "cei_001"
        ).count()
        assert count == 1


class TestEventStats:
    def _add_events(self, db_session):
        svc = EventService(db_session)
        svc.create_event(event_id="s_imp", event_type="impression", request_id="r1",
                         user_id="u1", item_id="i1", position=1)
        svc.create_event(event_id="s_imp2", event_type="impression", request_id="r1",
                         user_id="u1", item_id="i1", position=2)
        svc.create_event(event_id="s_click", event_type="click", request_id="r1",
                         user_id="u1", item_id="i1", position=1)
        svc.create_event(event_id="s_fav", event_type="favorite", request_id="r1",
                         user_id="u1", item_id="i1")
        svc.create_event(event_id="s_atc", event_type="add_to_cart", request_id="r1",
                         user_id="u1", item_id="i1")
        svc.create_event(event_id="s_purch", event_type="purchase", request_id="r1",
                         user_id="u1", item_id="i1")
        svc.create_event(event_id="s_click2", event_type="click", request_id="r2",
                         user_id="u1", item_id="i1", position=2,
                         occurred_at=datetime(2026, 1, 1, tzinfo=UTC))
        db_session.commit()

    def test_empty_stats_all_zero(self, db_session):
        svc = EventService(db_session)
        s = svc.get_stats()
        assert s["total_events"] == 0
        assert s["event_counts"]["impression"] == 0

    def test_total_events(self, db_session, _setup_users_items):
        self._add_events(db_session)
        svc = EventService(db_session)
        assert svc.get_stats()["total_events"] == 7

    def test_event_counts(self, db_session, _setup_users_items):
        self._add_events(db_session)
        s = EventService(db_session).get_stats()
        assert s["event_counts"]["impression"] == 2
        assert s["event_counts"]["click"] == 2
        assert s["event_counts"]["favorite"] == 1

    def test_ctr(self, db_session, _setup_users_items):
        self._add_events(db_session)
        s = EventService(db_session).get_stats()
        assert s["rates"]["click_through_rate"] == 1.0  # 2/2

    def test_favorite_rate(self, db_session, _setup_users_items):
        self._add_events(db_session)
        s = EventService(db_session).get_stats()
        assert s["rates"]["favorite_rate"] == 0.5  # 1/2

    def test_zero_click_ratio(self, db_session, _setup_users_items):
        svc = EventService(db_session)
        svc.create_event(event_id="z_imp", event_type="impression", request_id="r1",
                         user_id="u1", item_id="i1")
        db_session.commit()
        s = svc.get_stats()
        assert s["rates"]["click_through_rate"] == 0.0
        assert s["rates"]["favorite_rate"] == 0.0

    def test_zero_impression_ctr(self, db_session, _setup_users_items):
        svc = EventService(db_session)
        svc.create_event(event_id="z_click", event_type="click", request_id="r1",
                         user_id="u1", item_id="i1")
        db_session.commit()
        s = svc.get_stats()
        assert s["rates"]["click_through_rate"] == 0.0  # cf / 0 imp = 0

    def test_user_id_filter(self, db_session, _setup_users_items):
        self._add_events(db_session)
        s = EventService(db_session).get_stats(user_id="u1")
        assert s["total_events"] == 7
        s2 = EventService(db_session).get_stats(user_id="nonexistent")
        assert s2["total_events"] == 0

    def test_event_type_filter(self, db_session, _setup_users_items):
        self._add_events(db_session)
        s = EventService(db_session).get_stats(event_type="click")
        assert s["total_events"] == 2

    def test_start_at_filter(self, db_session, _setup_users_items):
        self._add_events(db_session)
        s = EventService(db_session).get_stats(start_at=datetime(2026, 6, 1, tzinfo=UTC))
        assert s["total_events"] == 6  # excludes the Jan 1 click

    def test_end_at_filter(self, db_session, _setup_users_items):
        self._add_events(db_session)
        s = EventService(db_session).get_stats(end_at=datetime(2026, 3, 1, tzinfo=UTC))
        assert s["total_events"] == 1  # only the Jan 1 click

    def test_start_and_end_combined(self, db_session, _setup_users_items):
        self._add_events(db_session)
        s = EventService(db_session).get_stats(
            start_at=datetime(2025, 1, 1, tzinfo=UTC),
            end_at=datetime(2026, 3, 1, tzinfo=UTC),
        )
        assert s["total_events"] == 1


class TestRecentEvents:
    def _setup(self, db_session, _setup_users_items):
        svc = EventService(db_session)
        for j in range(5):
            svc.create_event(event_id=f"rec_{j}", event_type="click", request_id="r1",
                             user_id="u1", item_id="i1")
        db_session.commit()

    def test_default_limit(self, db_session, _setup_users_items):
        self._setup(db_session, _setup_users_items)
        events = EventService(db_session).list_recent()
        assert len(events) == 5

    def test_custom_limit(self, db_session, _setup_users_items):
        self._setup(db_session, _setup_users_items)
        events = EventService(db_session).list_recent(limit=2)
        assert len(events) == 2

    def test_event_type_filter(self, db_session, _setup_users_items):
        self._setup(db_session, _setup_users_items)
        events = EventService(db_session).list_recent(event_type="favorite")
        assert len(events) == 0  # all are clicks

    def test_user_id_filter(self, db_session, _setup_users_items):
        self._setup(db_session, _setup_users_items)
        events = EventService(db_session).list_recent(user_id="nonexistent")
        assert len(events) == 0
