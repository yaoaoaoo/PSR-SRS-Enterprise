"""ServiceContainer — explicit, testable service wiring."""

from __future__ import annotations

import logging

from sqlalchemy.orm import sessionmaker

from app.core.service_config import ServiceSettings, service_settings
from app.services.evaluation_service import EvaluationService
from app.services.index_manager import IndexManager
from app.services.personalization_service import PersonalizationService
from app.services.profile_service import ProfileService
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Holds all service instances with explicit dependencies."""

    def __init__(
        self,
        session_factory: sessionmaker,
        settings: ServiceSettings | None = None,
    ):
        self._settings = settings or service_settings
        self._session_factory = session_factory

        # Create services in dependency order
        self.index_manager = IndexManager(session_factory)
        self.profile_service = ProfileService(session_factory)
        self.personalization_service = PersonalizationService(self.profile_service)
        self.search_service = SearchService(
            self.index_manager, self.personalization_service,
        )
        self.evaluation_service = EvaluationService(
            self.index_manager, session_factory,
        )
        self._initialized = False

    def initialize(self) -> None:
        """Build indices and profiles (idempotent)."""
        if self._initialized:
            logger.info("ServiceContainer already initialized — skipping")
            return

        if self._settings.INDEX_BUILD_ON_STARTUP:
            try:
                self.index_manager.build()
            except Exception:
                logger.exception("Index build failed during initialization")

        if self._settings.PROFILE_BUILD_ON_STARTUP:
            try:
                self.profile_service.build()
            except Exception:
                logger.exception("Profile build failed during initialization")

        self._initialized = True
        logger.info("ServiceContainer initialized")

    def shutdown(self) -> None:
        """Release resources (idempotent)."""
        self._initialized = False
        logger.info("ServiceContainer shutdown complete")
