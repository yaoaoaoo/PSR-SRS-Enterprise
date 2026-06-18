"""Search API route."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_search_service
from app.schemas.common import DataResponse
from app.schemas.search import SearchHitSchema, SearchRequest, SearchResponse
from app.services.errors import IndexNotReadyError, InvalidSearchRequestError
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=DataResponse[SearchResponse])
def search(
    body: SearchRequest,
    request: Request,
    svc: SearchService = Depends(get_search_service),
):
    """Execute a search query with optional personalization."""
    try:
        result = svc.search(
            query_text=body.query.strip(),
            mode=body.mode,
            top_k=body.top_k,
            user_id=body.user_id,
            personalize=body.personalize,
        )
    except IndexNotReadyError:
        raise
    except InvalidSearchRequestError:
        raise

    hits = [
        SearchHitSchema(
            item_id=h.item_id,
            rank=h.rank,
            score=h.score,
            source=h.source,
            original_rank=h.original_rank,
            bm25_score=h.bm25_score,
            semantic_score=h.semantic_score,
            fusion_score=h.fusion_score,
            personalization_score=h.personalization_score,
            title=str(h.metadata.get("title", "")),
            category=str(h.metadata.get("category", "")),
            subcategory=str(h.metadata.get("subcategory", "")),
            brand=str(h.metadata.get("brand", "")),
            price=str(h.metadata.get("price", "")),
            quality_score=float(h.metadata.get("quality_score", 0))
            if h.metadata.get("quality_score") is not None
            else None,
            popularity_score=float(h.metadata.get("popularity_score", 0))
            if h.metadata.get("popularity_score") is not None
            else None,
            is_cold_start=bool(h.metadata.get("is_cold_start"))
            if h.metadata.get("is_cold_start") is not None
            else None,
        )
        for h in result.hits
    ]

    rid = getattr(request.state, "request_id", "")
    return DataResponse(
        meta={"request_id": rid, "api_version": "v1"},
        data=SearchResponse(
            query=result.query_text,
            mode=result.mode,
            personalization_requested=body.personalize,
            personalization_applied=result.personalized,
            user_id=result.user_id,
            fallback_reason=result.fallback_reason,
            total_candidates=result.total_candidates,
            returned_count=result.returned_count,
            index_generation=result.index_generation,
            took_ms=result.took_ms,
            hits=hits,
        ),
    )
