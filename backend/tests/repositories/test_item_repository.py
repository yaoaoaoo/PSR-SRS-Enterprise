"""Tests for ItemRepository."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.item import Item
from app.repositories.item_repository import ItemRepository


@pytest.fixture
def _items(db_session):
    items = [
        Item(
            item_id=f"i{i}",
            title=f"Item {i}",
            description="",
            category="Electronics" if i % 2 == 0 else "Books",
            subcategory="S",
            brand="B",
            price=Decimal("10"),
            quality_score=0.5,
            popularity_score=0.5,
        )
        for i in range(5)
    ]
    db_session.add_all(items)
    db_session.commit()


class TestItemRepository:
    def test_get_by_id(self, db_session, _items):
        repo = ItemRepository(db_session)
        item = repo.get_by_id("i0")
        assert item is not None
        assert item.item_id == "i0"

    def test_get_missing(self, db_session, _items):
        repo = ItemRepository(db_session)
        assert repo.get_by_id("nonexistent") is None

    def test_count(self, db_session, _items):
        repo = ItemRepository(db_session)
        assert repo.count() == 5

    def test_list_pagination(self, db_session, _items):
        repo = ItemRepository(db_session)
        items = repo.list(limit=3)
        assert len(items) == 3

    def test_category_filter(self, db_session, _items):
        repo = ItemRepository(db_session)
        items = repo.list(category="Electronics")
        assert len(items) == 3  # i0, i2, i4

    def test_get_many_by_ids(self, db_session, _items):
        repo = ItemRepository(db_session)
        items = repo.get_many_by_ids(["i0", "i2", "i99"])
        assert len(items) == 2

    def test_list_for_indexing(self, db_session, _items):
        repo = ItemRepository(db_session)
        pairs = repo.list_for_indexing()
        assert len(pairs) == 5
        for iid, text in pairs:
            assert isinstance(iid, str)
            assert isinstance(text, str)
            assert len(text) > 0

    def test_build_items_map(self, db_session, _items):
        repo = ItemRepository(db_session)
        items_map = repo.build_items_map()
        assert len(items_map) == 5
        assert "category" in items_map["i0"]
        assert "price" in items_map["i0"]
