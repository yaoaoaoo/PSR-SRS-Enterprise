"""PersonalizationService — re-rank search results using user profiles."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.personalization.reranker import PersonalizationConfig, rerank_candidates
from app.services.index_manager import IndexSnapshot
from app.services.profile_service import ProfileService
from app.services.types import SearchHit

logger = logging.getLogger(__name__)

FALLBACK_UNKNOWN_USER = "unknown_user"
FALLBACK_COLD_START = "cold_start_user"
FALLBACK_NO_PROFILE = "no_profile"
FALLBACK_PROFILES_NOT_READY = "profiles_not_ready"
FALLBACK_EMPTY_CANDIDATES = "empty_candidates"
FALLBACK_NONE = "none"


@dataclass(frozen=True)
class PersonalizationResult:
    hits: list[SearchHit]
    applied: bool
    fallback_reason: str


class PersonalizationService:
    """Re-ranks search candidates using user profiles."""

    def __init__(
        self,
        profile_service: ProfileService,
        config: PersonalizationConfig | None = None,
    ):
        self._profile_service = profile_service
        self._config = config or PersonalizationConfig()

    def rerank(
        self,
        candidates: list[SearchHit],
        *,
        user_id: str,
        top_k: int,
        index_snapshot: IndexSnapshot,
    ) -> PersonalizationResult:
        """Re-rank *candidates* for *user_id*, returning top *top_k* hits."""
        if not candidates:
            return PersonalizationResult(
                hits=[], applied=False, fallback_reason=FALLBACK_EMPTY_CANDIDATES,
            )

        # Get profile
        profile = self._profile_service.get_profile(user_id)
        if profile is None:
            # User doesn't exist at all — check if profiles were even built
            if not self._profile_service.is_ready():
                return PersonalizationResult(
                    hits=list(candidates[:top_k]),
                    applied=False,
                    fallback_reason=FALLBACK_PROFILES_NOT_READY,
                )
            return PersonalizationResult(
                hits=list(candidates[:top_k]),
                applied=False,
                fallback_reason=FALLBACK_UNKNOWN_USER,
            )

        # Convert candidates to dict form for reranker
        cand_dicts = [
            {
                "item_id": h.item_id,
                "rank": str(h.rank),
                "fusion_score": str(h.fusion_score if h.fusion_score is not None else h.score),
            }
            for h in candidates
        ]

        items_map = index_snapshot.items_map
        ranked = rerank_candidates(cand_dicts, profile, items_map, self._config)

        # Check if cold-start fallback was applied
        applied = profile.profile_status == "warm"
        fallback = FALLBACK_COLD_START if profile.is_cold_start else (
            FALLBACK_NONE if applied else FALLBACK_NO_PROFILE
        )

        hits: list[SearchHit] = []
        for r in ranked[:top_k]:
            meta = items_map.get(r.item_id, {})
            hits.append(SearchHit(
                item_id=r.item_id,
                score=r.personalized_score,
                rank=r.rank,
                source="personalized",
                fusion_score=r.original_fusion_score,
                personalization_score=r.personalized_score,
                original_rank=r.original_rank,
                metadata=dict(meta),
            ))

        return PersonalizationResult(
            hits=hits, applied=applied, fallback_reason=fallback,
        )
