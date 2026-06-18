"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.error_handlers import (
    http_404_handler,
    internal_error_handler,
    service_error_handler,
    validation_error_handler,
)
from app.api.middleware import RequestIDMiddleware
from app.api.router import router as v1_router
from app.core.config import settings
from app.services.errors import ServiceError
from app.services.lifecycle import app_lifespan


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Personalized Search Ranking & Semantic Retrieval — Enterprise API",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        lifespan=app_lifespan,
    )

    # Middleware (outermost first)
    app.add_middleware(RequestIDMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # Exception handlers
    app.add_exception_handler(ServiceError, service_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_404_handler)
    app.add_exception_handler(Exception, internal_error_handler)

    # Routes
    app.include_router(v1_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
