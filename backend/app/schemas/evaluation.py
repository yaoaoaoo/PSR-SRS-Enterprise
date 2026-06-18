"""Evaluation API schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvalQueryItem(BaseModel):
    query_id: str = Field(..., max_length=64)
    query_text: str = Field(default="", max_length=512)


class EvaluationQueriesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queries: list[EvalQueryItem] = Field(..., min_length=1, max_length=100)
    ks: list[int] = Field(default_factory=lambda: [5, 10, 20], min_length=1, max_length=10)

    @field_validator("ks")
    @classmethod
    def validate_ks(cls, v: list[int]) -> list[int]:
        for k in v:
            if k < 1 or k > 100:
                raise ValueError(f"k must be 1-100, got {k}")
        return v


class CoverageRequestItem(BaseModel):
    request_id: str = Field(..., max_length=64)
    query_id: str = Field(default="", max_length=64)
    candidate_item_ids: list[str] = Field(default_factory=list, max_length=200)


class CandidateCoverageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requests: list[CoverageRequestItem] = Field(..., min_length=0, max_length=500)


class CandidateCoverageResponse(BaseModel):
    eligible_requests: int
    covered_requests: int
    uncovered_requests: int
    request_level_coverage: float
    total_positive_items: int = 0
    covered_positive_items: int = 0
    item_level_recall: float = 0.0
    took_ms: float = 0.0


class EvaluationResponse(BaseModel):
    query_count: int
    metrics: dict
    candidate_coverage: dict | None = None
    took_ms: float
    ks: list[int]
