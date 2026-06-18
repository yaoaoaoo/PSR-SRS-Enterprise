"""TF-IDF + TruncatedSVD vectorisation pipeline for LSA semantic retrieval.

Uses scikit-learn.  Strictly **inductive**: fit only on item documents;
queries are transformed afterwards.  Instance-level ``RLock`` protects the
mutable sklearn transformers during concurrent reads.

Identical algorithm to PSR-SRS-MVP.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.sparse import hstack
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class SemanticConfig:
    """Typed configuration for LSA semantic retrieval.

    Attributes:
        word_ngram_range: Word n-gram range for TF-IDF.
        char_ngram_range: Character n-gram range for TF-IDF.
        word_weight: Weight multiplier for word features.
        char_weight: Weight multiplier for character features.
        min_df: Minimum document frequency for TF-IDF.
        max_df: Maximum document frequency (proportion) for TF-IDF.
        sublinear_tf: Apply ``1 + log(tf)`` if True.
        svd_components: Target number of SVD latent dimensions.
        random_state: Fixed seed for deterministic SVD.
        top_k_values: K cutoffs for evaluation.
        relevance_threshold: Minimum qrels grade for relevance.
    """

    word_ngram_range: list[int] = field(default_factory=lambda: [1, 2])
    char_ngram_range: list[int] = field(default_factory=lambda: [3, 5])
    word_weight: float = 1.0
    char_weight: float = 0.5
    min_df: int = 1
    max_df: float = 1.0
    sublinear_tf: bool = True
    svd_components: int = 64
    random_state: int = 20260614
    top_k_values: list[int] = field(default_factory=lambda: [5, 10, 20])
    relevance_threshold: int = 1

    @property
    def max_k(self) -> int:
        return max(self.top_k_values) if self.top_k_values else 20

    def validate(self) -> list[str]:
        """Return a list of validation errors (empty if valid)."""
        errors: list[str] = []
        for name, rng in [("word_ngram_range", self.word_ngram_range),
                          ("char_ngram_range", self.char_ngram_range)]:
            if len(rng) != 2:
                errors.append(f"{name} must have 2 elements")
            elif not (isinstance(rng[0], int) and isinstance(rng[1], int) and rng[0] >= 1 and rng[1] >= 1):
                errors.append(f"{name} must be positive ints")
            elif rng[0] > rng[1]:
                errors.append(f"{name}: min > max")
        if self.word_weight < 0 or self.char_weight < 0:
            errors.append("weights must be non-negative")
        if self.word_weight == 0 and self.char_weight == 0:
            errors.append("at least one weight must be > 0")
        if self.svd_components < 2:
            errors.append("svd_components must be >= 2")
        if not isinstance(self.random_state, int):
            errors.append("random_state must be int")
        if not self.top_k_values:
            errors.append("top_k_values must not be empty")
        for k in self.top_k_values:
            if k <= 0 or not isinstance(k, int):
                errors.append(f"top_k_values must be positive ints, got {k}")
        if self.relevance_threshold not in (1, 2, 3):
            errors.append("relevance_threshold must be 1, 2, or 3")
        if self.min_df < 1:
            errors.append("min_df must be >= 1")
        if not (0 < self.max_df <= 1.0):
            errors.append("max_df must be in (0, 1]")
        return errors

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> SemanticConfig:
        """Create a validated config from a dictionary."""
        valid_keys = set(cls.__dataclass_fields__.keys())
        kwargs = {k: v for k, v in data.items() if k in valid_keys}
        cfg = cls(**kwargs)  # type: ignore[arg-type]
        errs = cfg.validate()
        if errs:
            raise ValueError("\n".join(errs))
        return cfg

    @classmethod
    def from_json(cls, path: str | Path) -> SemanticConfig:
        """Load config from a JSON file (convenience for offline scripts)."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)


# ---------------------------------------------------------------------------
# Vectoriser pipeline
# ---------------------------------------------------------------------------

class SemanticVectorizer:
    """TF-IDF + TruncatedSVD pipeline with L2-normalised output.

    Built **inductively**: TF-IDF vocabulary and SVD are fit on item
    documents only.  Queries are transformed through the same pipeline
    without re-fitting.

    An instance-level ``threading.RLock`` guards ``transform`` and
    ``fit`` calls so that scikit-learn's mutable internal state is
    never accessed concurrently.
    """

    def __init__(self, config: SemanticConfig):
        self.cfg = config
        self._lock = threading.RLock()

        # Word-level TF-IDF
        self._word_vec = TfidfVectorizer(
            analyzer="word",
            ngram_range=tuple(config.word_ngram_range),
            min_df=config.min_df,
            max_df=config.max_df,
            sublinear_tf=config.sublinear_tf,
            norm=None,  # we normalise after SVD
        )

        # Character-level TF-IDF
        self._char_vec = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=tuple(config.char_ngram_range),
            min_df=config.min_df,
            max_df=config.max_df,
            sublinear_tf=config.sublinear_tf,
            norm=None,
        )

        self._svd: TruncatedSVD | None = None
        self._svd_actual: int = 0

        # State
        self._fitted: bool = False
        self.word_feature_count: int = 0
        self.char_feature_count: int = 0
        self.combined_feature_count: int = 0

    # ------------------------------------------------------------------
    # Fit (items only — inductive)
    # ------------------------------------------------------------------

    def fit(self, documents: Sequence[str]) -> SemanticVectorizer:
        """Fit TF-IDF and SVD on item documents.

        Acquires the write lock — do not call concurrently.
        """
        with self._lock:
            # Fit TF-IDF
            word_matrix = self._word_vec.fit_transform(documents)
            char_matrix = self._char_vec.fit_transform(documents)

            self.word_feature_count = word_matrix.shape[1]
            self.char_feature_count = char_matrix.shape[1]

            # Weighted combination
            combined = self._combine(word_matrix, char_matrix)
            self.combined_feature_count = combined.shape[1]

            # Fit SVD — clamp dimensions to what the data supports
            actual = min(
                self.cfg.svd_components,
                combined.shape[1] - 1,
                combined.shape[0] - 1,
            )
            actual = max(actual, 2)  # floor
            self._svd_actual = actual
            self._svd = TruncatedSVD(
                n_components=actual,
                random_state=self.cfg.random_state,
            )
            self._svd.fit(combined)
            self._fitted = True
            return self

    # ------------------------------------------------------------------
    # Transform
    # ------------------------------------------------------------------

    def transform(self, texts: Sequence[str]) -> np.ndarray:
        """Transform texts through the fitted pipeline → L2-normalised vectors.

        Acquires the read lock — safe for concurrent reads.
        """
        with self._lock:
            if not self._fitted:
                raise RuntimeError("SemanticVectorizer not fitted. Call fit() first.")

            assert self._svd is not None
            word_matrix = self._word_vec.transform(texts)
            char_matrix = self._char_vec.transform(texts)
            combined = self._combine(word_matrix, char_matrix)
            latent = self._svd.transform(combined)
            return normalize(latent, norm="l2", copy=False)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def svd_components_actual(self) -> int:
        return self._svd_actual

    @property
    def explained_variance_ratio_sum(self) -> float:
        if self._svd is None:
            return 0.0
        return float(self._svd.explained_variance_ratio_.sum())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _combine(self, word_m, char_m):
        parts = []
        if self.cfg.word_weight > 0:
            parts.append(word_m * self.cfg.word_weight)
        if self.cfg.char_weight > 0:
            parts.append(char_m * self.cfg.char_weight)
        if len(parts) == 2:
            return hstack(parts, format="csr")
        return parts[0]


def is_zero_vector(vec: np.ndarray) -> bool:
    """Check if a single vector has zero L2 norm (all elements zero)."""
    return bool(np.allclose(vec, 0.0))
