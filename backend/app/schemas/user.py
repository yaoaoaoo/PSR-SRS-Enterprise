"""User API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    preferred_categories: list[str] = Field(default_factory=list)
    preferred_brands: list[str] = Field(default_factory=list)
    price_preference: str | None = None
    activity_level: str | None = None
    is_cold_start: bool = False
    created_at: datetime | None = None


class UserFilterParams(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    is_cold_start: bool | None = None
    activity_level: str | None = None


class ProfileResponse(BaseModel):
    user_id: str
    status: str
    generation: int
    built_at: datetime | None = None
    is_cold_start: bool = False
    category_weights: dict[str, float] = Field(default_factory=dict)
    brand_weights: dict[str, float] = Field(default_factory=dict)
    mean_log_price: float | None = None
    fallback_reason: str | None = None
