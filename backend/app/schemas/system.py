"""System/status API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SystemStatusResponse(BaseModel):
    service: str
    version: str
    environment: str
    database_connected: bool
    schema_available: bool
    index_ready: bool
    index_generation: int
    profile_ready: bool
    profile_generation: int
    uptime_seconds: float | None = None


class IndexStatusResponse(BaseModel):
    ready: bool
    generation: int
    built_at: datetime | None = None
    item_count: int
    error_message: str | None = None


class ProfileStatusResponse(BaseModel):
    ready: bool
    generation: int
    built_at: datetime | None = None
    profile_count: int
    error_message: str | None = None
