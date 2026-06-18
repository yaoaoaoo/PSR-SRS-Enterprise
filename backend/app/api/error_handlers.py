"""Unified error mapping — ServiceError → HTTP response."""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ApiMeta, ErrorDetail, ErrorResponse
from app.services.errors import (
    IndexNotReadyError,
    InvalidSearchRequestError,
    ProfileNotReadyError,
    ServiceError,
    ServiceInitializationError,
    UnsupportedSearchModeError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)

_ERROR_STATUS: dict[type[ServiceError], int] = {
    InvalidSearchRequestError: 400,
    UnsupportedSearchModeError: 400,
    UserNotFoundError: 404,
    IndexNotReadyError: 503,
    ProfileNotReadyError: 503,
    ServiceInitializationError: 503,
}


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    status = _ERROR_STATUS.get(type(exc), 500)
    rid = _get_request_id(request)
    logger.warning("ServiceError status=%d code=%s", status, exc.code, exc_info=False)
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(
            error=ErrorDetail(code=exc.code, message=exc.message, details=exc.detail),
            meta=ApiMeta(request_id=rid),
        ).model_dump(),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    rid = _get_request_id(request)
    details = exc.errors()
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error=ErrorDetail(
                code="request_validation_error",
                message="Request validation failed",
                details=details,
            ),
            meta=ApiMeta(request_id=rid),
        ).model_dump(),
    )


async def http_404_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    rid = _get_request_id(request)
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error=ErrorDetail(code="not_found", message="Resource not found"),
            meta=ApiMeta(request_id=rid),
        ).model_dump(),
    )


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    rid = _get_request_id(request)
    logger.exception("Internal server error | request_id=%s", rid)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(
                code="internal_error",
                message="An unexpected error occurred",
            ),
            meta=ApiMeta(request_id=rid),
        ).model_dump(),
    )
