"""ServiceContainer + Lifecycle tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.item import Item
from app.services.container import ServiceContainer


@pytest.fixture
def _items(db_session):
    for j in range(5):
        db_session.add(Item(
            item_id=f"i{j}", title=f"Item {j}", description="", category="C",
            subcategory="S", brand="B", price=Decimal("10"),
            quality_score=0.5, popularity_score=0.5,
        ))
    db_session.commit()


class TestServiceContainer:
    def test_create_all_services(self, db_session_factory):
        c = ServiceContainer(db_session_factory)
        assert c.index_manager is not None
        assert c.profile_service is not None
        assert c.personalization_service is not None
        assert c.search_service is not None
        assert c.evaluation_service is not None

    def test_initialize(self, db_session_factory, _items):
        c = ServiceContainer(db_session_factory)
        c.initialize()
        assert c.index_manager.is_ready()

    def test_double_initialize_safe(self, db_session_factory, _items):
        c = ServiceContainer(db_session_factory)
        c.initialize()
        c.initialize()  # should not raise

    def test_shutdown_idempotent(self, db_session_factory):
        c = ServiceContainer(db_session_factory)
        c.shutdown()
        c.shutdown()  # should not raise

    def test_search_uses_same_index_manager(self, db_session_factory):
        c = ServiceContainer(db_session_factory)
        assert c.search_service._index_manager is c.index_manager
