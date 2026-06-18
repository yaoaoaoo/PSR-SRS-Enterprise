"""Personalization-specific result types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RankedItem:
    """A single item after personalized re-ranking.

    Carries the retrieval score, per-signal affinity scores, and the
    final personalized score for diagnostics.
    """

    item_id: str
    rank: int
    original_rank: int
    original_fusion_score: float
    normalized_retrieval_score: float
    category_affinity: float
    subcategory_affinity: float
    brand_affinity: float
    price_affinity: float
    personalized_score: float
    profile_status: str
    is_cold_start: bool
    behavior_relevance_grade: int = 0
    qrels_relevance_grade: int = 0

    @classmethod
    def from_fused_dict(
        cls,
        candidate: dict[str, str],
        rank: int,
        normalized_retrieval_score: float,
        category_affinity: float,
        subcategory_affinity: float,
        brand_affinity: float,
        price_affinity: float,
        personalized_score: float,
        profile_status: str,
        is_cold_start: bool,
        behavior_relevance_grade: int = 0,
        qrels_relevance_grade: int = 0,
    ) -> RankedItem:
        return cls(
            item_id=candidate["item_id"],
            rank=rank,
            original_rank=int(candidate["rank"]),
            original_fusion_score=float(candidate["fusion_score"]),
            normalized_retrieval_score=normalized_retrieval_score,
            category_affinity=category_affinity,
            subcategory_affinity=subcategory_affinity,
            brand_affinity=brand_affinity,
            price_affinity=price_affinity,
            personalized_score=personalized_score,
            profile_status=profile_status,
            is_cold_start=is_cold_start,
            behavior_relevance_grade=behavior_relevance_grade,
            qrels_relevance_grade=qrels_relevance_grade,
        )
