"""User profile construction from historical behaviour events.

Accepts in-memory data — no CSV, ORM, or FastAPI dependency.

Identical algorithm to PSR-SRS-MVP.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import UTC, datetime


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


class UserProfile:
    """Aggregated user preferences from training events.

    Attributes:
        user_id: Unique user identifier.
        is_cold_start: Whether the user was flagged as cold-start.
        profile_status: ``"warm"``, ``"cold_start"``, ``"no_positive"``, or ``"no_history"``.
        category_weights: Normalised category affinity scores.
        subcategory_weights: Normalised subcategory affinity scores.
        brand_weights: Normalised brand affinity scores.
        mean_log_price: Geometric-mean price preference.
        price_std: Fixed price scale parameter.
    """

    def __init__(self, user_id: str, is_cold_start: bool = False):
        self.user_id = user_id
        self.is_cold_start = is_cold_start
        self.train_event_count = 0
        self.train_session_count: set[str] = set()
        self.positive_event_count = 0
        self.profile_status = "empty"

        # Weighted accumulators
        self._cat_scores: dict[str, float] = defaultdict(float)
        self._subcat_scores: dict[str, float] = defaultdict(float)
        self._brand_scores: dict[str, float] = defaultdict(float)
        self._price_log_sum = 0.0
        self._price_weight_sum = 0.0
        self._last_ts: datetime | None = None

    @property
    def category_weights(self) -> dict[str, float]:
        return _normalize(self._cat_scores)

    @property
    def subcategory_weights(self) -> dict[str, float]:
        return _normalize(self._subcat_scores)

    @property
    def brand_weights(self) -> dict[str, float]:
        return _normalize(self._brand_scores)

    @property
    def mean_log_price(self) -> float | None:
        if self._price_weight_sum > 0:
            return self._price_log_sum / self._price_weight_sum
        return None

    @property
    def price_std(self) -> float:
        return 0.5  # simplified — same as MVP

    def add_event(self, event: dict, item: dict, weight: float, decay: float):
        """Add a single positive event contribution."""
        eff = weight * decay
        if eff <= 0:
            return
        cat = item.get("category", "")
        subcat = item.get("subcategory", "")
        brand = item.get("brand", "")
        if cat:
            self._cat_scores[cat] += eff
        if subcat:
            self._subcat_scores[subcat] += eff
        if brand:
            self._brand_scores[brand] += eff

        try:
            price = float(item.get("price", 0))
        except (ValueError, TypeError):
            price = 1.0
        if price > 0:
            self._price_log_sum += math.log(price) * eff
            self._price_weight_sum += eff

        self.positive_event_count += 1
        ts = _parse_ts(event["timestamp"])
        if self._last_ts is None or ts > self._last_ts:
            self._last_ts = ts

    def finalize(self):
        """Mark profile as ready and compute status."""
        if self.positive_event_count > 0:
            self.profile_status = "warm"
        elif self.is_cold_start:
            self.profile_status = "cold_start"
        elif self.train_event_count > 0:
            self.profile_status = "no_positive"
        else:
            self.profile_status = "no_history"

    def last_train_event_at(self) -> str:
        if self._last_ts:
            return self._last_ts.isoformat()
        return ""


def _normalize(d: dict[str, float]) -> dict[str, float]:
    total = sum(d.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in d.items()}


def build_profiles(
    train_events: list[dict],
    items: dict[str, dict],
    users_map: dict[str, dict],
    event_weights: dict[str, float],
    half_life_days: float,
) -> dict[str, UserProfile]:
    """Build user profiles from training events only.

    Args:
        train_events: List of event dicts (must have ``user_id``, ``event_type``,
                      ``item_id``, ``timestamp``, optionally ``session_id``).
        items: ``{item_id: {category, subcategory, brand, price, ...}}``.
        users_map: ``{user_id: {is_cold_start, ...}}``.
        event_weights: ``{"click": 1.0, "favorite": 2.0, ...}``.
        half_life_days: Exponential decay half-life in days.

    Returns:
        ``{user_id: UserProfile}`` — all known users are included, even
        those without events.
    """
    profiles: dict[str, UserProfile] = {}

    # Initialize all known users
    for uid, urow in users_map.items():
        is_cold = str(urow.get("is_cold_start", "false")).lower() == "true"
        profiles[uid] = UserProfile(uid, is_cold)

    # Find the latest training timestamp for decay reference
    train_ts = [_parse_ts(e["timestamp"]) for e in train_events]
    ref_ts = max(train_ts) if train_ts else datetime(2026, 3, 31, tzinfo=UTC)

    positive_types = {"click", "favorite", "add_to_cart", "purchase"}

    for e in train_events:
        uid = e["user_id"]
        if uid not in profiles:
            profiles[uid] = UserProfile(uid)
        profile = profiles[uid]
        profile.train_event_count += 1
        profile.train_session_count.add(e.get("session_id", ""))

        etype = e["event_type"]
        if etype not in positive_types:
            continue

        w = event_weights.get(etype, 0.0)
        if w <= 0:
            continue

        # Time decay
        ts = _parse_ts(e["timestamp"])
        age_days = (ref_ts - ts).total_seconds() / 86400.0
        decay = 0.5 ** (age_days / half_life_days) if half_life_days > 0 else 1.0

        iid = e.get("item_id", "")
        item = items.get(iid)
        if item:
            profile.add_event(e, item, w, decay)

    for p in profiles.values():
        p.finalize()

    return profiles
