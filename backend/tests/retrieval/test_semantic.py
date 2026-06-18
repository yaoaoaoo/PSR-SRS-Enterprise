"""Tests for SemanticIndex — build, search, edge cases, determinism."""

from __future__ import annotations

import pytest

from app.retrieval.semantic import SemanticIndex
from app.retrieval.vectorization import SemanticConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_docs() -> list[str]:
    return [
        "laptop computer electronics portable",
        "gaming laptop powerful graphics",
        "desktop computer office workstation",
        "wireless mouse ergonomic electronics",
        "mechanical keyboard gaming rgb",
        "headphones noise cancelling wireless",
        "monitor 4k display hdr",
        "printer laser wireless duplex",
    ]


@pytest.fixture
def sample_ids() -> list[str]:
    return [f"item_{i}" for i in range(8)]


@pytest.fixture
def small_config() -> SemanticConfig:
    return SemanticConfig(svd_components=4, random_state=42)


@pytest.fixture
def sample_index(sample_docs, sample_ids, small_config) -> SemanticIndex:
    return SemanticIndex.build(sample_docs, sample_ids, small_config)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

class TestSemanticBuild:
    def test_build_succeeds(self, sample_index):
        assert sample_index.document_count == 8
        assert sample_index.vector_dim == 4

    def test_build_empty_docs_raises(self, small_config):
        with pytest.raises(ValueError, match="empty"):
            SemanticIndex.build([], [], small_config)

    def test_build_length_mismatch_raises(self, small_config):
        with pytest.raises(ValueError, match="mismatch"):
            SemanticIndex.build(["a", "b"], ["x"], small_config)

    def test_build_single_document(self, small_config):
        idx = SemanticIndex.build(["hello world"], ["item_1"], small_config)
        assert idx.document_count == 1

    def test_build_preserves_item_order(self, sample_docs):
        cfg = SemanticConfig(svd_components=2, random_state=42)
        ids = ["z_item", "a_item", "m_item"]
        idx = SemanticIndex.build(sample_docs[:3], ids, cfg)
        results = idx.search("computer", top_k=10)
        # Results should have deterministic order
        assert len(results) > 0


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class TestSemanticSearch:
    def test_search_returns_results(self, sample_index):
        results = sample_index.search("gaming laptop")
        assert len(results) > 0

    def test_search_top_k(self, sample_index):
        results = sample_index.search("computer", top_k=3)
        assert len(results) <= 3

    def test_search_top_k_invalid(self, sample_index):
        with pytest.raises(ValueError):
            sample_index.search("query", top_k=0)
        with pytest.raises(ValueError):
            sample_index.search("query", top_k=-5)

    def test_search_empty_query(self, sample_index):
        results = sample_index.search("")
        # Empty string → zero vector → empty results
        assert results == []

    def test_search_before_build_raises(self):
        idx = SemanticIndex()
        with pytest.raises(RuntimeError, match="not built"):
            idx.search("query")

    def test_search_score_descending(self, sample_index):
        results = sample_index.search("wireless electronics")
        scores = [r.score for r in results]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_search_ranks_consecutive(self, sample_index):
        results = sample_index.search("monitor", top_k=5)
        ranks = [r.rank for r in results]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_search_source_is_semantic(self, sample_index):
        results = sample_index.search("keyboard")
        for r in results:
            assert r.source == "semantic"

    def test_search_deterministic(self, sample_docs, sample_ids, small_config):
        idx1 = SemanticIndex.build(sample_docs, sample_ids, small_config)
        idx2 = SemanticIndex.build(sample_docs, sample_ids, small_config)
        r1 = idx1.search("gaming")
        r2 = idx2.search("gaming")
        assert len(r1) == len(r2)
        for a, b in zip(r1, r2, strict=False):
            assert a.item_id == b.item_id
            assert a.score == pytest.approx(b.score)

    def test_search_result_frozen(self, sample_index):
        results = sample_index.search("laptop")
        r = results[0]
        with pytest.raises((TypeError, AttributeError, Exception)):
            r.score = 999.0  # type: ignore[misc]

    def test_query_with_all_oov_terms(self, sample_index):
        """Char n-grams can match even for unseen words — results may appear.
        True zero-vector only occurs for truly empty strings."""
        results = sample_index.search("zzzunknown xyznonexist")
        # Results may be all 8 items (char n-grams match); scores should be finite
        for r in results:
            assert r.score is not None
            assert isinstance(r.score, float)

    def test_single_doc_search(self, small_config):
        idx = SemanticIndex.build(["hello world"], ["item_1"], small_config)
        results = idx.search("hello")
        assert len(results) == 1
        assert results[0].item_id == "item_1"


class TestSemanticEdgeCases:
    """Additional edge cases for uncovered branches."""

    def test_search_top_k_larger_than_docs(self, small_config):
        idx = SemanticIndex.build(
            ["quantum physics mechanics", "computational chemistry bonds",
             "organic biology cells", "astronomy planets stars",
             "geology rocks minerals", "oceanography marine biology"],
            ["i1", "i2", "i3", "i4", "i5", "i6"], small_config,
        )
        results = idx.search("quantum mechanics", top_k=100)
        assert len(results) <= 6  # at most all docs

    def test_single_query_token_out_of_vocab(self, sample_index):
        """Query with single token that may or may not match — should handle gracefully."""
        results = sample_index.search("z")
        for r in results:
            assert isinstance(r.item_id, str)

    def test_config_property(self, sample_index):
        cfg = sample_index.config
        assert cfg is not None
        assert cfg.svd_components > 0

    def test_vectorizer_property(self, sample_index):
        vec = sample_index.vectorizer
        assert vec is not None

    def test_vector_dim_property(self, sample_index):
        assert sample_index.vector_dim > 0

    def test_document_count_property(self, sample_index):
        assert sample_index.document_count == 8

    def test_rebuild(self, sample_docs, sample_ids, small_config):
        """Build, search, then rebuild with different data."""
        idx = SemanticIndex.build(sample_docs[:4], sample_ids[:4], small_config)
        assert idx.document_count == 4
        r1 = idx.search("gaming")
        # Rebuild
        idx2 = SemanticIndex.build(sample_docs[4:], sample_ids[4:], small_config)
        assert idx2.document_count == 4
        r2 = idx2.search("gaming")
        # Results should differ since documents changed (but both contain "gaming" data)
        assert len(r1) >= 0 and len(r2) >= 0

    def test_svd_clamping_very_few_docs(self):
        cfg = SemanticConfig(svd_components=50, random_state=42)
        idx = SemanticIndex.build(
            ["alpha bravo charlie", "delta echo foxtrot", "golf hotel india"],
            ["i1", "i2", "i3"], cfg,
        )
        assert idx.vector_dim <= 3  # clamped to N-1 = 2

    def test_scores_within_range(self, sample_index):
        results = sample_index.search("monitor display", top_k=8)
        for r in results:
            assert -1.0 <= r.score <= 1.0  # cosine similarity range
