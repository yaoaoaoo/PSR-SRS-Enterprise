"""SearchService — orchestrate multi-mode retrieval with optional personalization."""

from __future__ import annotations

import logging
import time

from app.core.service_config import service_settings
from app.retrieval.fusion import build_candidates, fuse_linear, fuse_rrf
from app.retrieval.types import SearchResult as AlgSearchResult
from app.services.errors import (
    InvalidSearchRequestError,
    UnsupportedSearchModeError,
)
from app.services.index_manager import IndexManager, IndexSnapshot
from app.services.personalization_service import (
    PersonalizationService,
)
from app.services.types import SearchHit, SearchMode, SearchResponse

logger = logging.getLogger(__name__)


def _candidate_pool_size(top_k: int, item_count: int) -> int:
    pool = max(top_k * service_settings.SEARCH_CANDIDATE_MULTIPLIER,
               service_settings.SEARCH_MIN_CANDIDATES)
    return min(pool, item_count)


def _make_hits(
    results: list[AlgSearchResult],
    source: str,
    snapshot: IndexSnapshot,
    bm25_scores: dict[str, float] | None = None,
    sem_scores: dict[str, float] | None = None,
) -> list[SearchHit]:
    """Convert algorithm results to SearchHit DTOs with metadata."""
    hits: list[SearchHit] = []
    items_map = snapshot.items_map
    for r in results:
        meta = dict(items_map.get(r.item_id, {}))
        b25 = bm25_scores.get(r.item_id) if bm25_scores else None
        sem = sem_scores.get(r.item_id) if sem_scores else None
        hits.append(SearchHit(
            item_id=r.item_id,
            score=r.score if r.score is not None else 0.0,
            rank=r.rank or 0,
            source=source,
            bm25_score=b25,
            semantic_score=sem,
            fusion_score=r.score if source in ("rrf", "linear") else None,
            original_rank=r.rank,
            metadata=meta,
        ))
    return hits


class SearchService:
    """Orchestrates retrieval and optional personalization."""

    def __init__(
        self,
        index_manager: IndexManager,
        personalization_service: PersonalizationService | None = None,
    ):
        self._index_manager = index_manager
        self._personalization = personalization_service

    def search(
        self,
        query_text: str,
        *,
        mode: SearchMode = SearchMode.LINEAR,
        top_k: int = 10,
        user_id: str | None = None,
        personalize: bool = False,
    ) -> SearchResponse:
        """Execute a search and optionally personalize results."""
        t0 = time.monotonic()

        # Validate
        query_text = query_text.strip()
        if not query_text:
            raise InvalidSearchRequestError("query_text must not be empty")
        if top_k < 1:
            raise InvalidSearchRequestError("top_k must be >= 1")
        if top_k > service_settings.SEARCH_MAX_TOP_K:
            raise InvalidSearchRequestError(
                f"top_k {top_k} exceeds max {service_settings.SEARCH_MAX_TOP_K}"
            )
        if personalize and not user_id:
            raise InvalidSearchRequestError("user_id required when personalize=True")

        snapshot = self._index_manager.get_snapshot()

        pool = _candidate_pool_size(top_k, snapshot.item_count)

        # Execute retrieval
        if mode == SearchMode.BM25:
            alg_results = snapshot.bm25_index.search(query_text, top_k=pool)
            hits = _make_hits(alg_results, "bm25", snapshot)
        elif mode == SearchMode.SEMANTIC:
            alg_results = snapshot.semantic_index.search(query_text, top_k=pool)
            hits = _make_hits(alg_results, "semantic", snapshot)
        elif mode in (SearchMode.RRF, SearchMode.LINEAR):
            bm25_raw = snapshot.bm25_index.search(query_text, top_k=pool)
            sem_raw = snapshot.semantic_index.search(query_text, top_k=pool)

            # Convert to algorithm types for fusion
            bm25_alg = [AlgSearchResult(item_id=r.item_id, score=r.score, rank=r.rank or 0, source="bm25") for r in bm25_raw]
            sem_alg = [AlgSearchResult(item_id=r.item_id, score=r.score, rank=r.rank or 0, source="semantic") for r in sem_raw]

            candidates = build_candidates(bm25_alg, sem_alg)

            if mode == SearchMode.RRF:
                fused = fuse_rrf(candidates, rrf_k=60, top_k=top_k)
                source = "rrf"
            else:
                fused = fuse_linear(candidates, bm25_weight=0.5, semantic_weight=0.5, top_k=top_k)
                source = "linear"

            # Convert fused results
            hits = []
            items_map = snapshot.items_map
            for r in fused:
                meta = dict(items_map.get(r.item_id, {}))
                hits.append(SearchHit(
                    item_id=r.item_id, score=r.fusion_score, rank=r.rank,
                    source=source,
                    bm25_score=r.bm25_score, semantic_score=r.semantic_score,
                    fusion_score=r.fusion_score, metadata=meta,
                ))
        else:
            raise UnsupportedSearchModeError(f"Unknown mode: {mode}")

        # Personalization
        personalized = False
        fallback_reason = None
        if personalize and self._personalization:
            result = self._personalization.rerank(
                candidates=hits, user_id=user_id,  # type: ignore[arg-type]
                top_k=top_k, index_snapshot=snapshot,
            )
            personalized = result.applied
            fallback_reason = result.fallback_reason
            hits = result.hits

        hits = hits[:top_k]

        took_ms = (time.monotonic() - t0) * 1000

        return SearchResponse(
            query_text=query_text,
            mode=mode.value,
            personalized=personalized,
            user_id=user_id,
            hits=hits,
            total_candidates=pool,
            returned_count=len(hits),
            index_generation=snapshot.generation,
            took_ms=round(took_ms, 2),
            fallback_reason=fallback_reason,
        )
