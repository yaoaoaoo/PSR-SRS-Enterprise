"""Tests for database session management."""

from __future__ import annotations

from decimal import Decimal

from app.models.item import Item


class TestSession:
    def test_session_commits(self, db_session):
        item = Item(
            item_id="ss_c", title="X", description="", category="C",
            subcategory="S", brand="B", price=Decimal("10"),
            quality_score=0.5, popularity_score=0.5,
        )
        db_session.add(item)
        db_session.commit()
        assert db_session.get(Item, "ss_c") is not None

    def test_session_rolls_back(self, db_session):
        item = Item(
            item_id="ss_rb", title="X", description="", category="C",
            subcategory="S", brand="B", price=Decimal("10"),
            quality_score=0.5, popularity_score=0.5,
        )
        db_session.add(item)
        db_session.rollback()
        assert db_session.get(Item, "ss_rb") is None

    def test_check_db_connection(self, db_session_factory):
        from app.db.session import check_db_connection

        # Engine should use test DB since we set DATABASE_URL
        assert check_db_connection() is True
