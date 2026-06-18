"""Tests for BM25 index — build, search, configuration, tie-breaking."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from app.retrieval.bm25 import BM25Config, BM25Index

# ---------------------------------------------------------------------------
# Shared fixture — small in-memory item set
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_items() -> list[tuple[str, str]]:
    """Five simple items with controlled overlap."""
    return [
        ("i1", "laptop computer electronics"),
        ("i2", "gaming laptop powerful"),
        ("i3", "desktop computer office"),
        ("i4", "wireless mouse electronics"),
        ("i5", "mechanical keyboard gaming"),
    ]


@pytest.fixture
def sample_index(sample_items) -> BM25Index:
    """A pre-built BM25 index over the sample items."""
    return BM25Index.build(sample_items, k1=1.5, b=0.75)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class TestBM25Config:
    """Configuration creation and validation."""

    def test_default_construction(self):
        cfg = BM25Config()
        assert cfg.k1 == 1.5
        assert cfg.b == 0.75
        assert cfg.top_k_values == [5, 10, 20]
        assert cfg.relevance_threshold == 1

    def test_from_dict_complete(self):
        cfg = BM25Config.from_dict({"k1": 2.0, "b": 0.5, "top_k_values": [10]})
        assert cfg.k1 == 2.0
        assert cfg.b == 0.5
        assert cfg.top_k_values == [10]

    def test_from_dict_partial(self):
        cfg = BM25Config.from_dict({"k1": 1.2})
        assert cfg.k1 == 1.2
        assert cfg.b == 0.75  # default

    def test_from_dict_empty(self):
        cfg = BM25Config.from_dict({})
        assert cfg.k1 == 1.5  # defaults

    def test_from_dict_unknown_fields_ignored(self):
        cfg = BM25Config.from_dict({"k1": 1.5, "extra_thing": 999})
        assert cfg.k1 == 1.5

    def test_from_dict_invalid_k1(self):
        with pytest.raises(ValueError, match="k1"):
            BM25Config.from_dict({"k1": 0})

    def test_from_dict_invalid_b(self):
        with pytest.raises(ValueError, match="b"):
            BM25Config.from_dict({"b": 2.0})

    def test_from_json_roundtrip(self):
        cfg = BM25Config(k1=1.8, b=0.6)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"k1": 1.8, "b": 0.6}, f)
            path = f.name
        try:
            loaded = BM25Config.from_json(path)
            assert loaded.k1 == cfg.k1
            assert loaded.b == cfg.b
        finally:
            Path(path).unlink()

    def test_max_k_property(self):
        cfg = BM25Config(top_k_values=[5, 10, 20])
        assert cfg.max_k == 20

    def test_validate_empty_field_weights(self):
        cfg = BM25Config(field_weights={})
        errs = cfg.validate()
        assert len(errs) > 0
        assert any("field_weights" in e for e in errs)


# ---------------------------------------------------------------------------
# BM25 Index: Build
# ---------------------------------------------------------------------------

class TestBM25Build:
    """Index construction."""

    def test_build_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            BM25Index.build([], k1=1.5, b=0.75)

    def test_build_k1_zero_raises(self, sample_items):
        with pytest.raises(ValueError, match="k1"):
            BM25Index.build(sample_items, k1=0, b=0.75)

    def test_build_b_out_of_range_raises(self, sample_items):
        with pytest.raises(ValueError, match="b"):
            BM25Index.build(sample_items, k1=1.5, b=-0.1)

    def test_build_succeeds(self, sample_index):
        assert sample_index.document_count == 5

    def test_pre_tokenized_input(self):
        idx = BM25Index.build(
            [("a", ["hello", "world"]), ("b", ["foo", "bar"])],
            k1=1.5, b=0.75,
        )
        assert idx.document_count == 2

    def test_string_input_tokenized(self):
        idx = BM25Index.build(
            [("a", "hello world"), ("b", "foo bar")],
            k1=1.5, b=0.75,
        )
        assert idx.document_count == 2
        assert idx.vocabulary_size == 4

    def test_build_sets_properties(self, sample_index):
        assert sample_index.k1 == 1.5
        assert sample_index.b == 0.75
        assert sample_index.avgdl > 0
        assert sample_index.vocabulary_size > 0


# ---------------------------------------------------------------------------
# BM25 Index: Search
# ---------------------------------------------------------------------------

class TestBM25Search:
    """Query execution."""

    def test_search_returns_results(self, sample_index):
        results = sample_index.search("laptop")
        assert len(results) > 0
        assert results[0].item_id in ("i1", "i2")

    def test_search_top_k(self, sample_index):
        results = sample_index.search("computer", top_k=2)
        assert len(results) <= 2

    def test_search_top_k_zero_raises(self, sample_index):
        with pytest.raises(ValueError, match="top_k"):
            sample_index.search("laptop", top_k=0)

    def test_search_top_k_negative_raises(self, sample_index):
        with pytest.raises(ValueError, match="top_k"):
            sample_index.search("laptop", top_k=-1)

    def test_search_empty_query(self, sample_index):
        results = sample_index.search("")
        assert results == []

    def test_search_stopwords_only_query(self, sample_index):
        results = sample_index.search("the and of")
        assert results == []

    def test_search_unknown_word(self, sample_index):
        results = sample_index.search("zzzunknown")
        assert results == []

    def test_search_score_descending(self, sample_index):
        results = sample_index.search("computer laptop")
        # Scores should be non-increasing
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    def test_search_ranks_are_consecutive(self, sample_index):
        results = sample_index.search("mouse", top_k=5)
        ranks = [r.rank for r in results]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_search_source_is_bm25(self, sample_index):
        results = sample_index.search("laptop")
        assert all(r.source == "bm25" for r in results)

    def test_search_before_build_raises(self):
        idx = BM25Index()
        with pytest.raises(RuntimeError, match="not built"):
            idx.search("query")

    def test_search_deterministic_tie_break(self):
        """Same score → item_id ascending for stable ordering."""
        # Create two documents with identical content
        idx = BM25Index.build(
            [("z", "same content"), ("a", "same content")],
            k1=1.5, b=0.75,
        )
        results = idx.search("same content")
        assert results[0].item_id == "a"
        assert results[1].item_id == "z"

    def test_search_result_is_frozen(self, sample_index):
        results = sample_index.search("laptop")
        r = results[0]
        with pytest.raises((TypeError, AttributeError, Exception)):
            r.score = 999.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BM25 Index: Re-build
# ---------------------------------------------------------------------------

class TestBM25Rebuild:
    """Rebuilding behaviour."""

    def test_rebuild_creates_fresh_index(self, sample_items):
        idx1 = BM25Index.build(sample_items)
        idx2 = BM25Index.build(sample_items)
        r1 = idx1.search("laptop", top_k=5)
        r2 = idx2.search("laptop", top_k=5)
        assert len(r1) == len(r2)
        for a, b in zip(r1, r2, strict=False):
            assert a.item_id == b.item_id
            assert a.score == pytest.approx(b.score)
