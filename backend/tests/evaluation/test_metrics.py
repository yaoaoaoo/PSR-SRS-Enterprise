"""Tests for offline evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.evaluation.metrics import (
    MetricResult,
    evaluate_all,
    evaluate_query,
    macro_average,
)


@dataclass(frozen=True)
class _FakeResult:
    """Fake ranked result satisfying RankedItemProtocol."""
    item_id: str
    score: float


class TestEvaluateQuery:
    def test_perfect_results(self):
        results = [_FakeResult(f"item_{i}", 10.0 - i) for i in range(5)]
        qrels = {"q1": {f"item_{i}": 3 for i in range(5)}}
        m = evaluate_query(results, "q1", "test query", qrels, ks=[5])
        assert m.precision[5] == 1.0
        assert m.recall[5] == 1.0
        assert m.mrr[5] == 1.0

    def test_no_relevant(self):
        results = [_FakeResult(f"item_{i}", 10.0) for i in range(3)]
        qrels = {"q1": {}}
        m = evaluate_query(results, "q1", "query", qrels, ks=[5])
        assert m.precision[5] == 0.0
        assert m.ndcg[5] == 0.0

    def test_empty_results(self):
        qrels = {"q1": {"a": 1}}
        m = evaluate_query([], "q1", "query", qrels, ks=[5])
        assert m.precision[5] == 0.0
        assert m.recall[5] == 0.0

    def test_k_greater_than_results(self):
        results = [_FakeResult("a", 1.0), _FakeResult("b", 0.5)]
        qrels = {"q1": {"a": 1, "b": 1, "c": 1}}
        m = evaluate_query(results, "q1", "query", qrels, ks=[5])
        # Only 2 results, all relevant
        assert m.precision[5] == 2 / 5  # 2 relevant / 5 total considered
        assert m.recall[5] == 2 / 3  # 2 of 3 relevant found

    def test_threshold(self):
        results = [_FakeResult("a", 1.0)]
        qrels = {"q1": {"a": 1}}
        m = evaluate_query(results, "q1", "q", qrels, ks=[1], relevance_threshold=2)
        # grade 1 < threshold 2
        assert m.precision[1] == 0.0

    def test_query_not_in_qrels(self):
        results = [_FakeResult("x", 1.0)]
        m = evaluate_query(results, "unknown", "query", {}, ks=[5])
        assert m.precision[5] == 0.0

    def test_multiple_ks(self):
        results = [_FakeResult(f"item_{i}", 10.0 - i) for i in range(10)]
        qrels = {"q1": {f"item_{i}": 3 for i in range(5)}}
        m = evaluate_query(results, "q1", "query", qrels, ks=[3, 5, 10])
        assert m.precision[3] == 1.0
        assert m.recall[10] == 1.0

    def test_flat_dict(self):
        results = [_FakeResult("a", 1.0)]
        qrels = {"q1": {"a": 1}}
        m = evaluate_query(results, "q1", "query", qrels, ks=[5])
        d = m.to_flat_dict()
        assert d["query_id"] == "q1"
        assert "precision_at_5" in d

    def test_ndcg_zero_idcg(self):
        """All zero qrels → NDCG = 0."""
        results = [_FakeResult("a", 1.0)]
        qrels = {"q1": {"a": 0}}  # grade 0 = not relevant
        m = evaluate_query(results, "q1", "q", qrels, ks=[1])
        assert m.ndcg[1] == 0.0

    def test_single_graded_result(self):
        results = [_FakeResult("a", 1.0), _FakeResult("b", 0.9)]
        qrels = {"q1": {"a": 3, "b": 1}}
        m = evaluate_query(results, "q1", "q", qrels, ks=[2])
        # a is grade 3 at rank 1 → high NDCG
        assert m.ndcg[2] > 0.0


class TestEvaluateAll:
    def test_multiple_queries(self):
        all_results = {
            "q1": [_FakeResult("a", 1.0)],
            "q2": [_FakeResult("b", 1.0)],
        }
        queries = [
            {"query_id": "q1", "query_text": "text1"},
            {"query_id": "q2", "query_text": "text2"},
        ]
        qrels = {"q1": {"a": 1}, "q2": {"b": 1}}
        metrics = evaluate_all(all_results, queries, qrels, ks=[1])
        assert len(metrics) == 2

    def test_query_missing_text(self):
        all_results = {"q1": [_FakeResult("a", 1.0)]}
        metrics = evaluate_all(all_results, [], {"q1": {"a": 1}}, ks=[1])
        assert len(metrics) == 1
        assert metrics[0].query_text == "q1"  # falls back to query_id


class TestMacroAverage:
    def test_basic(self):
        m1 = MetricResult(query_id="q1", query_text="t1", ks=[5])
        m1.precision[5] = 0.8
        m1.recall[5] = 0.6

        m2 = MetricResult(query_id="q2", query_text="t2", ks=[5])
        m2.precision[5] = 0.4
        m2.recall[5] = 0.3

        avg = macro_average([m1, m2])
        assert avg["precision"][5] == pytest.approx(0.6)
        assert avg["recall"][5] == pytest.approx(0.45)

    def test_empty(self):
        assert macro_average([]) == {}
