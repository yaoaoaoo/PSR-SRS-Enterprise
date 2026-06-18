"""Item API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: str
    title: str
    description: str = ""
    category: str
    subcategory: str
    brand: str
    price: str  # Decimal serialized as string
    quality_score: float
    popularity_score: float
    is_cold_start: bool
    created_at: datetime | None = None


class ItemFilterParams(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    category: str | None = None
    subcategory: str | None = None
    brand: str | None = None
    is_cold_start: bool | None = None
