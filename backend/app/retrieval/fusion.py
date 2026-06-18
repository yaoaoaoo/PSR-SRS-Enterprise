"""Hybrid retrieval fusion — RRF and weighted linear score combination.

Combines BM25 keyword results with LSA semantic results.
Neither qrels nor user-behaviour data are used in fusion.

Identical algorithms to PSR-SRS-MVP, adapted for unified ``SearchResult``.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.retrieval.types import FusedSearchResult, SearchResult

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_VALID_NORMALIZATIONS = ("min_max",)


@dataclass
class FusionConfig:
    """Typed configuration for hybrid retrieval fusion.

    Attributes:
        candidate_k: Max candidates to consider from each channel.
        top_k_values: K cutoffs for evaluation.
        relevance_threshold: Minimum qrels grade for relevance.
        rrf_k: RRF smoothing constant (k=60 is standard).
        bm25_weight: Weight for BM25 scores in linear fusion.
        semantic_weight: Weight for semantic scores in linear fusion.
        score_normalization: Normalisation method (currently only ``"min_max"``).
    """

    candidate_k: int = 100
    top_k_values: list[int] = field(default_factory=lambda: [5, 10, 20])
    relevance_threshold: int = 1
    rrf_k: int = 60
    bm25_weight: float = 0.5
    semantic_weight: float = 0.5
    score_normalization: str = "min_max"

    @property
    def max_k(self) -> int:
        return max(self.top_k_values) if self.top_k_values else 20

    def validate(self) -> list[str]:
        """Return a list of validation errors (empty if valid)."""
        errors: list[str] = []
        if self.candidate_k < 1:
            errors.append("candidate_k must be >= 1")
        if self.candidate_k < self.max_k:
            errors.append(f"candidate_k ({self.candidate_k}) < max K ({self.max_k})")
        if not self.top_k_values:
            errors.append("top_k_values must not be empty")
        for k in self.top_k_values:
            if k <= 0 or not isinstance(k, int):
                errors.append(f"top_k_values must be positive ints, got {k}")
        if self.rrf_k <= 0:
            errors.append("rrf_k must be > 0")
        if self.bm25_weight < 0 or not math.isfinite(self.bm25_weight):
            errors.append("bm25_weight must be non-negative finite")
        if self.semantic_weight < 0 or not math.isfinite(self.semantic_weight):
            errors.append("semantic_weight must be non-negative finite")
        if self.bm25_weight + self.semantic_weight <= 0:
            errors.append("at least one weight must be > 0")
        if self.score_normalization not in _VALID_NORMALIZATIONS:
            errors.append(
                f"score_normalization must be one of {_VALID_NORMALIZATIONS}"
            )
        if self.relevance_threshold not in (1, 2, 3):
            errors.append("relevance_threshold must be 1, 2, or 3")
        return errors

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> FusionConfig:
        """Create a validated config from a dictionary."""
        valid_keys = set(cls.__dataclass_fields__.keys())
        kwargs = {k: v for k, v in data.items() if k in valid_keys}
        cfg = cls(**kwargs)  # type: ignore[arg-type]
        errs = cfg.validate()
        if errs:
            raise ValueError("\n".join(errs))
        return cfg

    @classmethod
    def from_json(cls, path: str | Path) -> FusionConfig:
        """Load config from a JSON file (convenience for offline scripts)."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)


# ---------------------------------------------------------------------------
# Candidate building
# ---------------------------------------------------------------------------

def build_candidates(
    bm25_results: Sequence[SearchResult],
    semantic_results: Sequence[SearchResult],
) -> dict[str, dict[str, Any]]:
    """Build a unified candidate dict from two result lists.

    Returns:
        ``{item_id: {"bm25_rank": int|None, "bm25_score": float|None,
                     "semantic_rank": int|None, "semantic_score": float|None,
                     "sources": tuple}}``
    """
    candidates: dict[str, dict[str, Any]] = {}

    for r in bm25_results:
        candidates[r.item_id] = {
            "bm25_rank": r.rank,
            "bm25_score": r.score,
            "semantic_rank": None,
            "semantic_score": None,
            "sources": ("bm25",),
        }

    for r in semantic_results:
        if r.item_id in candidates:
            entry = candidates[r.item_id]
            entry["semantic_rank"] = r.rank
            entry["semantic_score"] = r.score
            entry["sources"] = ("bm25", "semantic")
        else:
            candidates[r.item_id] = {
                "bm25_rank": None,
                "bm25_score": None,
                "semantic_rank": r.rank,
                "semantic_score": r.score,
                "sources": ("semantic",),
            }

    return candidates


# ---------------------------------------------------------------------------
# RRF
# ---------------------------------------------------------------------------

def fuse_rrf(
    candidates: dict[str, dict[str, Any]],
    rrf_k: int,
    top_k: int = 20,
) -> list[FusedSearchResult]:
    """Reciprocal Rank Fusion.

    RRF(d) = Σ 1 / (k + rank_r(d))

    Args:
        candidates: Output of ``build_candidates``.
        rrf_k: RRF smoothing constant (k=60 is standard).
        top_k: Max results to return.

    Returns:
        Ranked fused results.
    """
    scored: list[tuple[float, str, dict]] = []
    for item_id, info in candidates.items():
        score = 0.0
        if info["bm25_rank"] is not None:
            score += 1.0 / (rrf_k + info["bm25_rank"])
        if info["semantic_rank"] is not None:
            score += 1.0 / (rrf_k + info["semantic_rank"])
        scored.append((score, item_id, info))

    # Score descending, item_id ascending for ties
    scored.sort(key=lambda x: (-x[0], x[1]))

    results: list[FusedSearchResult] = []
    for rank, (score, item_id, info) in enumerate(scored[:top_k], start=1):
        results.append(FusedSearchResult(
            item_id=item_id,
            rank=rank,
            fusion_score=score,
            bm25_rank=info["bm25_rank"],
            semantic_rank=info["semantic_rank"],
            bm25_score=info["bm25_score"],
            semantic_score=info["semantic_score"],
            sources=info["sources"],
        ))
    return results


# ---------------------------------------------------------------------------
# Linear fusion (min-max normalised)
# ---------------------------------------------------------------------------

def _normalize_scores(scores: list[float]) -> list[float]:
    """Min-max normalise a list of scores to [0, 1].

    If all scores are identical (or only one score), returns all 1.0.
    """
    if not scores:
        return []
    mn = min(scores)
    mx = max(scores)
    if mx == mn:
        return [1.0] * len(scores)
    denom = mx - mn
    return [(s - mn) / denom for s in scores]


def fuse_linear(
    candidates: dict[str, dict[str, Any]],
    bm25_weight: float,
    semantic_weight: float,
    top_k: int = 20,
) -> list[FusedSearchResult]:
    """Weighted linear score fusion with per-channel min-max normalisation.

    linear_score(d) = bm25_weight × norm_bm25(d) + semantic_weight × norm_sem(d)

    Missing in a source → that source's contribution is 0.
    """
    # Normalise weights to sum to 1
    total_w = bm25_weight + semantic_weight
    w_bm25 = bm25_weight / total_w if total_w > 0 else 0.5
    w_sem = semantic_weight / total_w if total_w > 0 else 0.5

    # Collect BM25 scores and semantic scores for normalisation
    items = list(candidates.items())
    bm25_scores_raw = [
        info["bm25_score"]
        for _, info in items
        if info["bm25_score"] is not None and math.isfinite(info["bm25_score"])
    ]
    sem_scores_raw = [
        info["semantic_score"]
        for _, info in items
        if info["semantic_score"] is not None and math.isfinite(info["semantic_score"])
    ]

    # Normalise per source
    bm25_norm = _normalize_scores(bm25_scores_raw)
    sem_norm = _normalize_scores(sem_scores_raw)

    # Map normalised scores back to item_ids
    bm25_norm_map: dict[str, float] = {}
    idx = 0
    for item_id, info in items:
        if info["bm25_score"] is not None and math.isfinite(info["bm25_score"]):
            bm25_norm_map[item_id] = bm25_norm[idx]
            idx += 1

    sem_norm_map: dict[str, float] = {}
    idx = 0
    for item_id, info in items:
        if info["semantic_score"] is not None and math.isfinite(info["semantic_score"]):
            sem_norm_map[item_id] = sem_norm[idx]
            idx += 1

    # Score and sort
    scored: list[tuple[float, str, dict, float, float]] = []
    for item_id, info in items:
        bm25_n = bm25_norm_map.get(item_id, 0.0)
        sem_n = sem_norm_map.get(item_id, 0.0)
        linear = w_bm25 * bm25_n + w_sem * sem_n
        scored.append((linear, item_id, info, bm25_n, sem_n))

    scored.sort(key=lambda x: (-x[0], x[1]))

    results: list[FusedSearchResult] = []
    for rank, (score, item_id, info, bm25_n, sem_n) in enumerate(scored[:top_k], start=1):
        results.append(FusedSearchResult(
            item_id=item_id,
            rank=rank,
            fusion_score=score,
            bm25_rank=info["bm25_rank"],
            semantic_rank=info["semantic_rank"],
            bm25_score=info["bm25_score"],
            semantic_score=info["semantic_score"],
            bm25_normalized_score=bm25_n if info["bm25_rank"] is not None else None,
            semantic_normalized_score=sem_n if info["semantic_rank"] is not None else None,
            sources=info["sources"],
        ))
    return results
