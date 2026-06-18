"""EventService — user behavior event recording and statistics."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.event import Event
from app.repositories.event_repository import EventRepository

logger = logging.getLogger(__name__)

_VALID_EVENT_TYPES = {"impression", "click", "favorite", "add_to_cart", "purchase"}


class EventService:
    def __init__(self, session: Session):
        self._session = session
        self._repo = EventRepository(session)

    def create_event(
        self,
        *,
        event_id: str,
        event_type: str,
        request_id: str,
        session_id: str = "",
        user_id: str = "",
        query_id: str | None = None,
        query_text: str | None = None,
        item_id: str = "",
        position: int | None = None,
        occurred_at: datetime | None = None,
        click_duration_ms: int | None = None,
        add_to_cart_quantity: int | None = None,
        purchase_amount: float | None = None,
        client_event_id: str | None = None,
    ) -> Event:
        if event_type not in _VALID_EVENT_TYPES:
            raise ValueError(f"Invalid event_type: {event_type!r}")

        # Idempotency: if client_event_id provided and already exists, return existing
        if client_event_id:
            existing = self._session.query(Event).filter(
                Event.client_event_id == client_event_id
            ).first()
            if existing:
                logger.debug("Idempotent return for client_event_id=%s", client_event_id)
                return existing

        ts = occurred_at or datetime.now(UTC)

        event = Event(
            event_id=event_id,
            client_event_id=client_event_id,
            event_type=event_type,
            request_id=request_id or "",
            session_id=session_id or "",
            user_id=user_id or "",
            query_id=query_id or None,
            query_text=query_text or None,
            item_id=item_id or "",
            position=position,
            timestamp=ts,
            click_duration_ms=click_duration_ms,
            add_to_cart_quantity=add_to_cart_quantity,
            purchase_amount=purchase_amount,
        )
        try:
            self._session.add(event)
            self._session.flush()
        except IntegrityError:
            self._session.rollback()
            if client_event_id:
                existing = self._session.query(Event).filter(
                    Event.client_event_id == client_event_id
                ).first()
                if existing:
                    return existing
            raise

        return event

    def get_stats(
        self,
        *,
        user_id: str | None = None,
        query_id: str | None = None,
        event_type: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> dict:
        # Apply all filters at the database level
        total = self._repo.count(
            user_id=user_id, query_id=query_id, event_type=event_type,
            start_at=start_at, end_at=end_at,
        )
        counts = self._repo.count_by_type(
            user_id=user_id, query_id=query_id, event_type=event_type,
            start_at=start_at, end_at=end_at,
        )

        impression = counts.get("impression", 0)
        click = counts.get("click", 0)

        def rate(numerator: int, denominator: int) -> float:
            return round(numerator / denominator, 6) if denominator > 0 else 0.0

        return {
            "total_events": total,
            "event_counts": {
                "impression": impression,
                "click": click,
                "favorite": counts.get("favorite", 0),
                "add_to_cart": counts.get("add_to_cart", 0),
                "purchase": counts.get("purchase", 0),
            },
            "rates": {
                "click_through_rate": rate(click, impression),
                "favorite_rate": rate(counts.get("favorite", 0), click),
                "add_to_cart_rate": rate(counts.get("add_to_cart", 0), click),
                "purchase_rate": rate(counts.get("purchase", 0), click),
            },
        }

    def list_recent(
        self,
        *,
        limit: int = 20,
        user_id: str | None = None,
        event_type: str | None = None,
    ) -> list[Event]:
        return self._repo.list_recent(limit=limit, user_id=user_id, event_type=event_type)
