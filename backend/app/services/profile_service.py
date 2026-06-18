"""ProfileService — build and serve user profiles, with behavior-based refresh."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import sessionmaker

from app.personalization.profiles import UserProfile, build_profiles
from app.repositories.algorithm_inputs import build_profile_input
from app.repositories.event_repository import EventRepository
from app.repositories.item_repository import ItemRepository
from app.repositories.user_repository import UserRepository
from app.services.types import ProfileStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProfileSnapshot:
    generation: int
    built_at: datetime
    profile_count: int
    profiles: dict[str, UserProfile]
    source_distribution: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class RefreshResult:
    user_id: str
    generation: int
    source: str  # "base", "behavior", "combined", "cold_start"
    event_count: int
    ignored_event_count: int
    built_at: datetime
    last_event_at: datetime | None = None
    profile: dict | None = None


@dataclass(frozen=True)
class BatchRefreshResult:
    requested_users: int
    refreshed_users: int
    unchanged_users: int
    failed_users: int
    total_events_used: int
    generation: int
    built_at: datetime


_TS = "2026-01-01T00:00:00+00:00"


class ProfileService:
    def __init__(
        self,
        session_factory: sessionmaker,
        event_weights: dict[str, float] | None = None,
        half_life_days: float = 30.0,
        base_profile_weight: float = 0.4,
        behavior_profile_weight: float = 0.6,
        recency_decay_enabled: bool = False,
    ):
        self._session_factory = session_factory
        self._event_weights = event_weights or {
            "click": 1.0, "favorite": 2.0, "add_to_cart": 3.0, "purchase": 5.0,
        }
        # When recency decay is disabled, use a very large half-life so all
        # events contribute equally regardless of their timestamp.
        self._half_life_days = half_life_days if recency_decay_enabled else 1e12
        self._base_weight = base_profile_weight
        self._behavior_weight = behavior_profile_weight

        self._lock = threading.RLock()
        self._snapshot: ProfileSnapshot | None = None
        self._generation: int = 0
        self._error_message: str | None = None

    # ------------------------------------------------------------------
    # Build (original — all users from events)
    # ------------------------------------------------------------------

    def build(self) -> None:
        with self._lock:
            self._build_unlocked()

    def rebuild(self) -> None:
        self.build()

    def _build_unlocked(self) -> None:
        logger.info("Profile build started")
        t0 = datetime.now(UTC)
        session = self._session_factory()
        try:
            event_repo = EventRepository(session)
            item_repo = ItemRepository(session)
            user_repo = UserRepository(session)
            train_events, items_map, users_map = build_profile_input(
                event_repo, item_repo, user_repo,
            )
        finally:
            session.close()

        if not users_map:
            self._error_message = "No users found"
            return

        try:
            profiles = build_profiles(
                train_events, items_map, users_map,
                self._event_weights, self._half_life_days,
            )
        except Exception:
            self._error_message = "Profile build failed"
            logger.exception(self._error_message)
            return

        self._generation += 1
        self._snapshot = ProfileSnapshot(
            generation=self._generation,
            built_at=datetime.now(UTC),
            profile_count=len(profiles),
            profiles=profiles,
        )
        self._error_message = None
        elapsed = (datetime.now(UTC) - t0).total_seconds()
        logger.info("Profile build completed gen=%d count=%d %.2fs", self._generation, len(profiles), elapsed)

    # ------------------------------------------------------------------
    # Single-user behavior refresh
    # ------------------------------------------------------------------

    def refresh_user(self, user_id: str) -> RefreshResult:
        session = self._session_factory()
        try:
            user_repo = UserRepository(session)
            user = user_repo.get_by_id(user_id)
            if user is None:
                raise ValueError("user_not_found")

            event_repo = EventRepository(session)
            # Read recent events for this user
            raw_events = event_repo.list_for_user(
                user_id, limit=5000,
                event_type=None,
            )
            positive_types = {"click", "favorite", "add_to_cart", "purchase"}
            events = [e for e in raw_events if e.event_type in positive_types]

            item_repo = ItemRepository(session)
            items_map = item_repo.build_items_map()
            # Filter to only items that exist
            valid_events = [e for e in events if e.item_id in items_map]
            ignored = len(events) - len(valid_events)

            # Build behavior profile
            users_map = {user_id: {"is_cold_start": str(user.is_cold_start).lower()}}
            event_dicts = [
                {
                    "user_id": e.user_id,
                    "event_type": e.event_type,
                    "item_id": e.item_id,
                    "timestamp": e.timestamp.isoformat(),
                    "session_id": e.session_id,
                }
                for e in valid_events
            ]
            profiles = build_profiles(
                event_dicts, items_map, users_map,
                self._event_weights, self._half_life_days,
            )
            behavior_profile = profiles.get(user_id)
            last_event_at = max((e.timestamp for e in valid_events), default=None)

        finally:
            session.close()

        # Merge with base profile
        with self._lock:
            old_snap = self._snapshot
            base_profile = old_snap.profiles.get(user_id) if old_snap else None

            final_profile, source = self._merge_profiles(
                user, base_profile, behavior_profile,
            )

            # Update snapshot
            self._snapshot = self._snapshot or ProfileSnapshot(
                generation=0, built_at=datetime.now(UTC), profile_count=0,
                profiles={},
            )
            new_profiles = dict(self._snapshot.profiles)
            new_profiles[user_id] = final_profile
            self._generation += 1

            dist = dict(self._snapshot.source_distribution or {})
            dist[source] = dist.get(source, 0) + 1

            self._snapshot = ProfileSnapshot(
                generation=self._generation,
                built_at=datetime.now(UTC),
                profile_count=len(new_profiles),
                profiles=new_profiles,
                source_distribution=dist,
            )

        return RefreshResult(
            user_id=user_id,
            generation=self._generation,
            source=source,
            event_count=len(valid_events),
            ignored_event_count=ignored,
            built_at=datetime.now(UTC),
            last_event_at=last_event_at,
            profile={
                "category_weights": dict(final_profile.category_weights),
                "brand_weights": dict(final_profile.brand_weights),
                "mean_log_price": final_profile.mean_log_price,
            },
        )

    # ------------------------------------------------------------------
    # Batch refresh
    # ------------------------------------------------------------------

    def refresh_all(
        self,
        *,
        only_with_events: bool = False,
        limit: int = 100,
    ) -> BatchRefreshResult:
        session = self._session_factory()
        try:
            user_repo = UserRepository(session)
            users = user_repo.list(limit=limit)
        finally:
            session.close()

        requested = len(users)
        refreshed = 0
        unchanged = 0
        failed = 0
        total_events = 0

        for user in users:
            try:
                result = self.refresh_user(user.user_id)
                total_events += result.event_count
                if result.event_count > 0:
                    refreshed += 1
                else:
                    unchanged += 1
            except Exception:
                failed += 1

        return BatchRefreshResult(
            requested_users=requested,
            refreshed_users=refreshed,
            unchanged_users=unchanged,
            failed_users=failed,
            total_events_used=total_events,
            generation=self._generation,
            built_at=datetime.now(UTC),
        )

    # ------------------------------------------------------------------
    # Profile merge
    # ------------------------------------------------------------------

    def _merge_profiles(
        self,
        user,
        base_profile: UserProfile | None,
        behavior_profile: UserProfile | None,
    ) -> tuple[UserProfile, str]:
        """Merge base and behavior profiles with configured weights."""
        is_cold = user.is_cold_start if user else False

        # No behavior data → use base
        if behavior_profile is None or behavior_profile.profile_status in (
            "cold_start", "no_history", "no_positive", "empty",
        ):
            if base_profile is not None:
                return base_profile, "base"
            # Cold-start fallback
            p = UserProfile(user.user_id, is_cold_start=is_cold)
            p.finalize()
            return p, "cold_start"

        # No base → use behavior only
        if base_profile is None or base_profile.profile_status in (
            "cold_start", "no_history", "no_positive", "empty",
        ):
            behavior_profile.profile_status = "warm"
            return behavior_profile, "behavior"

        # Both exist → weighted merge
        combined = UserProfile(user.user_id)
        bw = self._base_weight
        bhw = self._behavior_weight

        # Merge category weights
        for cat, w in base_profile.category_weights.items():
            combined._cat_scores[cat] = w * bw
        for cat, w in behavior_profile.category_weights.items():
            combined._cat_scores[cat] = combined._cat_scores.get(cat, 0) + w * bhw

        # Merge brand weights
        for brand, w in base_profile.brand_weights.items():
            combined._brand_scores[brand] = w * bw
        for brand, w in behavior_profile.brand_weights.items():
            combined._brand_scores[brand] = combined._brand_scores.get(brand, 0) + w * bhw

        # Merge price
        bp = base_profile.mean_log_price
        bhp = behavior_profile.mean_log_price
        if bp is not None and bhp is not None:
            combined._price_log_sum = bp * bw + bhp * bhw
            combined._price_weight_sum = 1.0
        elif bhp is not None:
            combined._price_log_sum = bhp
            combined._price_weight_sum = 1.0
        elif bp is not None:
            combined._price_log_sum = bp
            combined._price_weight_sum = 1.0

        combined.positive_event_count = (
            (base_profile.positive_event_count or 0) +
            (behavior_profile.positive_event_count or 0)
        )
        combined.profile_status = "warm"
        combined.is_cold_start = False
        return combined, "combined"

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_profile(self, user_id: str) -> UserProfile | None:
        with self._lock:
            snap = self._snapshot
        if snap is None:
            return None
        return snap.profiles.get(user_id)

    def get_snapshot(self) -> ProfileSnapshot | None:
        with self._lock:
            return self._snapshot

    def get_status(self) -> ProfileStatus:
        with self._lock:
            snap = self._snapshot
            gen = self._generation
            err = self._error_message
        if snap is not None:
            return ProfileStatus(
                ready=True, generation=snap.generation,
                built_at=snap.built_at, profile_count=snap.profile_count,
            )
        return ProfileStatus(
            ready=False, generation=gen,
            built_at=None, profile_count=0, error_message=err,
        )

    def is_ready(self) -> bool:
        return self.get_status().ready

    def invalidate(self) -> None:
        with self._lock:
            self._snapshot = None
            self._error_message = None
