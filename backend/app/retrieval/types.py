"""Common result types shared across retrieval modules.

All result types are frozen dataclasses — safe for caching, hashing, and
serialisation.  They carry no database, ORM, or FastAPI dependency.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResult:
    """A single ranked search result from any retrieval channel.

    Attributes:
        item_id: Unique item identifier (string).
        score: Relevance score (higher = more relevant).
        rank: 1-based rank position (set by the caller / fusion).
        source: Optional label identifying the retrieval channel
                (e.g. ``"bm25"``, ``"semantic"``, ``"rrf"``).
    """

    item_id: str
    score: float
    rank: int | None = None
    source: str | None = None


@dataclass(frozen=True)
class FusedSearchResult:
    """A result produced by hybrid fusion of two or more channels.

    Carries per-channel metadata for diagnostics.
    """

    item_id: str
    rank: int
    fusion_score: float
    sources: tuple[str, ...] = ()
    # Per-channel ranks and scores (None when channel didn't return item)
    bm25_rank: int | None = None
    semantic_rank: int | None = None
    bm25_score: float | None = None
    semantic_score: float | None = None
    # Normalized scores (for linear fusion diagnostics)
    bm25_normalized_score: float | None = None
    semantic_normalized_score: float | None = None
