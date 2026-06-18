"""Standard Okapi BM25 index with deterministic tie-breaking.

Pure Python 3.11+ stdlib for the core algorithm — no ``rank_bm25`` or NumPy
dependency.  Identical scoring to PSR-SRS-MVP.

.. code-block:: python

    config = BM25Config.from_dict({"k1": 1.5, "b": 0.75})
    index = BM25Index.build(documents, k1=config.k1, b=config.b)
    results = index.search("query text", top_k=10)
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from app.retrieval.tokenization import tokenize
from app.retrieval.types import SearchResult

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class BM25Config:
    """Typed BM25 configuration.

    Attributes:
        k1: Term frequency saturation parameter (> 0).
        b: Length normalisation parameter (0 ≤ b ≤ 1).
        top_k_values: K cutoffs for evaluation.
        relevance_threshold: Minimum qrels grade for relevance.
        field_weights: Per-field repetition counts for ``build_item_text``.
        use_stopwords: Whether to filter stop-words during tokenisation.
    """

    k1: float = 1.5
    b: float = 0.75
    top_k_values: list[int] = field(default_factory=lambda: [5, 10, 20])
    relevance_threshold: int = 1
    field_weights: dict[str, int] = field(default_factory=lambda: {
        "title": 3, "description": 1, "category": 2, "subcategory": 2, "brand": 2,
    })
    use_stopwords: bool = True

    @property
    def max_k(self) -> int:
        return max(self.top_k_values) if self.top_k_values else 20

    def validate(self) -> list[str]:
        """Return a list of validation errors (empty if valid)."""
        errors: list[str] = []
        if self.k1 <= 0:
            errors.append("k1 must be > 0")
        if not (0 <= self.b <= 1):
            errors.append("b must be in [0, 1]")
        if not self.top_k_values:
            errors.append("top_k_values must not be empty")
        for k in self.top_k_values:
            if k <= 0 or not isinstance(k, int):
                errors.append(f"top_k_values must be positive ints, got {k}")
        if self.relevance_threshold not in (1, 2, 3):
            errors.append("relevance_threshold must be 1, 2, or 3")
        if not self.field_weights:
            errors.append("field_weights must not be empty")
        if all(w <= 0 for w in self.field_weights.values()):
            errors.append("at least one field weight must be > 0")
        return errors

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> BM25Config:
        """Create a validated config from a dictionary.

        Unknown keys are ignored (forward-compatible).  Missing keys
        fall back to dataclass defaults.  Raises ``TypeError`` or
        ``ValueError`` for invalid values.
        """
        valid_keys = set(cls.__dataclass_fields__.keys())
        kwargs = {k: v for k, v in data.items() if k in valid_keys}
        cfg = cls(**kwargs)  # type: ignore[arg-type]
        errs = cfg.validate()
        if errs:
            raise ValueError("\n".join(errs))
        return cfg

    @classmethod
    def from_json(cls, path: str | Path) -> BM25Config:
        """Load config from a JSON file (convenience for offline scripts)."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)


# ---------------------------------------------------------------------------
# Internal document representation
# ---------------------------------------------------------------------------

@dataclass
class _Document:
    """Internal document representation for BM25 indexing."""

    item_id: str
    tokens: list[str]
    length: int


# ---------------------------------------------------------------------------
# BM25 Index
# ---------------------------------------------------------------------------

class BM25Index:
    """Okapi BM25 index with deterministic search.

    Build the index once from a collection of tokenised documents, then
    search repeatedly.  The index is **not** thread-safe during building;
    searches are read-only after build.

    Typical usage::

        docs = [
            ("item_001", tokenize(build_item_text(...))),
            ("item_002", tokenize(build_item_text(...))),
        ]
        index = BM25Index.build(docs, k1=1.5, b=0.75)
        results = index.search("laptop", top_k=10)
    """

    def __init__(self) -> None:
        self._docs: list[_Document] = []
        self._id_to_doc: dict[str, _Document] = {}
        self._inverted_index: dict[str, list[tuple[int, int]]] = defaultdict(list)
        # token -> [(doc_idx, term_freq_in_doc), ...]
        self._doc_freq: dict[str, int] = {}  # token -> number of docs containing it
        self._avgdl: float = 0.0
        self._k1: float = 1.5
        self._b: float = 0.75
        self._built: bool = False

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    @classmethod
    def build(
        cls,
        documents: Sequence[tuple[str, str | list[str]]],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> BM25Index:
        """Build an inverted index from *(item_id, text_or_tokens)* pairs.

        Each document is a ``(item_id, text_or_tokens)`` tuple.

        - If the second element is a ``str``, it is tokenized internally
          using ``tokenize()``.
        - If it is a ``list[str]``, it is used directly as pre-tokenized tokens.

        Args:
            documents: Sequence of ``(item_id, text_or_tokens)``.
            k1: Term frequency saturation parameter (> 0).
            b: Length normalisation parameter (0 ≤ b ≤ 1).

        Returns:
            A built ``BM25Index`` ready for search.

        Raises:
            ValueError: If ``k1`` or ``b`` are out of range.
            ValueError: If documents is empty.
        """
        if k1 <= 0:
            raise ValueError(f"k1 must be > 0, got {k1}")
        if not (0 <= b <= 1):
            raise ValueError(f"b must be in [0, 1], got {b}")

        # Pre-process documents
        processed: list[_Document] = []
        for item_id, raw in documents:
            toks = (
                tokenize(raw, remove_stopwords=True)
                if isinstance(raw, str)
                else list(raw)  # defensive copy
            )
            processed.append(_Document(item_id=item_id, tokens=toks, length=len(toks)))

        if not processed:
            raise ValueError("Cannot build BM25Index with empty documents")

        idx = cls()
        idx._k1 = k1
        idx._b = b
        idx._docs = processed
        idx._id_to_doc = {d.item_id: d for d in processed}

        total_len = 0
        for doc_idx, doc in enumerate(idx._docs):
            total_len += doc.length
            # Count term frequencies per document
            tf_map: dict[str, int] = {}
            for t in doc.tokens:
                tf_map[t] = tf_map.get(t, 0) + 1
            for token, tf in tf_map.items():
                idx._inverted_index[token].append((doc_idx, tf))

        idx._avgdl = total_len / len(idx._docs) if idx._docs else 1.0
        idx._doc_freq = {t: len(postings) for t, postings in idx._inverted_index.items()}
        idx._built = True

        return idx

    # ------------------------------------------------------------------
    # IDF
    # ------------------------------------------------------------------

    def idf(self, token: str) -> float:
        """Non-negative IDF: log(1 + (N - df + 0.5) / (df + 0.5))."""
        n = len(self._docs)
        df = self._doc_freq.get(token, 0)
        if df == 0:
            return 0.0
        return math.log(1.0 + (n - df + 0.5) / (df + 0.5))

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        """Execute a BM25 search.

        Args:
            query: Raw query string (will be tokenized internally).
            top_k: Maximum number of results to return. Must be >= 1.

        Returns:
            List of ``SearchResult`` sorted by score descending, then
            ``item_id`` ascending for ties.

        Raises:
            RuntimeError: If index has not been built.
            ValueError: If ``top_k < 1``.
        """
        if not self._built:
            raise RuntimeError("Index not built. Call BM25Index.build() first.")
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k}")

        query_tokens = tokenize(query, remove_stopwords=True)

        if not query_tokens:
            return []

        # Aggregate scores per document
        scores: dict[int, float] = {}  # doc_idx -> accumulated score

        for qt in query_tokens:
            idf_val = self.idf(qt)
            if idf_val == 0.0:
                continue  # unknown token — skip silently

            postings = self._inverted_index.get(qt, [])
            for doc_idx, tf in postings:
                doc = self._docs[doc_idx]
                doc_len = doc.length
                # BM25 term score
                numerator = tf * (self._k1 + 1.0)
                denominator = tf + self._k1 * (1.0 - self._b + self._b * doc_len / self._avgdl)
                term_score = idf_val * numerator / denominator
                scores[doc_idx] = scores.get(doc_idx, 0.0) + term_score

        # Build results sorted by (score descending, item_id ascending for ties)
        results: list[tuple[float, str]] = []
        for doc_idx, score in scores.items():
            doc = self._docs[doc_idx]
            results.append((score, doc.item_id))

        # Sort: score descending (-score ascending), item_id ascending
        results.sort(key=lambda x: (-x[0], x[1]))

        return [
            SearchResult(item_id=iid, score=s, rank=rank, source="bm25")
            for rank, (s, iid) in enumerate(results[:top_k], start=1)
        ]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def document_count(self) -> int:
        return len(self._docs)

    @property
    def avgdl(self) -> float:
        return self._avgdl

    @property
    def vocabulary_size(self) -> int:
        return len(self._doc_freq)

    @property
    def k1(self) -> float:
        return self._k1

    @property
    def b(self) -> float:
        return self._b
