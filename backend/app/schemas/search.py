"""Search API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.services.types import SearchMode


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        ..., min_length=1, max_length=500,
        description="Search query text",
    )
    mode: SearchMode = Field(
        default=SearchMode.LINEAR,
        description="Retrieval mode: bm25, semantic, rrf, linear",
    )
    top_k: int = Field(
        default=10, ge=1, le=100,
        description="Number of results to return",
    )
    user_id: str | None = Field(
        default=None, max_length=64,
        description="User ID for personalization",
    )
    personalize: bool = Field(
        default=False,
        description="Enable personalized re-ranking",
    )


class SearchHitSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: str
    rank: int
    score: float
    source: str
    original_rank: int | None = None
    bm25_score: float | None = None
    semantic_score: float | None = None
    fusion_score: float | None = None
    personalization_score: float | None = None
    title: str | None = None
    category: str | None = None
    subcategory: str | None = None
    brand: str | None = None
    price: str | None = None
    quality_score: float | None = None
    popularity_score: float | None = None
    is_cold_start: bool | None = None


class SearchResponse(BaseModel):
    query: str
    mode: str
    personalization_requested: bool = False
    personalization_applied: bool = False
    user_id: str | None = None
    fallback_reason: str | None = None
    total_candidates: int
    returned_count: int
    index_generation: int
    took_ms: float
    hits: list[SearchHitSchema]
