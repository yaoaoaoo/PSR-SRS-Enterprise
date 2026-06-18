"""EventRepository — queries for the events table."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.event import Event


def _apply_filters(
    stmt,
    *,
    user_id: str | None = None,
    query_id: str | None = None,
    event_type: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
):
    if user_id:
        stmt = stmt.where(Event.user_id == user_id)
    if query_id:
        stmt = stmt.where(Event.query_id == query_id)
    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    if start_at:
        stmt = stmt.where(Event.timestamp >= start_at)
    if end_at:
        stmt = stmt.where(Event.timestamp <= end_at)
    return stmt


class EventRepository:
    """Data access for events."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, event_id: str) -> Event | None:
        return self._session.get(Event, event_id)

    def count(
        self,
        *,
        user_id: str | None = None,
        query_id: str | None = None,
        event_type: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Event)
        stmt = _apply_filters(stmt, user_id=user_id, query_id=query_id,
                              event_type=event_type, start_at=start_at, end_at=end_at)
        return self._session.execute(stmt).scalar_one()

    def count_by_type(
        self,
        *,
        user_id: str | None = None,
        query_id: str | None = None,
        event_type: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> dict[str, int]:
        stmt = (
            select(Event.event_type, func.count())
            .group_by(Event.event_type)
        )
        stmt = _apply_filters(stmt, user_id=user_id, query_id=query_id,
                              event_type=event_type, start_at=start_at, end_at=end_at)
        rows = self._session.execute(stmt).all()
        return {row[0]: row[1] for row in rows}

    def list_for_user(
        self,
        user_id: str,
        *,
        limit: int = 1000,
        event_type: str | None = None,
        after: datetime | None = None,
        before: datetime | None = None,
    ) -> list[Event]:
        stmt = (
            select(Event)
            .where(Event.user_id == user_id)
            .order_by(Event.timestamp, Event.event_id)
        )
        if event_type:
            stmt = stmt.where(Event.event_type == event_type)
        if after:
            stmt = stmt.where(Event.timestamp >= after)
        if before:
            stmt = stmt.where(Event.timestamp < before)
        return list(
            self._session.execute(stmt.limit(limit)).scalars().all()
        )

    def list_for_query(
        self,
        query_id: str,
        *,
        limit: int = 1000,
    ) -> list[Event]:
        stmt = (
            select(Event)
            .where(Event.query_id == query_id)
            .order_by(Event.timestamp, Event.event_id)
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())

    def list_for_request(
        self,
        request_id: str,
        *,
        limit: int = 100,
    ) -> list[Event]:
        stmt = (
            select(Event)
            .where(Event.request_id == request_id)
            .order_by(Event.position)
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())

    def list_training_events(
        self,
        *,
        event_types: list[str] | None = None,
        after: datetime | None = None,
        before: datetime | None = None,
        limit: int = 20000,
    ) -> list[dict]:
        """Return events suitable for profile building (as dicts)."""
        stmt = select(Event).order_by(Event.timestamp, Event.event_id)
        if event_types:
            stmt = stmt.where(Event.event_type.in_(event_types))
        if after:
            stmt = stmt.where(Event.timestamp >= after)
        if before:
            stmt = stmt.where(Event.timestamp < before)

        events = self._session.execute(stmt.limit(limit)).scalars().all()
        return [
            {
                "user_id": e.user_id,
                "event_type": e.event_type,
                "item_id": e.item_id,
                "timestamp": e.timestamp.isoformat(),
                "session_id": e.session_id,
            }
            for e in events
        ]

    def list_recent(
        self,
        *,
        limit: int = 20,
        user_id: str | None = None,
        query_id: str | None = None,
        event_type: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[Event]:
        stmt = select(Event).order_by(Event.timestamp.desc())
        stmt = _apply_filters(stmt, user_id=user_id, query_id=query_id,
                              event_type=event_type, start_at=start_at, end_at=end_at)
        return list(self._session.execute(stmt.limit(min(limit, 100))).scalars().all())
