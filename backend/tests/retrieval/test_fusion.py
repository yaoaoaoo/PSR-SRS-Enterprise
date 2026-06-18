"""Tests for hybrid fusion — RRF, linear, candidates, edge cases."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from app.retrieval.fusion import (
    FusionConfig,
    build_candidates,
    fuse_linear,
    fuse_rrf,
)
from app.retrieval.types import SearchResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bm25(items: list[tuple[str, float]]) -> list[SearchResult]:
    return [
        SearchResult(item_id=iid, score=s, rank=rank, source="bm25")
        for rank, (iid, s) in enumerate(items, start=1)
    ]


def _make_semantic(items: list[tuple[str, float]]) -> list[SearchResult]:
    return [
        SearchResult(item_id=iid, score=s, rank=rank, source="semantic")
        for rank, (iid, s) in enumerate(items, start=1)
    ]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestFusionConfig:
    def test_defaults(self):
        cfg = FusionConfig()
        assert cfg.rrf_k == 60
        assert cfg.bm25_weight == 0.5
        assert cfg.semantic_weight == 0.5

    def test_from_dict(self):
        cfg = FusionConfig.from_dict({"rrf_k": 30, "candidate_k": 50})
        assert cfg.rrf_k == 30
        assert cfg.candidate_k == 50

    def test_from_dict_invalid_rrf_k(self):
        with pytest.raises(ValueError, match="rrf_k"):
            FusionConfig.from_dict({"rrf_k": 0})

    def test_from_dict_zero_weights(self):
        with pytest.raises(ValueError, match="weight"):
            FusionConfig.from_dict({"bm25_weight": 0, "semantic_weight": 0})

    def test_from_json(self):
        data = {"rrf_k": 45, "candidate_k": 80}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            cfg = FusionConfig.from_json(path)
            assert cfg.rrf_k == 45
        finally:
            Path(path).unlink()


# ---------------------------------------------------------------------------
# Candidate building
# ---------------------------------------------------------------------------

class TestBuildCandidates:
    def test_basic_union(self):
        bm25 = _make_bm25([("a", 3.0), ("b", 2.0)])
        sem = _make_semantic([("b", 5.0), ("c", 4.0)])
        cand = build_candidates(bm25, sem)
        assert set(cand.keys()) == {"a", "b", "c"}

    def test_both_sources(self):
        bm25 = _make_bm25([("x", 1.0)])
        sem = _make_semantic([("x", 2.0)])
        cand = build_candidates(bm25, sem)
        assert cand["x"]["sources"] == ("bm25", "semantic")

    def test_empty_bm25(self):
        sem = _make_semantic([("a", 1.0)])
        cand = build_candidates([], sem)
        assert len(cand) == 1
        assert cand["a"]["sources"] == ("semantic",)
        assert cand["a"]["bm25_rank"] is None

    def test_empty_semantic(self):
        bm25 = _make_bm25([("a", 1.0)])
        cand = build_candidates(bm25, [])
        assert len(cand) == 1
        assert cand["a"]["sources"] == ("bm25",)
        assert cand["a"]["semantic_rank"] is None

    def test_both_empty(self):
        cand = build_candidates([], [])
        assert cand == {}


# ---------------------------------------------------------------------------
# RRF
# ---------------------------------------------------------------------------

class TestFuseRRF:
    def test_basic(self):
        bm25 = _make_bm25([("a", 3.0), ("b", 2.0)])
        sem = _make_semantic([("b", 5.0), ("c", 4.0)])
        cand = build_candidates(bm25, sem)
        results = fuse_rrf(cand, rrf_k=60, top_k=10)
        # "b" appears in both → highest RRF score
        assert results[0].item_id == "b"
        # All items should appear
        ids = {r.item_id for r in results}
        assert ids == {"a", "b", "c"}

    def test_top_k_limit(self):
        bm25 = _make_bm25([("a", 3.0), ("b", 2.0), ("c", 1.0)])
        sem = _make_semantic([("d", 5.0)])
        cand = build_candidates(bm25, sem)
        results = fuse_rrf(cand, rrf_k=60, top_k=2)
        assert len(results) == 2

    def test_deterministic_tie_break(self):
        """Different ranks → different RRF scores.
        For true tie, need manually equal ranks."""
        bm25 = _make_bm25([("z", 1.0), ("a", 1.0)])
        sem: list[SearchResult] = []
        cand = build_candidates(bm25, sem)
        results = fuse_rrf(cand, rrf_k=60, top_k=10)
        # z has rank=1 (score 1/(60+1)), a has rank=2 (score 1/(60+2)) → z first
        assert results[0].item_id == "z"
        assert results[1].item_id == "a"

    def test_single_source(self):
        bm25 = _make_bm25([("x", 1.0)])
        cand = build_candidates(bm25, [])
        results = fuse_rrf(cand, rrf_k=60, top_k=10)
        assert len(results) == 1
        assert results[0].item_id == "x"

    def test_empty_candidates(self):
        results = fuse_rrf({}, rrf_k=60)
        assert results == []


# ---------------------------------------------------------------------------
# Linear fusion
# ---------------------------------------------------------------------------

class TestFuseLinear:
    def test_basic(self):
        bm25 = _make_bm25([("a", 3.0), ("b", 2.0)])
        sem = _make_semantic([("b", 5.0), ("c", 4.0)])
        cand = build_candidates(bm25, sem)
        results = fuse_linear(cand, bm25_weight=0.5, semantic_weight=0.5, top_k=10)
        assert len(results) == 3

    def test_scores_normalized(self):
        """After min-max normalization, scores should be in [0, 1]."""
        bm25 = _make_bm25([("a", 10.0), ("b", 5.0)])
        cand = build_candidates(bm25, [])
        results = fuse_linear(cand, bm25_weight=1.0, semantic_weight=0.0, top_k=10)
        assert 0.0 <= results[0].fusion_score <= 1.0

    def test_top_k(self):
        bm25 = _make_bm25([(f"item_{i}", float(10 - i)) for i in range(10)])
        cand = build_candidates(bm25, [])
        results = fuse_linear(cand, bm25_weight=1.0, semantic_weight=0.0, top_k=3)
        assert len(results) == 3

    def test_deterministic_tie_break(self):
        """All scores identical → deterministic ordering by item_id."""
        bm25 = _make_bm25([("z", 5.0), ("a", 5.0)])
        cand = build_candidates(bm25, [])
        results = fuse_linear(cand, bm25_weight=1.0, semantic_weight=0.0)
        assert results[0].item_id == "a"
        assert results[1].item_id == "z"

    def test_empty(self):
        results = fuse_linear({}, bm25_weight=0.5, semantic_weight=0.5)
        assert results == []

    def test_missing_source_none(self):
        """Item only in BM25 → semantic_normalized_score is None (not 0),
        matching MVP behaviour."""
        bm25 = _make_bm25([("x", 10.0)])
        cand = build_candidates(bm25, [])
        results = fuse_linear(cand, bm25_weight=0.5, semantic_weight=0.5)
        assert results[0].semantic_normalized_score is None
        assert results[0].bm25_normalized_score == 1.0
        assert results[0].semantic_rank is None

    def test_equal_weights(self):
        bm25 = _make_bm25([("a", 10.0), ("b", 1.0)])
        sem = _make_semantic([("b", 10.0), ("a", 1.0)])
        cand = build_candidates(bm25, sem)
        results = fuse_linear(cand, bm25_weight=0.5, semantic_weight=0.5)
        # Both items have complementary strengths → scores should be close
        assert abs(results[0].fusion_score - results[1].fusion_score) < 1.0
