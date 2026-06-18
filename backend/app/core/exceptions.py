"""Unified exception hierarchy and global FastAPI exception handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application exception hierarchy
# ---------------------------------------------------------------------------

class AppError(Exception):
    """Base application error with a user-facing message and optional detail."""

    def __init__(self, message: str, detail: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


class NotFoundError(AppError):
    """Requested resource does not exist."""


class ValidationError(AppError):
    """Input validation failure."""


class ServiceError(AppError):
    """Internal service error — retryable or transient."""


class ConfigurationError(AppError):
    """Application misconfiguration."""


# ---------------------------------------------------------------------------
# FastAPI exception handlers
# ---------------------------------------------------------------------------

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("AppError | %s | %s", exc.message, exc.detail)
    return JSONResponse(
        status_code=_status_for(exc),
        content={
            "error": type(exc).__name__,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from starlette.exceptions import HTTPException as StarletteHTTPException

    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "not_found" if exc.status_code == 404 else "http_error",
                "message": str(exc.detail) if exc.detail else "Resource not found",
            },
        )
    raise exc


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception | %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


def _status_for(exc: AppError) -> int:
    mapping = {
        NotFoundError: 404,
        ValidationError: 422,
        ConfigurationError: 500,
    }
    return mapping.get(type(exc), 500)
