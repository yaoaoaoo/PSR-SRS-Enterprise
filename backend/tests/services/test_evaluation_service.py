"""EvaluationService tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.item import Item
from app.models.qrel import Qrel
from app.models.query import Query
from app.services.container import ServiceContainer


@pytest.fixture
def _eval_data(db_session):
    items = [
        Item(item_id=f"i{j}", title=f"Item {j}", description="", category="C",
             subcategory="S", brand="B", price=Decimal("10"),
             quality_score=0.5, popularity_score=0.5)
        for j in range(5)
    ]
    queries = [Query(query_id=f"q{j}", query_text=f"query {j}") for j in range(3)]
    db_session.add_all(items + queries)
    db_session.flush()
    qrels = [
        Qrel(query_id="q0", item_id="i0", relevance_grade=3),
        Qrel(query_id="q0", item_id="i1", relevance_grade=1),
        Qrel(query_id="q1", item_id="i2", relevance_grade=2),
    ]
    db_session.add_all(qrels)
    db_session.commit()


@pytest.fixture
def container(db_session_factory, _eval_data):
    c = ServiceContainer(db_session_factory)
    c.initialize()
    return c


class TestEvaluationService:
    def test_evaluate_single_query(self, container):
        report = container.evaluation_service.evaluate_queries(["q0"])
        assert report.query_count == 1
        assert report.duration_seconds >= 0
        assert "macro_average" in report.metrics

    def test_evaluate_multiple_queries(self, container):
        report = container.evaluation_service.evaluate_queries(["q0", "q1"])
        assert report.query_count == 2

    def test_evaluate_empty_list(self, container):
        report = container.evaluation_service.evaluate_queries([])
        assert report.query_count == 0

    def test_result_json_compatible(self, container):
        import json
        report = container.evaluation_service.evaluate_queries(["q0"])
        data = json.dumps(report.metrics)
        assert data is not None
