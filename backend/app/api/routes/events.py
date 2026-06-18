"""Event API routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.schemas.common import (
    ApiMeta,
    DataResponse,
    ErrorDetail,
    ErrorResponse,
    ListResponse,
    PaginationMeta,
)
from app.schemas.event import CreateEventRequest, EventResponse, EventStatsResponse
from app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["Events"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


@router.post("", response_model=DataResponse[EventResponse], status_code=201)
def create_event(
    body: CreateEventRequest,
    request: Request,
    session: Session = Depends(get_db_session),
):
    svc = EventService(session)
    try:
        event = svc.create_event(
            event_id=body.event_id,
            event_type=body.event_type,
            request_id=body.request_id,
            session_id=body.session_id,
            user_id=body.user_id,
            query_id=body.query_id,
            query_text=body.query_text,
            item_id=body.item_id,
            position=body.position,
            occurred_at=body.occurred_at,
            click_duration_ms=body.click_duration_ms,
            add_to_cart_quantity=body.add_to_cart_quantity,
            purchase_amount=body.purchase_amount,
            client_event_id=body.client_event_id,
        )
        session.commit()
    except ValueError as e:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=ErrorDetail(code="invalid_event", message=str(e)),
                meta=ApiMeta(request_id=_request_id(request)),
            ).model_dump(),
        )

    return DataResponse(
        meta=ApiMeta(request_id=_request_id(request)),
        data=EventResponse(
            event_id=event.event_id,
            event_type=event.event_type,
            client_event_id=event.client_event_id,
            request_id=event.request_id,
            session_id=event.session_id,
            user_id=event.user_id,
            query_id=event.query_id,
            query_text=event.query_text,
            item_id=event.item_id,
            position=event.position,
            timestamp=event.timestamp.isoformat(),
            click_duration_ms=event.click_duration_ms,
            add_to_cart_quantity=event.add_to_cart_quantity,
            purchase_amount=event.purchase_amount,
        ),
    )


@router.get("/stats", response_model=DataResponse[EventStatsResponse])
def get_event_stats(
    request: Request,
    session: Session = Depends(get_db_session),
    user_id: str | None = Query(default=None),
    query_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    start_at: str | None = Query(default=None, description="ISO-8601 start (inclusive)"),
    end_at: str | None = Query(default=None, description="ISO-8601 end (inclusive)"),
):
    # Parse time params
    start_dt: datetime | None = None
    end_dt: datetime | None = None
    try:
        if start_at:
            start_dt = datetime.fromisoformat(start_at)
        if end_at:
            end_dt = datetime.fromisoformat(end_at)
    except ValueError as e:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=ErrorDetail(code="invalid_time_format", message=f"Invalid ISO-8601: {e}"),
                meta=ApiMeta(request_id=_request_id(request)),
            ).model_dump(),
        )

    if start_dt and end_dt and start_dt > end_dt:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=ErrorDetail(code="invalid_time_range", message="start_at must be <= end_at"),
                meta=ApiMeta(request_id=_request_id(request)),
            ).model_dump(),
        )

    svc = EventService(session)
    stats = svc.get_stats(
        user_id=user_id, query_id=query_id, event_type=event_type,
        start_at=start_dt, end_at=end_dt,
    )
    return DataResponse(
        meta=ApiMeta(request_id=_request_id(request)),
        data=EventStatsResponse(**stats),
    )


@router.get("/recent", response_model=ListResponse[EventResponse])
def get_recent_events(
    request: Request,
    session: Session = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
):
    svc = EventService(session)
    events = svc.list_recent(limit=limit, user_id=user_id, event_type=event_type)
    data = [
        EventResponse(
            event_id=e.event_id,
            event_type=e.event_type,
            client_event_id=e.client_event_id,
            request_id=e.request_id,
            session_id=e.session_id,
            user_id=e.user_id,
            query_id=e.query_id,
            query_text=e.query_text,
            item_id=e.item_id,
            position=e.position,
            timestamp=e.timestamp.isoformat(),
            click_duration_ms=e.click_duration_ms,
            add_to_cart_quantity=e.add_to_cart_quantity,
            purchase_amount=e.purchase_amount,
        )
        for e in events
    ]
    return ListResponse(
        data=data,
        pagination=PaginationMeta(offset=0, limit=limit, total=len(data), returned=len(data)),
        meta=ApiMeta(request_id=_request_id(request)),
    )
