"""ProfileService tests — build, rebuild, snapshots, edge cases."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.event import Event
from app.models.item import Item
from app.models.user import User
from app.services.profile_service import ProfileService


@pytest.fixture
def _profile_data(db_session):
    from datetime import UTC, datetime

    users = [User(user_id=f"u{j}", is_cold_start=(j >= 3)) for j in range(5)]
    items = [
        Item(item_id=f"i{j}", title=f"Item {j}", description="", category="Electronics",
             subcategory="S", brand="B", price=Decimal("100"),
             quality_score=0.5, popularity_score=0.5)
        for j in range(3)
    ]
    db_session.add_all(users + items)
    db_session.flush()

    events = [
        Event(event_id=f"ev_{j}", event_type="click", request_id="r", session_id="s",
              user_id=f"u{j}", item_id=f"i{min(j, 2)}", position=1,
              timestamp=datetime(2026, 3, j + 1, tzinfo=UTC))
        for j in range(3)
    ]
    db_session.add_all(events)
    db_session.commit()


class TestProfileServiceBasic:
    def test_initial_not_ready(self, db_session_factory):
        ps = ProfileService(db_session_factory)
        assert not ps.is_ready()
        assert ps.get_profile("u0") is None

    def test_build_succeeds(self, db_session_factory, _profile_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        assert ps.is_ready()
        st = ps.get_status()
        assert st.generation == 1
        assert st.profile_count == 5

    def test_get_profile_warm_user(self, db_session_factory, _profile_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        p = ps.get_profile("u0")
        assert p is not None
        assert p.profile_status == "warm"

    def test_cold_start_user(self, db_session_factory, _profile_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        p = ps.get_profile("u3")  # is_cold_start=True
        assert p is not None
        assert p.is_cold_start

    def test_unknown_user(self, db_session_factory, _profile_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        p = ps.get_profile("nonexistent")
        assert p is None

    def test_built_at_utc(self, db_session_factory, _profile_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        st = ps.get_status()
        assert st.built_at.tzinfo is not None


class TestProfileServiceRebuild:
    def test_rebuild_increments_generation(self, db_session_factory, _profile_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        assert ps.get_status().generation == 1
        ps.build()
        assert ps.get_status().generation == 2

    def test_invalidate(self, db_session_factory, _profile_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        assert ps.is_ready()
        ps.invalidate()
        assert not ps.is_ready()
        assert ps.get_snapshot() is None

    def test_read_old_snapshot_during_rebuild(self, db_session_factory, _profile_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        old = ps.get_snapshot()
        ps.build()
        assert old.generation == 1
        assert ps.get_snapshot().generation == 2


class TestProfileServiceFailedRebuild:
    def test_empty_users_preserves_old_snapshot(self, db_session_factory, _profile_data):
        ps = ProfileService(db_session_factory)
        ps.build()
        ps.get_snapshot()  # verify snapshot exists
        old_gen = ps.get_status().generation

        # Delete all users, then rebuild
        from app.models.event import Event
        from app.models.user import User
        s = db_session_factory()
        s.query(Event).delete()
        s.query(User).delete()
        s.commit()
        s.close()

        ps.build()  # no users → records error, preserves old snapshot

        cur_snap = ps.get_snapshot()
        assert cur_snap is not None
        assert cur_snap.generation == old_gen
        p = ps.get_profile("u0")
        assert p is not None

    def test_failed_first_build_not_ready(self, db_session_factory):
        ps = ProfileService(db_session_factory)
        ps.build()  # no data
        assert not ps.is_ready()
        assert ps.get_status().generation == 0
