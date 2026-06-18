"""FastAPI dependency injection — service and session accessors."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.session import _get_session_factory
from app.services.container import ServiceContainer
from app.services.errors import ServiceInitializationError
from app.services.evaluation_service import EvaluationService
from app.services.index_manager import IndexManager
from app.services.personalization_service import PersonalizationService
from app.services.profile_service import ProfileService
from app.services.search_service import SearchService


def _get_container(request: Request) -> ServiceContainer:
    container = getattr(request.app.state, "service_container", None)
    if container is None:
        raise ServiceInitializationError("Service container not initialized")
    return container


def get_search_service(request: Request) -> SearchService:
    return _get_container(request).search_service


def get_index_manager(request: Request) -> IndexManager:
    return _get_container(request).index_manager


def get_profile_service(request: Request) -> ProfileService:
    return _get_container(request).profile_service


def get_personalization_service(request: Request) -> PersonalizationService:
    return _get_container(request).personalization_service


def get_evaluation_service(request: Request) -> EvaluationService:
    return _get_container(request).evaluation_service


def get_db_session() -> Generator[Session, None, None]:
    """Yield a short-lived database session for read queries."""
    factory = _get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
