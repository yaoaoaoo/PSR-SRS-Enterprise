"""FastAPI lifespan — create and initialise the service container."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.service_config import service_settings
from app.db.session import _get_session_factory, check_db_connection
from app.services.container import ServiceContainer

logger = logging.getLogger(__name__)


def _check_schema() -> bool:
    """Verify that database tables exist (schema migrated)."""
    try:
        factory = _get_session_factory()
        session = factory()
        try:
            session.execute(
                session.bind.dialect.dialect_description("SELECT 1 FROM items LIMIT 0")
            )
            return True
        except Exception:
            return False
        finally:
            session.close()
    except Exception:
        return False


def create_container() -> ServiceContainer:
    """Build and return a ServiceContainer."""
    factory = _get_session_factory()
    return ServiceContainer(factory, service_settings)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """FastAPI lifespan — creates services, runs startup builds, cleans up."""
    # Startup
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    if not check_db_connection():
        logger.critical("Database connection failed — service may be degraded")

    schema_ok = _check_schema()
    if not schema_ok:
        logger.warning(
            "Schema not found — run: alembic upgrade head"
        )

    container = create_container()
    try:
        container.initialize()
    except Exception:
        logger.exception("Service initialization failed — starting in degraded mode")

    app.state.service_container = container
    logger.info("Lifespan startup complete")

    yield  # Application runs here

    # Shutdown
    try:
        container.shutdown()
    except Exception:
        logger.exception("Error during shutdown")
    logger.info("Lifespan shutdown complete")
