"""Tests for Qrel ORM model."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.item import Item
from app.models.qrel import Qrel
from app.models.query import Query


@pytest.fixture
def _setup_qrel_refs(db_session):
    i = Item(
        item_id="i1", title="T", description="", category="C",
        subcategory="S", brand="B", price=10, quality_score=0.5, popularity_score=0.5,
    )
    q = Query(query_id="q1", query_text="test")
    db_session.add_all([i, q])
    db_session.commit()


class TestQrelModel:
    def test_create(self, db_session, _setup_qrel_refs):
        qrel = Qrel(query_id="q1", item_id="i1", relevance_grade=3)
        db_session.add(qrel)
        db_session.commit()
        assert db_session.get(Qrel, ("q1", "i1")) is not None

    def test_duplicate_rejected(self, db_session, _setup_qrel_refs):
        q1 = Qrel(query_id="q1", item_id="i1", relevance_grade=3)
        q2 = Qrel(query_id="q1", item_id="i1", relevance_grade=2)
        db_session.add_all([q1, q2])
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_grade_out_of_range(self, db_session, _setup_qrel_refs):
        qrel = Qrel(query_id="q1", item_id="i1", relevance_grade=5)
        db_session.add(qrel)
        with pytest.raises(IntegrityError):
            db_session.commit()
