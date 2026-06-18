"""Comprehensive tests for personalization evaluation module.

Covers compute_behavior_metrics, compute_qrels_metrics, macro_average_dict,
compute_candidate_coverage, and their edge cases.
"""

from __future__ import annotations

import pytest

from app.personalization.evaluation import (
    behavior_grade,
    compute_behavior_metrics,
    compute_candidate_coverage,
    compute_qrels_metrics,
    macro_average_dict,
)
from app.personalization.types import RankedItem

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(
    item_id: str,
    rank: int = 1,
    personalized_score: float = 1.0,
    behavior_grade: int = 0,
    qrels_grade: int = 0,
) -> RankedItem:
    return RankedItem(
        item_id=item_id,
        rank=rank,
        original_rank=rank,
        original_fusion_score=1.0,
        normalized_retrieval_score=1.0,
        category_affinity=0.0,
        subcategory_affinity=0.0,
        brand_affinity=0.0,
        price_affinity=0.0,
        personalized_score=personalized_score,
        profile_status="warm",
        is_cold_start=False,
        behavior_relevance_grade=behavior_grade,
        qrels_relevance_grade=qrels_grade,
    )


# ---------------------------------------------------------------------------
# behavior_grade
# ---------------------------------------------------------------------------

class TestBehaviorGrade:
    def test_returns_grade(self):
        assert behavior_grade("a", {"a": 3}) == 3

    def test_missing_returns_zero(self):
        assert behavior_grade("x", {"a": 1}) == 0

    def test_empty_grades(self):
        assert behavior_grade("a", {}) == 0


# ---------------------------------------------------------------------------
# compute_behavior_metrics
# ---------------------------------------------------------------------------

class TestComputeBehaviorMetrics:
    def test_all_positive_hit(self):
        items = [_make_item("a", 1), _make_item("b", 2)]
        grades = {"a": 1, "b": 1}
        pos = {"a", "b"}
        m = compute_behavior_metrics(items, grades, pos, ks=[2])
        assert m["hit_rate_at_2"] == 1.0

    def test_no_hit(self):
        items = [_make_item("a", 1)]
        m = compute_behavior_metrics(items, {"c": 1}, {"c"}, ks=[1])
        assert m["hit_rate_at_1"] == 0.0

    def test_mrr_at_k(self):
        items = [_make_item("a", 1), _make_item("b", 2)]
        pos = {"b"}
        m = compute_behavior_metrics(items, {}, pos, ks=[2])
        assert m["mrr_at_2"] == 0.5  # rank 2

    def test_mrr_no_match(self):
        items = [_make_item("a", 1)]
        m = compute_behavior_metrics(items, {}, {"z"}, ks=[1])
        assert m["mrr_at_1"] == 0.0

    def test_ndcg_with_grades(self):
        items = [
            _make_item("a", 1, behavior_grade=3),
            _make_item("b", 2, behavior_grade=1),
        ]
        grades = {"a": 3, "b": 1}
        m = compute_behavior_metrics(items, grades, {"a", "b"}, ks=[2])
        # DCG = (2^3-1)/log2(2) + (2^1-1)/log2(3) = 7/1 + 1/~1.585 ≈ 7.631
        # IDCG = 7/1 + 1/log2(3) ≈ same = 1.0 NDCG
        assert m["ndcg_at_2"] == pytest.approx(1.0)

    def test_ndcg_zero_idcg(self):
        items = [_make_item("a", 1)]
        m = compute_behavior_metrics(items, {}, set(), ks=[1])
        assert m["ndcg_at_1"] == 0.0

    def test_positive_recall(self):
        items = [_make_item("a", 1), _make_item("b", 2), _make_item("c", 3)]
        pos = {"a", "d", "e"}  # 1/3 covered
        m = compute_behavior_metrics(items, {}, pos, ks=[2])
        assert m["positive_recall_at_2"] == pytest.approx(1 / 3)

    def test_positive_recall_empty(self):
        items = [_make_item("a", 1)]
        m = compute_behavior_metrics(items, {}, set(), ks=[1])
        assert m["positive_recall_at_1"] == 0.0

    def test_k_larger_than_results(self):
        items = [_make_item("a", 1)]
        m = compute_behavior_metrics(items, {"a": 1}, {"a"}, ks=[10])
        assert m["hit_rate_at_10"] == 1.0

    def test_empty_results(self):
        m = compute_behavior_metrics([], {"a": 1}, {"a"}, ks=[5])
        assert m["hit_rate_at_5"] == 0.0
        assert m["mrr_at_5"] == 0.0

    def test_multiple_ks(self):
        items = [_make_item("a", 1), _make_item("b", 2)]
        m = compute_behavior_metrics(items, {"a": 1}, {"a"}, ks=[1, 2])
        assert "hit_rate_at_1" in m
        assert "hit_rate_at_2" in m


# ---------------------------------------------------------------------------
# compute_qrels_metrics
# ---------------------------------------------------------------------------

class TestComputeQrelsMetrics:
    def test_precision_recall(self):
        items = [_make_item("a", 1), _make_item("b", 2)]
        qrels = {"a": 3, "b": 0, "c": 1}  # 2 relevant
        m = compute_qrels_metrics(items, qrels, ks=[2])
        assert m["precision_at_2"] == 0.5  # a relevant, b not
        assert m["recall_at_2"] == 0.5  # 1/2 relevant found

    def test_no_relevant_in_qrels(self):
        items = [_make_item("a", 1)]
        m = compute_qrels_metrics(items, {}, ks=[1])
        assert m["precision_at_1"] == 0.0
        assert m["recall_at_1"] == 0.0

    def test_all_relevant(self):
        items = [_make_item("a", 1), _make_item("b", 2)]
        qrels = {"a": 3, "b": 3}
        m = compute_qrels_metrics(items, qrels, ks=[2])
        assert m["precision_at_2"] == 1.0

    def test_threshold(self):
        items = [_make_item("a", 1)]
        qrels = {"a": 1}
        m = compute_qrels_metrics(items, qrels, ks=[1], relevance_threshold=2)
        assert m["precision_at_1"] == 0.0  # grade 1 < threshold 2

    def test_mrr(self):
        items = [_make_item("a", 1), _make_item("b", 2)]
        qrels = {"b": 3}
        m = compute_qrels_metrics(items, qrels, ks=[2])
        assert m["mrr_at_2"] == 0.5

    def test_ndcg(self):
        items = [_make_item("a", 1), _make_item("b", 2)]
        qrels = {"a": 3, "b": 1}
        m = compute_qrels_metrics(items, qrels, ks=[2])
        # Perfect ordering (high grade first) → NDCG ≈ 1.0
        assert m["ndcg_at_2"] > 0.5

    def test_ndcg_all_zero(self):
        items = [_make_item("a", 1)]
        qrels = {"a": 0}
        m = compute_qrels_metrics(items, qrels, ks=[1])
        assert m["ndcg_at_1"] == 0.0

    def test_empty_results(self):
        m = compute_qrels_metrics([], {"a": 1}, ks=[5])
        assert m["precision_at_5"] == 0.0

    def test_k_larger_than_results(self):
        items = [_make_item("a", 1)]
        qrels = {"a": 3, "b": 1}  # 2 relevant total
        m = compute_qrels_metrics(items, qrels, ks=[5])
        assert m["precision_at_5"] == 0.2  # 1/5
        assert m["recall_at_5"] == 0.5  # 1/2


# ---------------------------------------------------------------------------
# macro_average_dict
# ---------------------------------------------------------------------------

class TestMacroAverageDict:
    def test_basic(self):
        metrics = [
            {"precision_at_5": 0.8, "recall_at_5": 0.6},
            {"precision_at_5": 0.4, "recall_at_5": 0.2},
        ]
        result = macro_average_dict(metrics, ["precision_at_5"])
        assert result["precision_at_5"] == pytest.approx(0.6)

    def test_empty_metrics(self):
        result = macro_average_dict([], ["precision_at_5"])
        assert result["precision_at_5"] == 0.0

    def test_missing_keys(self):
        """Values for keys not present in a metrics dict are excluded from that
        metric's average (not defaulted to 0.0)."""
        metrics = [{"precision_at_5": 0.8}, {"recall_at_5": 0.2}]
        result = macro_average_dict(metrics, ["precision_at_5", "recall_at_5"])
        # precision appeared in 1/1 (only first dict has it) → 0.8/1 = 0.8
        assert result["precision_at_5"] == 0.8
        # recall appeared in 1/1 (only second dict has it) → 0.2/1 = 0.2
        assert result["recall_at_5"] == 0.2

    def test_missing_key_in_all(self):
        """When no metrics dict contains the key, average is 0.0."""
        result = macro_average_dict([{"a": 1.0}, {"a": 2.0}], ["b"])
        assert result["b"] == 0.0

    def test_single_metric(self):
        m = macro_average_dict([{"a": 1.0}], ["a"])
        assert m["a"] == 1.0


# ---------------------------------------------------------------------------
# compute_candidate_coverage
# ---------------------------------------------------------------------------

class TestComputeCandidateCoverage:
    def test_full_coverage(self):
        test_requests = {
            "r1": {
                "query_id": "q1",
                "items": {"i1": 1, "i2": 0},
                "profile_status": "warm",
            },
        }
        candidates_by_qid = {
            "q1": [{"item_id": "i1"}, {"item_id": "i2"}],
        }
        result = compute_candidate_coverage(
            test_requests, candidates_by_qid, ["r1"]
        )
        assert result["request_level_candidate_positive_coverage"] == 1.0
        assert result["item_level_candidate_positive_recall"] == 1.0
        assert result["covered_positive_request_count"] == 1

    def test_no_coverage(self):
        test_requests = {
            "r1": {
                "query_id": "q1",
                "items": {"i1": 1},
                "profile_status": "warm",
            },
        }
        candidates_by_qid = {"q1": []}
        result = compute_candidate_coverage(
            test_requests, candidates_by_qid, ["r1"]
        )
        assert result["request_level_candidate_positive_coverage"] == 0.0
        assert result["uncovered_positive_request_count"] == 1

    def test_empty_eligible(self):
        result = compute_candidate_coverage({}, {}, [])
        assert result["eligible_positive_request_count"] == 0
        assert result["request_level_candidate_positive_coverage"] == 0

    def test_missing_query_candidates(self):
        test_requests = {
            "r1": {"query_id": "q_nonexist", "items": {"i1": 1}, "profile_status": "warm"},
        }
        result = compute_candidate_coverage(
            test_requests, {}, ["r1"]
        )
        assert result["request_level_candidate_positive_coverage"] == 0.0

    def test_eligible_not_in_test_requests(self):
        """eligible_rids includes an ID not in test_requests — should skip gracefully."""
        test_requests = {
            "r1": {"query_id": "q1", "items": {"i1": 1}, "profile_status": "warm"},
        }
        candidates_by_qid = {"q1": [{"item_id": "i1"}]}
        result = compute_candidate_coverage(
            test_requests, candidates_by_qid, ["r1", "r_missing"]
        )
        assert result["eligible_positive_request_count"] == 2
        # r_missing skipped — only r1 counted in covered/uncovered
        assert result["covered_positive_request_count"] == 1
        assert result["uncovered_positive_request_count"] == 0

    def test_warm_vs_cold_split(self):
        test_requests = {
            "r_warm": {"query_id": "q1", "items": {"i1": 1}, "profile_status": "warm"},
            "r_cold": {"query_id": "q2", "items": {"i2": 1}, "profile_status": "cold_start"},
        }
        candidates_by_qid = {
            "q1": [{"item_id": "i1"}],
            "q2": [],  # cold user has no coverage
        }
        result = compute_candidate_coverage(
            test_requests, candidates_by_qid, ["r_warm", "r_cold"]
        )
        assert result["warm_request_coverage"] == 1.0
        assert result["fallback_request_coverage"] == 0.0

    def test_no_positive_items(self):
        test_requests = {
            "r1": {"query_id": "q1", "items": {"i1": 0}, "profile_status": "warm"},
        }
        candidates_by_qid = {"q1": [{"item_id": "i1"}]}
        result = compute_candidate_coverage(
            test_requests, candidates_by_qid, ["r1"]
        )
        assert result["total_positive_item_count"] == 0
        assert result["item_level_candidate_positive_recall"] == 0

    def test_all_pos_items_covered(self):
        test_requests = {
            "r1": {"query_id": "q1", "items": {"a": 1, "b": 2, "c": 3}, "profile_status": "warm"},
        }
        candidates_by_qid = {"q1": [{"item_id": "a"}, {"item_id": "b"}, {"item_id": "c"}]}
        result = compute_candidate_coverage(
            test_requests, candidates_by_qid, ["r1"]
        )
        assert result["covered_positive_item_count"] == 3
        assert result["item_level_candidate_positive_recall"] == 1.0

    def test_return_field_types(self):
        result = compute_candidate_coverage({}, {}, [])
        assert isinstance(result["eligible_positive_request_count"], int)
        assert isinstance(result["request_level_candidate_positive_coverage"], float)

    def test_input_not_modified(self):
        test_requests = {"r1": {"query_id": "q1", "items": {"i1": 1}}}
        candidates_by_qid = {"q1": [{"item_id": "i1"}]}
        before_req = dict(test_requests)
        before_cand = dict(candidates_by_qid)
        compute_candidate_coverage(test_requests, candidates_by_qid, ["r1"])
        assert test_requests == before_req
        assert candidates_by_qid == before_cand

    def test_unknown_profile_status(self):
        test_requests = {
            "r1": {"query_id": "q1", "items": {"i1": 1}, "profile_status": "unknown"},
        }
        candidates_by_qid = {"q1": [{"item_id": "i1"}]}
        result = compute_candidate_coverage(
            test_requests, candidates_by_qid, ["r1"]
        )
        # Unknown → treated as non-warm (cold_total, fallback)
        assert result["fallback_request_coverage"] == 1.0
        assert result["warm_request_coverage"] == 0
