"""Common API schema types — responses, pagination, meta."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiMeta(BaseModel):
    request_id: str = Field(default="", description="Unique request identifier")
    api_version: str = Field(default="v1", description="API version")


class DataResponse(BaseModel, Generic[T]):
    data: T
    meta: ApiMeta = Field(default_factory=ApiMeta)


class PaginationMeta(BaseModel):
    offset: int
    limit: int
    total: int
    returned: int


class ListResponse(BaseModel, Generic[T]):
    data: list[T]
    pagination: PaginationMeta
    meta: ApiMeta = Field(default_factory=ApiMeta)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    meta: ApiMeta = Field(default_factory=ApiMeta)


class ValidationIssue(BaseModel):
    field: str | None = None
    message: str
    type: str = "validation_error"
