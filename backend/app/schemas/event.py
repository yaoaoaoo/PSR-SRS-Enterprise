"""Event API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(..., pattern="^(impression|click|favorite|add_to_cart|purchase)$")
    event_id: str = Field(..., min_length=1, max_length=64)
    client_event_id: str | None = Field(default=None, max_length=64)
    request_id: str = Field(default="", max_length=64)
    session_id: str = Field(default="", max_length=64)
    user_id: str = Field(default="", max_length=64)
    query_id: str | None = Field(default=None, max_length=64)
    query_text: str | None = Field(default=None, max_length=512)
    item_id: str = Field(default="", max_length=64)
    position: int | None = Field(default=None, ge=1)
    occurred_at: datetime | None = None
    click_duration_ms: int | None = Field(default=None, ge=0)
    add_to_cart_quantity: int | None = Field(default=None, ge=0)
    purchase_amount: float | None = Field(default=None, ge=0.0)


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    event_type: str
    client_event_id: str | None = None
    request_id: str
    session_id: str
    user_id: str
    query_id: str | None = None
    query_text: str | None = None
    item_id: str
    position: int | None = None
    timestamp: str
    click_duration_ms: int | None = None
    add_to_cart_quantity: int | None = None
    purchase_amount: float | None = None


class EventStatsResponse(BaseModel):
    total_events: int
    event_counts: dict[str, int]
    rates: dict[str, float]
