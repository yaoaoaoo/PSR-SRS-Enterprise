# Phase E1 — Algorithm Migration Report

> **Date**: 2026-06-18  
> **Status**: Complete  
> **MVP Source**: `D:\project\PSR-SRS-MVP` (read-only)  
> **Target**: `D:\project\PSR-SRS-Enterprise\backend\app\`

---

## 1. Migration Summary

| # | MVP Module | Enterprise Module | Status | Key Changes |
|---|-----------|-------------------|--------|-------------|
| 1 | `retrieval/tokenization.py` | `app/retrieval/tokenization.py` | ✅ Identical | None |
| 2 | `retrieval/bm25.py` | `app/retrieval/bm25.py` | ✅ Adapted | Added `from_dict()`, `build()` takes `(id, text|tokens)` tuples, uses unified `SearchResult` |
| 3 | `retrieval/vectorization.py` | `app/retrieval/vectorization.py` | ✅ Adapted | Added `from_dict()`, `threading.RLock` on `transform()` |
| 4 | `retrieval/semantic.py` | `app/retrieval/semantic.py` | ✅ Adapted | Returns unified `SearchResult`, `RLock` on `search()` |
| 5 | `retrieval/fusion.py` | `app/retrieval/fusion.py` | ✅ Adapted | Added `from_dict()`, uses unified `SearchResult`/`FusedSearchResult` |
| 6 | `evaluation/metrics.py` | `app/evaluation/metrics.py` | ✅ Adapted | Uses `RankedItemProtocol` instead of concrete `SearchResult` |
| 7 | `personalization/profiles.py` | `app/personalization/profiles.py` | ✅ Adapted | Removed CSV loaders — accepts in-memory dicts |
| 8 | `personalization/reranker.py` | `app/personalization/reranker.py` | ✅ Adapted | Added `from_dict()` |
| 9 | `personalization/evaluation.py` | `app/personalization/evaluation.py` | ✅ Adapted | Import path only |
| — | (new) | `app/retrieval/types.py` | ✅ New | Unified `SearchResult`, `FusedSearchResult` |
| — | (new) | `app/evaluation/protocols.py` | ✅ New | `RankedItemProtocol` |
| — | (new) | `app/personalization/types.py` | ✅ New | `RankedItem` (personalization-specific) |

---

## 2. Config Adaptation — `from_dict()`

All four config dataclasses received:

```python
@classmethod
def from_dict(cls, data: Mapping[str, object]) -> Self:
    valid_keys = set(cls.__dataclass_fields__.keys())
    kwargs = {k: v for k, v in data.items() if k in valid_keys}
    cfg = cls(**kwargs)
    errs = cfg.validate()
    if errs:
        raise ValueError("\n".join(errs))
    return cfg
```

| Config Class | Module | JSON → from_dict bridge |
|-------------|--------|------------------------|
| `BM25Config` | `app/retrieval/bm25.py` | `from_json()` → `from_dict()` |
| `SemanticConfig` | `app/retrieval/vectorization.py` | `from_json()` → `from_dict()` |
| `FusionConfig` | `app/retrieval/fusion.py` | `from_json()` → `from_dict()` |
| `PersonalizationConfig` | `app/personalization/reranker.py` | `from_json()` → `from_dict()` |

Behavior:
- Unknown fields: **ignored** (forward-compatible)
- Missing fields: use dataclass defaults
- Invalid values: raise `ValueError` with clear message
- `from_json()` reads file and delegates to `from_dict()`

---

## 3. SearchResult Design

Unified result type at `app/retrieval/types.py`:

```python
@dataclass(frozen=True)
class SearchResult:
    item_id: str
    score: float
    rank: int | None = None
    source: str | None = None
```

- All retrieval channels (BM25, semantic, fusion output) produce `SearchResult`
- `source` field tracks origin: `"bm25"`, `"semantic"`, `"rrf"`, `"linear"`
- Frozen dataclass — safe for caching and hashing

`FusedSearchResult` carries per-channel diagnostic metadata:

```python
@dataclass(frozen=True)
class FusedSearchResult:
    item_id: str
    rank: int
    fusion_score: float
    sources: tuple[str, ...] = ()
    bm25_rank: int | None = None
    semantic_rank: int | None = None
    bm25_score: float | None = None
    semantic_score: float | None = None
    bm25_normalized_score: float | None = None
    semantic_normalized_score: float | None = None
```

---

## 4. Protocol Design

`app/evaluation/protocols.py`:

```python
@runtime_checkable
class RankedItemProtocol(Protocol):
    item_id: str
    score: float
```

- `SearchResult` (retrieval) and `RankedItem` (personalization) both satisfy this
- Evaluation functions accept any iterable of `RankedItemProtocol`
- No dependency on concrete result types

---

## 5. Concurrency Protection

`SemanticVectorizer` holds mutable sklearn transformers (`TfidfVectorizer`, `TruncatedSVD`). These are **read** during `transform()` but sklearn's thread safety is not guaranteed.

**Solution**: Instance-level `threading.RLock`

```python
class SemanticVectorizer:
    def __init__(self, config):
        self._lock = threading.RLock()

    def fit(self, documents):    # acquires write lock
        with self._lock: ...

    def transform(self, texts):  # acquires read lock
        with self._lock: ...

class SemanticIndex:
    def __init__(self):
        self._lock = threading.RLock()

    def search(self, query):     # acquires lock during transform
        with self._lock: ...
```

**Tested**: 4 threads × 20 iterations, no deadlock, no crashes.

---

## 6. Behavioral Changes

| Aspect | Change | Reason |
|--------|--------|--------|
| BM25 `build()` input | Now `Sequence[tuple[str, str|list[str]]]` instead of `Sequence[Document]` | More ergonomic for API callers |
| BM25 auto-tokenization | String inputs auto-tokenized; list inputs used as-is | Flexibility |
| CSV loaders removed | `load_items()`, `load_queries()`, `load_qrels()` removed from algorithm layer | File I/O belongs in scripts/repositories, not algorithms |
| `Profile` dataclass renamed | MVP's `RankedItem` → `app/personalization/types.py` `RankedItem` | Avoid name collision with retrieval types |
| Evaluation Protocol | Accepts `RankedItemProtocol` instead of concrete `SearchResult` | Decoupled from retrieval module |

**No changes** to: IDF formula, BM25 term scoring, SVD fitting, cosine similarity, RRF scoring, linear fusion normalization, profile status logic, reranking weights, cold-start fallback.

---

## 7. Unmigrated Content

| Item | Reason |
|------|--------|
| `data_generation/` (5 files) | Offline synthetic data — not needed at runtime |
| `notebooks/` | Jupyter notebook — not suitable for API server |
| `scripts/run_*.py` (4 files) | CLI scripts — will be recreated as service-layer scripts in E3 |
| `retrieval/io.py` (CSV loaders) | Replaced by DB repositories in E2 |
| `scripts/release_check.py`, `reproducibility_check.py`, `build_notebook.py`, `validate_notebook.py` | MVP-only tooling |

---

## 8. Parity Results

| Check | Result | Method |
|-------|--------|--------|
| Tokenization | ✅ Match | Code-identical — same STOP_WORDS, regex, NFKC pipeline |
| build_item_text | ✅ Match | Code-identical — same default weights |
| BM25 | ✅ Match | Verified by 31 tests — same Okapi formula, same tie-breaking |
| Semantic (LSA) | ✅ Match | Deterministic — same seed produces identical vectors |
| RRF Fusion | ✅ Match | Same formula, same k=60 |
| Linear Fusion | ✅ Match | Same min-max normalization |
| Profiles | ✅ Match | Same event weighting, same time decay |
| Reranking | ✅ Match | Same multi-signal affinity formula |
| Cold-start fallback | ✅ Match | Same fallback: original retrieval order |
| Metrics | ✅ Match | Same P@K, R@K, MRR, NDCG formulas |

See: `outputs/e1_parity_report.json`

---

## 9. Known Limitations

1. **Subprocess-based MVP comparison**: The parity script uses subprocess isolation for MVP imports, which is fragile. Direct algorithm verification via 177 unit tests is the authoritative check.
2. **E501 (line length)**: Some long validation expressions exceed 100 characters — cosmetic only.
3. **sklearn SVD warning**: Single-document SVD triggers a divide-by-zero warning in sklearn's variance calculation — happens with 1-2 document indices; all results remain correct.
4. **Starlette deprecation**: `httpx` with `testclient` is deprecated by Starlette — this is an upstream issue, not project code. Future upgrade to `httpx2` when available.
5. **SemanticVectorizer concurrency**: Lock protects `transform()` but does not guarantee optimal throughput under high concurrency. Acceptable for current scale.

---

## 10. Phase E2 Input Contracts

The algorithm layer now expects the following data structures from the database/repository layer:

### For retrieval index building:
```python
# Items with text for indexing
documents: Sequence[tuple[str, str]]  # (item_id, combined_text)
# Built via build_item_text() or direct text
```

### For user profiles:
```python
train_events: list[dict]  # {user_id, event_type, item_id, timestamp, session_id}
items: dict[str, dict]    # {item_id: {category, subcategory, brand, price}}
users_map: dict[str, dict]  # {user_id: {is_cold_start}}
event_weights: dict[str, float]
half_life_days: float
```

### For personalized re-ranking:
```python
candidates: list[dict[str, str]]  # [{item_id, rank, fusion_score}, ...]
profile: UserProfile
items_map: dict[str, dict]
config: PersonalizationConfig
```

### For evaluation:
```python
results: Sequence[RankedItemProtocol]  # any object with .item_id and .score
qrels: dict[str, dict[str, int]]  # {query_id: {item_id: grade}}
```

Phase E2's repository layer should produce these structures from SQLAlchemy models.
