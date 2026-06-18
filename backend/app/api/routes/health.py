"""Health-check endpoints with enhanced readiness."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.init_db import verify_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


def _get_index_status(request: Request) -> dict:
    try:
        container = request.app.state.service_container
        return container.index_manager.get_status().__dict__
    except Exception:
        return {"ready": False, "error": "container not initialized"}


def _get_profile_status(request: Request) -> dict:
    try:
        container = request.app.state.service_container
        return container.profile_service.get_status().__dict__
    except Exception:
        return {"ready": False, "error": "container not initialized"}


@router.get("/health")
async def health_check():
    """Liveness probe — returns basic service metadata."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(request: Request):
    """Readiness probe — verifies critical dependencies."""
    db_info = verify_db()
    db_ok = db_info.get("database_connected", False)

    # Check schema
    schema_ok = False
    if db_ok:
        from app.db.session import _get_session_factory
        try:
            s = _get_session_factory()()
            s.execute(s.bind.dialect.dialect_description("SELECT 1 FROM items LIMIT 0"))
            schema_ok = True
            s.close()
        except Exception:
            pass

    idx_status = _get_index_status(request)
    prof_status = _get_profile_status(request)

    index_ready = idx_status.get("ready", False)
    profiles_ready = prof_status.get("ready", False)

    # Determine overall status
    if db_ok and schema_ok and index_ready:
        overall = "ready"
        http_status = 200
    elif db_ok and schema_ok:
        overall = "degraded"
        http_status = 200
    else:
        overall = "not_ready"
        http_status = 503

    payload = {
        "status": overall,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "checks": {
            "config_loaded": True,
            "database": db_info,
            "schema": "ok" if schema_ok else "missing",
            "index": "ready" if index_ready else ("empty" if schema_ok else "not_ready"),
            "profiles": "ready" if profiles_ready else ("empty" if schema_ok else "not_ready"),
        },
        "details": {
            "index_generation": idx_status.get("generation", 0),
            "indexed_items": idx_status.get("item_count", 0),
            "profile_generation": prof_status.get("generation", 0),
            "profiles": prof_status.get("profile_count", 0),
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }

    return JSONResponse(status_code=http_status, content=payload)
