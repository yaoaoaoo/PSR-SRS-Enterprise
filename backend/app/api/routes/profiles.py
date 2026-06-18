"""Profile refresh and status API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.api.dependencies import get_profile_service
from app.schemas.common import ApiMeta, DataResponse, ErrorDetail, ErrorResponse
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profiles", tags=["Profiles"])


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "")


@router.get("/status", summary="Get profile status")
def get_profile_status(
    request: Request,
    profile_svc: ProfileService = Depends(get_profile_service),
):
    st = profile_svc.get_status()
    snap = profile_svc.get_snapshot()
    behavior_count = 0
    base_only = 0
    if snap:
        for _uid, p in snap.profiles.items():
            if p.profile_status == "warm" and p.positive_event_count > 0:
                behavior_count += 1
            else:
                base_only += 1
        base_only = max(0, snap.profile_count - behavior_count)

    return DataResponse(
        meta=ApiMeta(request_id=_rid(request)),
        data={
            "generation": st.generation,
            "profile_count": st.profile_count,
            "behavior_profile_count": behavior_count,
            "base_only_profile_count": base_only,
            "last_built_at": st.built_at.isoformat() if st.built_at else None,
            "ready": st.ready,
        },
    )


@router.post("/refresh", summary="Refresh all user profiles")
def refresh_all_profiles(
    request: Request,
    profile_svc: ProfileService = Depends(get_profile_service),
    only_with_events: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=200),
):
    result = profile_svc.refresh_all(
        only_with_events=only_with_events, limit=limit,
    )
    return DataResponse(
        meta=ApiMeta(request_id=_rid(request)),
        data={
            "requested_users": result.requested_users,
            "refreshed_users": result.refreshed_users,
            "unchanged_users": result.unchanged_users,
            "failed_users": result.failed_users,
            "total_events_used": result.total_events_used,
            "generation": result.generation,
            "built_at": result.built_at.isoformat(),
        },
    )


@router.post("/{user_id}/refresh", summary="Refresh a single user profile")
def refresh_user_profile(
    user_id: str,
    request: Request,
    profile_svc: ProfileService = Depends(get_profile_service),
):
    try:
        result = profile_svc.refresh_user(user_id)
    except ValueError as e:
        status = 404 if "not_found" in str(e) else 400
        return JSONResponse(
            status_code=status,
            content=ErrorResponse(
                error=ErrorDetail(code=str(e), message=str(e)),
                meta=ApiMeta(request_id=_rid(request)),
            ).model_dump(),
        )

    return DataResponse(
        meta=ApiMeta(request_id=_rid(request)),
        data={
            "user_id": result.user_id,
            "generation": result.generation,
            "source": result.source,
            "event_count": result.event_count,
            "ignored_event_count": result.ignored_event_count,
            "built_at": result.built_at.isoformat(),
            "last_event_at": result.last_event_at.isoformat() if result.last_event_at else None,
            "profile": result.profile,
        },
    )
