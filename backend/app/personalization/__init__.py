"""Personalization module — user profiles, re-ranking, cold-start fallback."""

from app.personalization.evaluation import (
    compute_behavior_metrics,
    compute_candidate_coverage,
    compute_qrels_metrics,
    macro_average_dict,
)
from app.personalization.profiles import UserProfile, build_profiles
from app.personalization.reranker import (
    PersonalizationConfig,
    RankedItem,
    rerank_candidates,
)

__all__ = [
    "UserProfile",
    "build_profiles",
    "PersonalizationConfig",
    "RankedItem",
    "rerank_candidates",
    "compute_behavior_metrics",
    "compute_qrels_metrics",
    "compute_candidate_coverage",
    "macro_average_dict",
]
