"""Users API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_profile_service
from app.repositories.user_repository import UserRepository
from app.schemas.common import (
    ApiMeta,
    DataResponse,
    ErrorDetail,
    ErrorResponse,
    ListResponse,
    PaginationMeta,
)
from app.schemas.user import ProfileResponse, UserSchema
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=ListResponse[UserSchema])
def list_users(session: Session = Depends(get_db_session)):
    repo = UserRepository(session)
    users = repo.list(limit=100)
    total = repo.count()
    return ListResponse(
        data=[_to_schema(u) for u in users],
        pagination=PaginationMeta(offset=0, limit=100, total=total, returned=len(users)),
    )


@router.get("/{user_id}", response_model=DataResponse[UserSchema])
def get_user(user_id: str, session: Session = Depends(get_db_session)):
    repo = UserRepository(session)
    user = repo.get_by_id(user_id)
    if user is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error=ErrorDetail(code="not_found", message=f"User {user_id!r} not found"),
                meta=ApiMeta(),
            ).model_dump(),
        )
    return DataResponse(data=_to_schema(user))


@router.get("/{user_id}/profile", response_model=DataResponse[ProfileResponse])
def get_user_profile(
    user_id: str,
    request: Request,
    profile_svc: ProfileService = Depends(get_profile_service),
    session: Session = Depends(get_db_session),
):
    if not profile_svc.is_ready():
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error=ErrorDetail(code="profile_not_ready", message="Profiles not built"),
                meta=ApiMeta(),
            ).model_dump(),
        )

    repo = UserRepository(session)
    user = repo.get_by_id(user_id)
    if user is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error=ErrorDetail(code="not_found", message=f"User {user_id!r} not found"),
                meta=ApiMeta(),
            ).model_dump(),
        )

    p = profile_svc.get_profile(user_id)
    status_msg = "warm" if p and p.profile_status == "warm" else (
        "cold_start" if user.is_cold_start else "no_behavior"
    )

    return DataResponse(data=ProfileResponse(
        user_id=user_id,
        status=status_msg,
        generation=profile_svc.get_status().generation,
        built_at=profile_svc.get_status().built_at,
        is_cold_start=user.is_cold_start,
        category_weights=p.category_weights if p else {},
        brand_weights=p.brand_weights if p else {},
        mean_log_price=p.mean_log_price if p else None,
        fallback_reason=None,
    ))


def _to_schema(user) -> UserSchema:
    cats = user.preferred_categories if isinstance(user.preferred_categories, list) else []
    brands = user.preferred_brands if isinstance(user.preferred_brands, list) else []
    return UserSchema(
        user_id=user.user_id,
        preferred_categories=cats,
        preferred_brands=brands,
        price_preference=user.price_preference,
        activity_level=user.activity_level,
        is_cold_start=user.is_cold_start,
        created_at=user.created_at,
    )
