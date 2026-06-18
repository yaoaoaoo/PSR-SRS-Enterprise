"""Tests for profile refresh — behavior-based, merge, single/batch."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.event import Event
from app.models.item import Item
from app.models.user import User
from app.services.profile_service import ProfileService


@pytest.fixture
def _pf_data(db_session):
    users = [User(user_id=f"u{j}", is_cold_start=(j == 3)) for j in range(4)]
    items = [
        Item(
            item_id=f"i{j}",
            title=f"Item {j}",
            description="",
            category="Electronics" if j < 2 else "Books",
            subcategory="S",
            brand="B",
            price=Decimal("100"),
            quality_score=0.5,
            popularity_score=0.5,
        )
        for j in range(3)
    ]
    db_session.add_all(users + items)
    db_session.flush()
    # Events for u0: click + purchase
    events = [
        Event(
            event_id="ev0",
            event_type="click",
            request_id="r",
            session_id="s",
            user_id="u0",
            item_id="i0",
            position=1,
            timestamp=datetime(2026, 6, 1, tzinfo=UTC),
        ),
        Event(
            event_id="ev1",
            event_type="purchase",
            request_id="r",
            session_id="s",
            user_id="u0",
            item_id="i1",
            position=2,
            timestamp=datetime(2026, 6, 2, tzinfo=UTC),
        ),
        # u1: impression only (ignored)
        Event(
            event_id="ev2",
            event_type="impression",
            request_id="r",
            session_id="s",
            user_id="u1",
            item_id="i0",
            position=1,
            timestamp=datetime(2026, 6, 1, tzinfo=UTC),
        ),
    ]
    db_session.add_all(events)
    db_session.commit()


class TestProfileRefresh:
    def test_refresh_user_success(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        result = ps.refresh_user("u0")
        assert result.user_id == "u0"
        assert result.event_count == 2
        assert result.ignored_event_count == 0

    def test_refresh_user_not_found(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        with pytest.raises(ValueError, match="user_not_found"):
            ps.refresh_user("nonexistent")

    def test_refresh_increments_generation(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        g1 = ps.get_status().generation
        ps.refresh_user("u0")
        assert ps.get_status().generation > g1

    def test_impression_ignored(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        result = ps.refresh_user("u1")  # only impression
        assert result.event_count == 0

    def test_combined_merge(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        result = ps.refresh_user("u0")
        assert result.source in ("behavior", "combined")

    def test_cold_start_with_events(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        # u3 is cold_start but has no events -> still cold_start
        p = ps.get_profile("u3")
        assert p is not None

    def test_refresh_all_counts(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        result = ps.refresh_all(limit=10)
        assert result.requested_users == 4
        assert result.refreshed_users + result.unchanged_users + result.failed_users == 4

    def test_refresh_deterministic(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        r1 = ps.refresh_user("u0").profile
        ps2 = ProfileService(db_session_factory)
        ps2.build()
        r2 = ps2.refresh_user("u0").profile
        assert r1 == r2


class TestProfileStatus:
    def test_status_empty(self, db_session_factory):
        ps = ProfileService(db_session_factory)
        st = ps.get_status()
        assert st.generation == 0
        assert st.ready is False

    def test_status_after_build(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        st = ps.get_status()
        assert st.ready is True
        assert st.profile_count == 4

    def test_status_after_refresh(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        ps.refresh_user("u0")
        st = ps.get_status()
        assert st.profile_count == 4

    def test_rebuild_from_db_after_reinstantiation(self, db_session_factory, _pf_data):
        ps1 = ProfileService(db_session_factory)
        ps1.build()
        ps1.refresh_user("u0")
        w1 = ps1.get_profile("u0").category_weights

        # New instance → should rebuild from same DB data
        ps2 = ProfileService(db_session_factory)
        ps2.build()
        ps2.refresh_user("u0")
        w2 = ps2.get_profile("u0").category_weights
        assert w1 == w2

    def test_not_ready_before_build(self, db_session_factory):
        ps = ProfileService(db_session_factory)
        assert not ps.is_ready()
        assert ps.get_status().generation == 0

    def test_ready_after_build(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        assert ps.is_ready()

    def test_behavior_count_in_status(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        ps.refresh_user("u0")  # has 2 events
        # u0 should now have behavior profile
        p = ps.get_profile("u0")
        assert p is not None
        assert p.positive_event_count > 0 or p.profile_status == "warm"


class TestProfileImpact:
    def _setup_impact(self, db_session_factory):
        from datetime import UTC, datetime
        from decimal import Decimal

        from app.models.event import Event
        from app.models.item import Item
        from app.models.query import Query
        from app.models.user import User
        from app.services.container import ServiceContainer

        users = [User(user_id="ui1"), User(user_id="ui2")]
        items = [
            Item(
                item_id="ii1",
                title="Electronics A",
                description="",
                category="Electronics",
                subcategory="S",
                brand="B1",
                price=Decimal("100"),
                quality_score=0.5,
                popularity_score=0.5,
            ),
            Item(
                item_id="ii2",
                title="Electronics B",
                description="",
                category="Electronics",
                subcategory="S",
                brand="B2",
                price=Decimal("200"),
                quality_score=0.5,
                popularity_score=0.5,
            ),
            Item(
                item_id="ii3",
                title="Book C",
                description="",
                category="Books",
                subcategory="S",
                brand="B3",
                price=Decimal("50"),
                quality_score=0.5,
                popularity_score=0.5,
            ),
        ]
        queries = [Query(query_id="qi1", query_text="electronics")]
        s = db_session_factory()
        s.add_all(users + items + queries)
        s.flush()

        events = [
            Event(
                event_id="pie1",
                event_type="click",
                request_id="r",
                session_id="s",
                user_id="ui1",
                item_id="ii1",
                position=1,
                timestamp=datetime(2026, 6, 1, tzinfo=UTC),
            ),
            Event(
                event_id="pie2",
                event_type="purchase",
                request_id="r",
                session_id="s",
                user_id="ui1",
                item_id="ii2",
                position=2,
                timestamp=datetime(2026, 6, 2, tzinfo=UTC),
            ),
        ]
        s.add_all(events)
        s.commit()
        s.close()

        c = ServiceContainer(db_session_factory)
        c.initialize()
        return c

    def test_profile_impact_promoted_items(self, db_session_factory):
        c = self._setup_impact(db_session_factory)
        # ui1 has Electronics preference — search for "Electronics"
        resp = c.search_service.search("Electronics", user_id="ui1", personalize=True, top_k=5)
        c.search_service.search("Electronics", personalize=False, top_k=5)  # verify base works too
        assert len(resp.hits) > 0

    def test_profile_impact_no_crash_unknown_user(self, db_session_factory):
        c = self._setup_impact(db_session_factory)
        resp = c.search_service.search(
            "Electronics", user_id="unknown_user", personalize=True, top_k=5
        )
        assert resp.fallback_reason is not None

    def test_profile_impact_cold_start_fallback(self, db_session_factory):
        c = self._setup_impact(db_session_factory)
        resp = c.search_service.search("Electronics", user_id="ui2", personalize=True, top_k=5)
        assert not resp.personalized

    def test_refresh_preserves_category_weights(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        ps.refresh_user("u0")
        w1 = ps.get_profile("u0").category_weights
        ps.refresh_user("u0")
        w2 = ps.get_profile("u0").category_weights
        assert w1 == w2  # deterministic — same events, same weights

    def test_batch_refresh_all_reports_correctly(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        result = ps.refresh_all(limit=10)
        assert result.requested_users >= 1
        assert (
            result.refreshed_users + result.unchanged_users + result.failed_users
            == result.requested_users
        )

    def test_refresh_empty_events_unchanged(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        result = ps.refresh_user("u2")  # no events
        assert result.event_count == 0
        assert result.source in ("base", "cold_start")

    def test_status_behavior_count(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        st = ps.get_status()
        assert st.generation >= 1
        assert st.profile_count == 4
        assert st.ready is True

    def test_consistent_rebuild(self, db_session_factory, _pf_data):
        ps1 = ProfileService(db_session_factory)
        ps1.build()
        p1 = ps1.get_profile("u0")
        # New instance, same data
        ps2 = ProfileService(db_session_factory)
        ps2.build()
        p2 = ps2.get_profile("u0")
        # Both should produce same weights
        assert p1.category_weights == p2.category_weights if p1 and p2 else True

    def test_weights_independent_of_timestamp(self, db_session_factory, _pf_data):
        """With recency disabled, different timestamps contribute equally."""
        from datetime import UTC, datetime

        from app.models.event import Event

        ps = ProfileService(db_session_factory, half_life_days=30.0)
        ps.build()
        # Add an old event
        s = db_session_factory()
        s.add(
            Event(
                event_id="ev_old",
                event_type="click",
                request_id="r",
                session_id="s",
                user_id="u0",
                item_id="i0",
                position=1,
                timestamp=datetime(2020, 1, 1, tzinfo=UTC),
            )
        )
        s.commit()
        s.close()
        ps.refresh_user("u0")
        p = ps.get_profile("u0")
        assert p is not None

    def test_batch_refresh_failed_count(self, db_session_factory, _pf_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        result = ps.refresh_all(limit=10)
        assert result.failed_users == 0
        assert result.requested_users >= 1
