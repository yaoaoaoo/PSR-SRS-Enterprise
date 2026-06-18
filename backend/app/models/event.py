"""Event ORM model — corresponds to MVP events.csv."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_VALID_EVENT_TYPES = {"impression", "click", "favorite", "add_to_cart", "purchase"}


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_event_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True,
        comment="Client-generated idempotency key",
    )
    event_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True,
    )
    request_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    query_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("queries.query_id", ondelete="RESTRICT"),
        nullable=True, index=True,
        comment="Nullable — impressions may not reference a query",
    )
    query_text: Mapped[str | None] = mapped_column(
        String(512), nullable=True,
    )
    item_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("items.item_id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
    )
    click_duration_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    add_to_cart_quantity: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    purchase_amount: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            f"event_type IN ({', '.join(repr(t) for t in sorted(_VALID_EVENT_TYPES))})",
            name="ck_event_type_valid",
        ),
        CheckConstraint(
            "position IS NULL OR position > 0",
            name="ck_event_position_positive",
        ),
        CheckConstraint(
            "click_duration_ms IS NULL OR click_duration_ms >= 0",
            name="ck_event_click_duration_non_negative",
        ),
        CheckConstraint(
            "add_to_cart_quantity IS NULL OR add_to_cart_quantity >= 0",
            name="ck_event_cart_quantity_non_negative",
        ),
        CheckConstraint(
            "purchase_amount IS NULL OR purchase_amount >= 0",
            name="ck_event_purchase_amount_non_negative",
        ),
        Index("ix_events_user_timestamp", "user_id", "timestamp"),
        Index("ix_events_query_timestamp", "query_id", "timestamp"),
        Index("ix_events_request_position", "request_id", "position"),
    )

    def __repr__(self) -> str:
        return (
            f"<Event {self.event_id!r} type={self.event_type!r} "
            f"user={self.user_id!r} item={self.item_id!r}>"
        )
