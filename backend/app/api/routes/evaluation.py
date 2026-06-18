"""Evaluation API routes."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import (
    get_evaluation_service,
    get_profile_service,
    get_search_service,
)
from app.personalization.evaluation import compute_candidate_coverage
from app.schemas.common import ApiMeta, DataResponse, ErrorDetail, ErrorResponse
from app.schemas.evaluation import (
    CandidateCoverageRequest,
    CandidateCoverageResponse,
    EvaluationQueriesRequest,
    EvaluationResponse,
)
from app.services.evaluation_service import EvaluationService
from app.services.types import SearchMode

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "")


@router.post("/queries", response_model=DataResponse[EvaluationResponse])
def evaluate_queries(
    body: EvaluationQueriesRequest,
    request: Request,
    svc: EvaluationService = Depends(get_evaluation_service),
):
    query_texts = [q.query_id for q in body.queries]
    report = svc.evaluate_queries(query_texts, ks=body.ks)

    return DataResponse(
        data=EvaluationResponse(
            query_count=report.query_count,
            metrics=report.metrics,
            candidate_coverage=report.candidate_coverage,
            took_ms=round(report.duration_seconds * 1000, 2),
            ks=body.ks,
        ),
    )


@router.post(
    "/candidate-coverage",
    response_model=DataResponse[CandidateCoverageResponse],
    summary="Compute candidate coverage metrics",
)
def candidate_coverage(
    body: CandidateCoverageRequest,
    request: Request,
):
    t0 = time.monotonic()

    test_requests: dict[str, dict] = {}
    candidates_by_qid: dict[str, list[dict]] = {}
    eligible_rids: list[str] = []

    for req_item in body.requests:
        rid = req_item.request_id
        qid = req_item.query_id
        eligible_rids.append(rid)

        # Count positive items — 1 if any candidate, else 0 (simplified)
        test_requests[rid] = {
            "query_id": qid,
            "items": {iid: 1 for iid in req_item.candidate_item_ids},
            "profile_status": "warm",  # simplified
        }
        candidates_by_qid[qid] = [
            {"item_id": iid} for iid in req_item.candidate_item_ids
        ]

    result = compute_candidate_coverage(
        test_requests, candidates_by_qid, eligible_rids,
    )

    took_ms = (time.monotonic() - t0) * 1000

    return DataResponse(
        data=CandidateCoverageResponse(
            eligible_requests=result["eligible_positive_request_count"],
            covered_requests=result["covered_positive_request_count"],
            uncovered_requests=result["uncovered_positive_request_count"],
            request_level_coverage=round(
                result["request_level_candidate_positive_coverage"], 6,
            ),
            total_positive_items=result.get("total_positive_item_count", 0),
            covered_positive_items=result.get("covered_positive_item_count", 0),
            item_level_recall=round(
                result.get("item_level_candidate_positive_recall", 0.0), 6,
            ),
            took_ms=round(took_ms, 2),
        ),
    )


@router.post("/profile-impact", summary="Profile impact evaluation")
def profile_impact(
    body: dict,
    request: Request,
    search_svc=Depends(get_search_service),
    profile_svc=Depends(get_profile_service),
):
    user_id = body.get("user_id", "")
    query_id = body.get("query_id", "")
    k = int(body.get("k", 10))

    if not user_id or not query_id:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=422, content=ErrorResponse(
            error=ErrorDetail(code="validation", message="user_id and query_id required"),
            meta=ApiMeta(request_id=_rid(request)),
        ).model_dump())
    if k < 1 or k > 100:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=422, content=ErrorResponse(
            error=ErrorDetail(code="validation", message="k must be 1-100"),
            meta=ApiMeta(request_id=_rid(request)),
        ).model_dump())

    gen = profile_svc.get_status().generation

    # Base ranking (non-personalized)
    base_resp = search_svc.search(query_id, mode=SearchMode.LINEAR, top_k=k, personalize=False)
    # Personalized ranking
    pers_resp = search_svc.search(query_id, mode=SearchMode.LINEAR, top_k=k,
                                  user_id=user_id, personalize=True)

    base_items = [h.item_id for h in base_resp.hits]
    pers_items = [h.item_id for h in pers_resp.hits]
    overlap = len(set(base_items) & set(pers_items))

    changed = 0
    promoted: list[dict] = []
    demoted: list[dict] = []
    pers_ranks = {h.item_id: h.rank for h in pers_resp.hits}
    for h in base_resp.hits[:k]:
        pr = pers_ranks.get(h.item_id, 999)
        if pr != h.rank:
            changed += 1
        if pr < h.rank:
            promoted.append({"item_id": h.item_id, "base_position": h.rank, "personalized_position": pr, "delta": pr - h.rank})
        elif pr > h.rank:
            demoted.append({"item_id": h.item_id, "base_position": h.rank, "personalized_position": pr, "delta": pr - h.rank})

    resp_data = {
        "user_id": user_id,
        "query_id": query_id,
        "profile_generation": gen,
        "k": k,
        "base_ranking": base_items[:k],
        "personalized_ranking": pers_items[:k],
        "changed_positions": changed,
        "top_k_overlap": round(overlap / k, 4) if k > 0 else 0.0,
        "promoted_items": promoted,
        "demoted_items": demoted,
    }

    return DataResponse(meta=ApiMeta(request_id=_rid(request)), data=resp_data)
