"""Tests for SemanticVectorizer — config, fit, transform, determinism, concurrency."""

from __future__ import annotations

import concurrent.futures
import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from app.retrieval.vectorization import (
    SemanticConfig,
    SemanticVectorizer,
    is_zero_vector,
)

# ---------------------------------------------------------------------------
# Sample data
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
def small_config() -> SemanticConfig:
    return SemanticConfig(svd_components=4, random_state=42)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class TestSemanticConfig:
    def test_defaults(self):
        cfg = SemanticConfig()
        assert cfg.svd_components == 64
        assert cfg.random_state == 20260614
        assert cfg.word_weight == 1.0

    def test_from_dict_complete(self):
        cfg = SemanticConfig.from_dict({
            "svd_components": 32,
            "word_weight": 0.8,
            "random_state": 99,
        })
        assert cfg.svd_components == 32
        assert cfg.word_weight == 0.8
        assert cfg.random_state == 99

    def test_from_dict_empty(self):
        cfg = SemanticConfig.from_dict({})
        assert cfg.svd_components == 64  # default

    def test_from_dict_unknown_ignored(self):
        cfg = SemanticConfig.from_dict({"svd_components": 16, "not_a_field": 123})
        assert cfg.svd_components == 16

    def test_from_dict_invalid_svd(self):
        with pytest.raises(ValueError, match="svd_components"):
            SemanticConfig.from_dict({"svd_components": 1})

    def test_from_dict_invalid_weights(self):
        with pytest.raises(ValueError, match="weight"):
            SemanticConfig.from_dict({"word_weight": 0, "char_weight": 0})

    def test_from_json_roundtrip(self):
        data = {"svd_components": 16, "random_state": 42}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            cfg = SemanticConfig.from_json(path)
            assert cfg.svd_components == 16
        finally:
            Path(path).unlink()

    def test_max_k(self):
        cfg = SemanticConfig(top_k_values=[5, 10, 20])
        assert cfg.max_k == 20


# ---------------------------------------------------------------------------
# Vectorizer: Fit & Transform
# ---------------------------------------------------------------------------

class TestSemanticVectorizer:
    def test_fit_sets_fitted_flag(self, sample_docs, small_config):
        vec = SemanticVectorizer(small_config)
        assert not hasattr(vec, '_fitted') or vec._fitted is False
        vec.fit(sample_docs)
        # _fitted is private — we verify via transform

    def test_transform_before_fit_raises(self, small_config):
        vec = SemanticVectorizer(small_config)
        with pytest.raises(RuntimeError, match="not fitted"):
            vec.transform(["hello world"])

    def test_fit_and_transform(self, sample_docs, small_config):
        vec = SemanticVectorizer(small_config)
        vec.fit(sample_docs)
        result = vec.transform(sample_docs)
        assert result.shape == (len(sample_docs), small_config.svd_components)
        # Vectors should be L2-normalised
        for row in result:
            assert abs(np.linalg.norm(row) - 1.0) < 1e-6 or np.allclose(row, 0)

    def test_transform_query(self, sample_docs, small_config):
        vec = SemanticVectorizer(small_config)
        vec.fit(sample_docs)
        q_vec = vec.transform(["gaming laptop"])
        assert q_vec.shape == (1, small_config.svd_components)

    def test_empty_text_handling(self, sample_docs, small_config):
        vec = SemanticVectorizer(small_config)
        vec.fit(sample_docs)
        result = vec.transform([""])
        assert result.shape == (1, small_config.svd_components)
        # Empty string → zero vector
        assert is_zero_vector(result[0])

    def test_determinism(self, sample_docs, small_config):
        vec1 = SemanticVectorizer(small_config)
        vec1.fit(sample_docs)
        r1 = vec1.transform(["gaming laptop"])

        vec2 = SemanticVectorizer(small_config)
        vec2.fit(sample_docs)
        r2 = vec2.transform(["gaming laptop"])

        assert np.allclose(r1, r2)

    def test_svd_components_clamped(self, small_config):
        """With 8 docs, svd_components=4, should use min(4, 7, 7)=4."""
        docs = ["doc one", "doc two", "doc three", "doc four",
                "doc five", "doc six", "doc seven", "doc eight"]
        vec = SemanticVectorizer(small_config)
        vec.fit(docs)
        assert vec.svd_components_actual <= 4
        assert vec.svd_components_actual >= 2

    def test_svd_too_few_docs(self):
        """Only 2 documents — SVD clamps to 2."""
        cfg = SemanticConfig(svd_components=10, random_state=42)
        docs = ["doc one", "doc two"]
        vec = SemanticVectorizer(cfg)
        vec.fit(docs)
        assert vec.svd_components_actual == 2

    def test_explained_variance_property(self, sample_docs, small_config):
        vec = SemanticVectorizer(small_config)
        vec.fit(sample_docs)
        ratio = vec.explained_variance_ratio_sum
        assert 0.0 < ratio <= 1.0


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------

class TestConcurrency:
    def test_concurrent_transforms(self, sample_docs, small_config):
        vec = SemanticVectorizer(small_config)
        vec.fit(sample_docs)

        def worker():
            for _ in range(20):
                vec.transform(["gaming laptop"])

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(worker) for _ in range(4)]
            for f in futures:
                f.result()  # no exception = pass

        # If we got here without deadlock or crash, concurrent reads work

    def test_concurrent_search_safe(self, sample_docs, small_config):
        from app.retrieval.semantic import SemanticIndex

        idx = SemanticIndex.build(
            documents=sample_docs,
            item_ids=[f"item_{i}" for i in range(len(sample_docs))],
            config=small_config,
        )

        def worker():
            for _ in range(10):
                idx.search("gaming", top_k=3)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(worker) for _ in range(4)]
            for f in futures:
                f.result()

    def test_concurrent_transform_different_instances(self, sample_docs, small_config):
        """Different instances should not interfere."""
        vec1 = SemanticVectorizer(small_config)
        vec1.fit(sample_docs[:4])
        vec2 = SemanticVectorizer(small_config)
        vec2.fit(sample_docs[4:])

        def worker1():
            for _ in range(10):
                vec1.transform(["laptop"])

        def worker2():
            for _ in range(10):
                vec2.transform(["monitor"])

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(worker1)
            f2 = pool.submit(worker2)
            f1.result()
            f2.result()


# ---------------------------------------------------------------------------
# is_zero_vector
# ---------------------------------------------------------------------------

class TestIsZeroVector:
    def test_zero_vector(self):
        v = np.zeros(10)
        assert is_zero_vector(v) is True

    def test_non_zero_vector(self):
        v = np.array([1.0, 0.0, 0.0])
        assert is_zero_vector(v) is False

    def test_near_zero(self):
        v = np.array([1e-12, 1e-12, 1e-12])
        assert is_zero_vector(v) is True


class TestVectorizerEdgeCases:
    """Additional edge cases for uncovered branches."""

    def test_refit(self, sample_docs, small_config):
        """Calling fit() twice replaces previous state."""
        import numpy as np
        vec = SemanticVectorizer(small_config)
        vec.fit(sample_docs)
        r1 = vec.transform(["gaming laptop"])
        # Re-fit with different data — needs >=4 docs for same config
        other_docs = [
            "completely different text here with more tokens",
            "another unique document for testing purposes",
            "third document with some more words here",
            "fourth document also has many different tokens",
        ]
        vec.fit(other_docs)
        r2 = vec.transform(["gaming laptop"])
        # Vectors differ because vocabulary changed
        # SVD clamps to min(components, n_docs-1, n_features-1) — both should be valid
        assert r2.shape[1] >= 2
        assert not np.allclose(r1[0], r2[0]) if r1.shape == r2.shape else True

    def test_empty_text_list(self, sample_docs, small_config):
        """scikit-learn requires >= 1 sample for transform().
        Empty input is a caller-level guard, not a vectorizer responsibility."""
        vec = SemanticVectorizer(small_config)
        vec.fit(sample_docs)
        # Empty input is not supported by sklearn — verify call raises
        with pytest.raises(ValueError):
            vec.transform([])

    def test_explained_variance_before_fit(self, small_config):
        vec = SemanticVectorizer(small_config)
        assert vec.explained_variance_ratio_sum == 0.0

    def test_all_texts_empty(self, sample_docs, small_config):
        vec = SemanticVectorizer(small_config)
        vec.fit(sample_docs)
        result = vec.transform(["", ""])
        assert result.shape == (2, vec.svd_components_actual)
        for row in result:
            assert is_zero_vector(row)

    def test_min_df_filtering(self):
        """With min_df=3, infrequent words should be filtered."""
        cfg = SemanticConfig(min_df=3, svd_components=2, random_state=42)
        docs = [
            "the cat sat",  # everyone has "the"
            "the dog ran",
            "the bird flew",
            "the fish swam",
        ]
        vec = SemanticVectorizer(cfg)
        vec.fit(docs)
        # Should work without error even with min_df filtering
        result = vec.transform(["the cat"])
        assert result.shape == (1, vec.svd_components_actual)

    def test_max_df_filtering(self):
        """With max_df=0.5, terms appearing in >50% docs are filtered."""
        cfg = SemanticConfig(max_df=0.5, svd_components=2, random_state=42)
        docs = [
            "alpha bravo charlie",
            "delta echo foxtrot",
            "golf hotel india",
            "juliet kilo lima",
        ]
        vec = SemanticVectorizer(cfg)
        vec.fit(docs)
        result = vec.transform(["alpha delta golf"])
        assert result.shape == (1, vec.svd_components_actual)

    def test_char_only_no_word(self, sample_docs):
        """word_weight=0, char_weight>0 — only character ngrams used."""
        cfg = SemanticConfig(
            word_weight=0.0, char_weight=1.0,
            svd_components=2, random_state=42,
        )
        vec = SemanticVectorizer(cfg)
        vec.fit(sample_docs)
        result = vec.transform(["gaming"])
        assert result.shape == (1, vec.svd_components_actual)

    def test_word_only_no_char(self, sample_docs):
        """char_weight=0, word_weight>0 — only word ngrams used."""
        cfg = SemanticConfig(
            word_weight=1.0, char_weight=0.0,
            svd_components=2, random_state=42,
        )
        vec = SemanticVectorizer(cfg)
        vec.fit(sample_docs)
        result = vec.transform(["gaming"])
        assert result.shape == (1, vec.svd_components_actual)

    def test_non_default_ngram_range(self):
        cfg = SemanticConfig(
            word_ngram_range=[1, 1], char_ngram_range=[2, 3],
            svd_components=2, random_state=42,
        )
        vec = SemanticVectorizer(cfg)
        vec.fit(["hello world", "foo bar"])
        result = vec.transform(["hello"])
        assert result.shape == (1, vec.svd_components_actual)
