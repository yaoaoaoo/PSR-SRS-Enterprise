"""Service-layer data transfer objects — immutable, ORM-free."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class SearchMode(StrEnum):
    BM25 = "bm25"
    SEMANTIC = "semantic"
    RRF = "rrf"
    LINEAR = "linear"


@dataclass(frozen=True)
class SearchHit:
    """A single ranked search result with metadata."""

    item_id: str
    score: float
    rank: int
    source: str
    # Multi-source diagnostics
    bm25_score: float | None = None
    semantic_score: float | None = None
    fusion_score: float | None = None
    personalization_score: float | None = None
    original_rank: int | None = None
    # Lightweight item metadata (from items_map)
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResponse:
    """Immutable search response."""

    query_text: str
    mode: str
    personalized: bool
    user_id: str | None
    hits: list[SearchHit]
    total_candidates: int
    returned_count: int
    index_generation: int
    took_ms: float
    fallback_reason: str | None = None


@dataclass(frozen=True)
class IndexStatus:
    """Read-only index status."""

    ready: bool
    generation: int
    built_at: datetime | None
    item_count: int
    error_message: str | None = None


@dataclass(frozen=True)
class ProfileStatus:
    """Read-only profile status."""

    ready: bool
    generation: int
    built_at: datetime | None
    profile_count: int
    error_message: str | None = None


@dataclass(frozen=True)
class EvaluationReport:
    """Offline evaluation report."""

    query_count: int
    metrics: dict[str, object]
    candidate_coverage: dict[str, object] | None = None
    duration_seconds: float = 0.0
