"""Verify SQLite foreign key enforcement."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.event import Event
from app.models.item import Item


class TestForeignKeys:
    def test_foreign_key_enforced(self, db_session):
        """Inserting an event referencing a non-existent item must fail."""
        # Don't insert any item — event references a missing item_id
        from datetime import UTC, datetime

        e = Event(
            event_id="e_fk", event_type="click",
            request_id="r1", session_id="s1",
            user_id="u_fk", item_id="i_fk",
            timestamp=datetime.now(UTC),
        )
        db_session.add(e)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_delete_referenced_item_restricted(self, db_session):
        """Deleting an item referenced by an event should be restricted."""
        from datetime import UTC, datetime

        item = Item(
            item_id="i_del", title="T", description="", category="C",
            subcategory="S", brand="B", price=Decimal("10"),
            quality_score=0.5, popularity_score=0.5,
        )
        db_session.add(item)
        db_session.flush()

        from app.models.user import User
        u = User(user_id="u_del")
        db_session.add(u)
        db_session.flush()

        e = Event(
            event_id="e_del", event_type="click",
            request_id="r1", session_id="s1",
            user_id="u_del", item_id="i_del",
            timestamp=datetime.now(UTC),
        )
        db_session.add(e)
        db_session.commit()

        # Now try to delete the item — should fail (RESTRICT)
        db_session.delete(item)
        with pytest.raises(IntegrityError):
            db_session.commit()
