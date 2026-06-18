"""Tests for Item ORM model — constraints, defaults, indexing."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.item import Item


class TestItemModel:
    def test_create_valid_item(self, db_session):
        item = Item(
            item_id="item_001", title="Laptop", description="A laptop",
            category="Electronics", subcategory="Laptops", brand="TechPro",
            price=Decimal("999.99"), quality_score=0.8, popularity_score=0.5,
        )
        db_session.add(item)
        db_session.commit()
        assert db_session.get(Item, "item_001") is not None

    def test_price_negative_rejected(self, db_session):
        item = Item(
            item_id="x", title="X", description="", category="C", subcategory="S",
            brand="B", price=Decimal("-1"), quality_score=0.5, popularity_score=0.5,
        )
        db_session.add(item)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_quality_score_out_of_range(self, db_session):
        item = Item(
            item_id="x", title="X", description="", category="C", subcategory="S",
            brand="B", price=Decimal("10"), quality_score=1.5, popularity_score=0.5,
        )
        db_session.add(item)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_default_values(self, db_session):
        item = Item(
            item_id="x", title="X", description="", category="C", subcategory="S",
            brand="B", price=Decimal("10"), quality_score=0.5, popularity_score=0.5,
        )
        db_session.add(item)
        db_session.commit()
        loaded = db_session.get(Item, "x")
        assert loaded.is_cold_start is False

    def test_created_at_auto_set(self, db_session):
        item = Item(
            item_id="x", title="X", description="", category="C", subcategory="S",
            brand="B", price=Decimal("10"), quality_score=0.5, popularity_score=0.5,
        )
        db_session.add(item)
        db_session.commit()
        assert db_session.get(Item, "x").created_at is not None
