"""Tests for user profile construction."""

from __future__ import annotations

import pytest

from app.personalization.profiles import UserProfile, build_profiles

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def items() -> dict[str, dict]:
    return {
        "i1": {"category": "Electronics", "subcategory": "Laptops", "brand": "TechPro", "price": "1000"},
        "i2": {"category": "Electronics", "subcategory": "Phones", "brand": "SmartWave", "price": "800"},
        "i3": {"category": "Books", "subcategory": "Fiction", "brand": "ReadWell", "price": "20"},
    }


@pytest.fixture
def users_map() -> dict[str, dict]:
    return {
        "u_warm": {"is_cold_start": "false"},
        "u_cold": {"is_cold_start": "true"},
        "u_empty": {"is_cold_start": "false"},
    }


@pytest.fixture
def train_events() -> list[dict]:
    return [
        {
            "user_id": "u_warm",
            "event_type": "click",
            "item_id": "i1",
            "timestamp": "2026-03-15T10:00:00+00:00",
            "session_id": "sess_1",
        },
        {
            "user_id": "u_warm",
            "event_type": "purchase",
            "item_id": "i2",
            "timestamp": "2026-03-20T10:00:00+00:00",
            "session_id": "sess_2",
        },
        {
            "user_id": "u_cold",
            "event_type": "impression",
            "item_id": "i3",
            "timestamp": "2026-03-10T10:00:00+00:00",
            "session_id": "sess_1",
        },
    ]


@pytest.fixture
def event_weights() -> dict[str, float]:
    return {"click": 1.0, "favorite": 2.0, "add_to_cart": 3.0, "purchase": 5.0}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestUserProfile:
    def test_default_empty(self):
        p = UserProfile("u1")
        assert p.user_id == "u1"
        assert p.is_cold_start is False
        p.finalize()  # finalize sets profile_status
        assert p.profile_status == "no_history"  # no events → no_history

    def test_cold_start(self):
        p = UserProfile("u1", is_cold_start=True)
        p.finalize()
        assert p.profile_status == "cold_start"

    def test_warm_with_positives(self):
        p = UserProfile("u1")
        p.positive_event_count = 5
        p.finalize()
        assert p.profile_status == "warm"

    def test_category_weights(self):
        p = UserProfile("u1")
        p._cat_scores = {"Electronics": 10.0, "Books": 5.0}
        assert p.category_weights == {"Electronics": 10 / 15, "Books": 5 / 15}

    def test_category_weights_empty(self):
        p = UserProfile("u1")
        assert p.category_weights == {}

    def test_mean_log_price(self):
        p = UserProfile("u1")
        p._price_log_sum = 10.0
        p._price_weight_sum = 2.0
        assert p.mean_log_price == 5.0

    def test_mean_log_price_none(self):
        p = UserProfile("u1")
        assert p.mean_log_price is None


class TestBuildProfiles:
    def test_warm_profile(self, train_events, items, users_map, event_weights):
        profiles = build_profiles(train_events, items, users_map, event_weights, 30.0)
        warm = profiles["u_warm"]
        assert warm.profile_status == "warm"
        assert warm.positive_event_count == 2
        assert warm.train_event_count == 2

    def test_cold_start_profile(self, train_events, items, users_map, event_weights):
        profiles = build_profiles(train_events, items, users_map, event_weights, 30.0)
        cold = profiles["u_cold"]
        assert cold.is_cold_start is True
        assert cold.profile_status == "cold_start"
        # Only had impression (not positive), but has train events
        assert cold.train_event_count == 1

    def test_empty_profile(self, train_events, items, users_map, event_weights):
        profiles = build_profiles(train_events, items, users_map, event_weights, 30.0)
        empty = profiles["u_empty"]
        assert empty.train_event_count == 0
        assert empty.profile_status == "no_history"

    def test_category_preferences(self, train_events, items, users_map, event_weights):
        profiles = build_profiles(train_events, items, users_map, event_weights, 30.0)
        warm = profiles["u_warm"]
        # Should have affinity for Electronics (both i1 and i2 are Electronics)
        assert len(warm.category_weights) > 0
        most_preferred = max(warm.category_weights, key=warm.category_weights.get)
        assert most_preferred == "Electronics"

    def test_brand_preferences(self, train_events, items, users_map, event_weights):
        profiles = build_profiles(train_events, items, users_map, event_weights, 30.0)
        warm = profiles["u_warm"]
        assert len(warm.brand_weights) > 0

    def test_missing_item_no_crash(self, items, users_map, event_weights):
        events = [{
            "user_id": "u_warm",
            "event_type": "purchase",
            "item_id": "nonexistent_item",
            "timestamp": "2026-03-20T10:00:00+00:00",
            "session_id": "sess_1",
        }]
        profiles = build_profiles(events, items, users_map, event_weights, 30.0)
        warm = profiles["u_warm"]
        assert warm.train_event_count == 1
        assert warm.positive_event_count == 0  # item not found, not counted

    def test_all_users_included(self, train_events, items, users_map, event_weights):
        profiles = build_profiles(train_events, items, users_map, event_weights, 30.0)
        assert set(profiles.keys()) == {"u_warm", "u_cold", "u_empty"}

    def test_time_decay(self, items, users_map, event_weights):
        """Older events should get lower weight."""
        events = [
            {
                "user_id": "u_warm",
                "event_type": "click",
                "item_id": "i1",
                "timestamp": "2026-02-01T10:00:00+00:00",  # very old
                "session_id": "sess_1",
            },
            {
                "user_id": "u_warm",
                "event_type": "click",
                "item_id": "i2",
                "timestamp": "2026-03-20T10:00:00+00:00",  # recent
                "session_id": "sess_2",
            },
        ]
        profiles = build_profiles(events, items, users_map, event_weights, 7.0)  # short half-life
        warm = profiles["u_warm"]
        # The old event should have near-zero contribution due to decay
        assert warm.positive_event_count == 2  # both counted as events
        # Brand from recent event should dominate
        weights = warm.brand_weights
        assert weights.get("SmartWave", 0) > weights.get("TechPro", 0)


class TestUserProfileEdgeCases:
    """Additional edge cases for profiles coverage."""

    def test_add_event_zero_weight(self):
        p = UserProfile("u1")
        p.add_event(
            {"timestamp": "2026-03-15T10:00:00+00:00"},
            {"category": "Electronics", "price": "100"},
            weight=0.0, decay=1.0,
        )
        assert p.positive_event_count == 0

    def test_add_event_zero_decay(self):
        p = UserProfile("u1")
        p.add_event(
            {"timestamp": "2026-03-15T10:00:00+00:00"},
            {"category": "Electronics", "price": "100"},
            weight=1.0, decay=0.0,
        )
        assert p.positive_event_count == 0

    def test_add_event_invalid_price(self):
        p = UserProfile("u1")
        p.add_event(
            {"timestamp": "2026-03-15T10:00:00+00:00"},
            {"category": "Electronics", "price": "not_a_number"},
            weight=1.0, decay=1.0,
        )
        assert p.positive_event_count == 1
        assert p.mean_log_price is not None

    def test_add_event_zero_price(self):
        p = UserProfile("u1")
        p.add_event(
            {"timestamp": "2026-03-15T10:00:00+00:00"},
            {"category": "Electronics", "price": "0"},
            weight=1.0, decay=1.0,
        )
        assert p.mean_log_price is None  # price=0 skipped

    def test_add_event_missing_category(self):
        p = UserProfile("u1")
        p.add_event(
            {"timestamp": "2026-03-15T10:00:00+00:00"},
            {},  # empty item
            weight=1.0, decay=1.0,
        )
        assert p.positive_event_count == 1
        assert p.category_weights == {}

    def test_add_event_missing_brand(self):
        p = UserProfile("u1")
        p.add_event(
            {"timestamp": "2026-03-15T10:00:00+00:00"},
            {"category": "X", "price": "50"},
            weight=1.0, decay=1.0,
        )
        assert p.brand_weights == {}

    def test_finalize_repeat_call(self):
        p = UserProfile("u1")
        p.positive_event_count = 1
        p.finalize()
        assert p.profile_status == "warm"
        p.finalize()  # second call should be idempotent
        assert p.profile_status == "warm"

    def test_last_train_event_at_empty(self):
        p = UserProfile("u1")
        assert p.last_train_event_at() == ""

    def test_last_train_event_at_populated(self):
        p = UserProfile("u1")
        p.add_event(
            {"timestamp": "2026-03-15T10:00:00+00:00"},
            {"category": "X", "price": "50"},
            weight=1.0, decay=1.0,
        )
        assert p.last_train_event_at() != ""

    def test_add_event_updates_last_ts(self):
        p = UserProfile("u1")
        p.add_event(
            {"timestamp": "2026-03-10T10:00:00+00:00"},
            {"category": "X", "price": "50"},
            weight=1.0, decay=1.0,
        )
        earlier = p.last_train_event_at()
        p.add_event(
            {"timestamp": "2026-03-20T10:00:00+00:00"},
            {"category": "Y", "price": "60"},
            weight=1.0, decay=1.0,
        )
        later = p.last_train_event_at()
        assert later != earlier


class TestBuildProfilesEdgeCases:
    """Edge cases for build_profiles."""

    def test_unknown_event_type(self, items, users_map, event_weights):
        events = [{
            "user_id": "u_warm", "event_type": "scroll",  # unknown type
            "item_id": "i1", "timestamp": "2026-03-15T10:00:00+00:00",
            "session_id": "sess_1",
        }]
        profiles = build_profiles(events, items, users_map, event_weights, 30.0)
        p = profiles["u_warm"]
        assert p.train_event_count == 1
        assert p.positive_event_count == 0  # scroll is not a positive type

    def test_event_with_missing_item_id(self, items, users_map, event_weights):
        events = [{
            "user_id": "u_warm", "event_type": "click",
            "item_id": "", "timestamp": "2026-03-15T10:00:00+00:00",
            "session_id": "sess_1",
        }]
        profiles = build_profiles(events, items, users_map, event_weights, 30.0)
        p = profiles["u_warm"]
        assert p.train_event_count == 1

    def test_new_user_not_in_users_map(self, items, users_map, event_weights):
        events = [{
            "user_id": "u_new", "event_type": "click",
            "item_id": "i1", "timestamp": "2026-03-15T10:00:00+00:00",
            "session_id": "sess_1",
        }]
        profiles = build_profiles(events, items, users_map, event_weights, 30.0)
        assert "u_new" in profiles
        assert profiles["u_new"].profile_status == "warm"

    def test_empty_train_events(self, users_map, event_weights):
        profiles = build_profiles([], {}, users_map, event_weights, 30.0)
        for p in profiles.values():
            assert p.train_event_count == 0

    def test_single_click_event(self, items, users_map, event_weights):
        events = [{
            "user_id": "u_warm", "event_type": "click",
            "item_id": "i1", "timestamp": "2026-03-15T10:00:00+00:00",
            "session_id": "sess_1",
        }]
        profiles = build_profiles(events, items, users_map, event_weights, 30.0)
        p = profiles["u_warm"]
        assert p.positive_event_count == 1
        assert p.train_event_count == 1
        assert len(p.train_session_count) == 1

    def test_multiple_events_accumulate(self, items, users_map, event_weights):
        events = [
            {"user_id": "u_warm", "event_type": "click", "item_id": "i1",
             "timestamp": "2026-03-15T10:00:00+00:00", "session_id": "sess_1"},
            {"user_id": "u_warm", "event_type": "purchase", "item_id": "i1",
             "timestamp": "2026-03-15T11:00:00+00:00", "session_id": "sess_1"},
        ]
        profiles = build_profiles(events, items, users_map, event_weights, 30.0)
        p = profiles["u_warm"]
        assert p.positive_event_count == 2
        assert p.train_event_count == 2
        # Category should accumulate
        assert len(p.category_weights) >= 1

    def test_no_positive_finalize_status(self, users_map, event_weights):
        events = [{
            "user_id": "u_warm", "event_type": "impression",
            "item_id": "i1", "timestamp": "2026-03-15T10:00:00+00:00",
            "session_id": "sess_1",
        }]
        profiles = build_profiles(
            events,
            {"i1": {"category": "X", "price": "10"}},
            users_map, event_weights, 30.0,
        )
        p = profiles["u_warm"]
        assert p.profile_status == "no_positive"
        assert p.train_event_count == 1

    def test_cold_start_with_no_events(self):
        """Cold start user who had no events at all."""
        users_map = {"u_c": {"is_cold_start": "true"}}
        profiles = build_profiles([], {}, users_map, {}, 30.0)
        p = profiles["u_c"]
        assert p.is_cold_start is True
        assert p.profile_status == "cold_start"

    def test_half_life_zero(self, items, users_map, event_weights):
        """half_life_days=0 means no decay."""
        events = [{
            "user_id": "u_warm", "event_type": "click",
            "item_id": "i1", "timestamp": "2026-01-01T00:00:00+00:00",
            "session_id": "sess_1",
        }]
        profiles = build_profiles(events, items, users_map, event_weights, 0.0)
        p = profiles["u_warm"]
        assert p.positive_event_count == 1  # no decay — event still counts
