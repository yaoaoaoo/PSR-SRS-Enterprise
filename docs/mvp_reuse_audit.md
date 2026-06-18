# MVP Reuse Audit

> **Source**: `D:\project\PSR-SRS-MVP` (read-only)  
> **Target**: `D:\project\PSR-SRS-Enterprise`  
> **Date**: 2026-06-18  
> **Status**: Complete

---

## 1. MVP Project Overview

| Attribute | Value |
|-----------|-------|
| Version | 0.1.0 |
| Python | 3.12+ |
| License | MIT |
| Tests | 255 passed |
| Core dep | scikit-learn==1.9.0 |
| Package | `psr_srs_mvp` (src layout) |
| Data | 500 items, 100 users, 200 queries, 6,376 events, 10,076 qrels |
| Seeds | Fixed: 20260614 — fully reproducible |

### Module Map

```
src/psr_srs_mvp/
├── __init__.py                    # Version: 0.1.0
├── data_generation/               # Synthetic data (not needed in API runtime)
│   ├── config.py
│   ├── generator.py
│   ├── schemas.py
│   ├── validation.py
│   └── writers.py
├── evaluation/                    # Shared IR metrics
│   └── metrics.py                 # evaluate_query, evaluate_all, macro_average
├── personalization/               # User profiles + re-ranking
│   ├── split.py                   # Time-based train/test split
│   ├── profiles.py                # UserProfile, build_profiles
│   ├── reranker.py                # PersonalizationConfig, rerank_candidates
│   └── evaluation.py              # Behavior/qrels evaluation + coverage
└── retrieval/                     # Core retrieval engine
    ├── tokenization.py            # tokenize, build_item_text, STOP_WORDS
    ├── bm25.py                    # BM25Index, BM25Config, SearchResult
    ├── vectorization.py           # SemanticVectorizer, SemanticConfig
    ├── semantic.py                # SemanticIndex, SemanticSearchResult
    ├── fusion.py                  # FusionConfig, fuse_rrf, fuse_linear
    └── io.py                      # CSV loaders (load_items, load_queries, load_qrels)
```

---

## 2. Modules: Direct Migration Candidates

These modules contain **pure algorithm logic** with no file-system or Notebook coupling. They can be copied into the Enterprise backend with minimal changes.

### 2.1 `retrieval/tokenization.py`

| Aspect | Detail |
|--------|--------|
| **Public API** | `tokenize(text, remove_stopwords) → list[str]`<br>`build_item_text(title, description, category, subcategory, brand, weights) → str` |
| **Dependencies** | Python stdlib only (`re`, `unicodedata`) |
| **Risk** | None — zero external deps |
| **Action** | **Direct migration** to `backend/app/retrieval/tokenization.py` |

### 2.2 `retrieval/bm25.py`

| Aspect | Detail |
|--------|--------|
| **Public API** | `BM25Config` — dataclass with `from_json(path)`<br>`BM25Index.build(documents, k1, b) → BM25Index`<br>`BM25Index.search(query, top_k) → list[SearchResult]`<br>`SearchResult` — frozen dataclass (score, item_id, rank) |
| **Dependencies** | Python stdlib + `retrieval/tokenization.py` |
| **Risk** | `BM25Config.from_json()` reads from file path — needs a `from_dict()` factory for API use |
| **Action** | **Direct migration** — add `from_dict()` class method for API config injection |

### 2.3 `retrieval/vectorization.py`

| Aspect | Detail |
|--------|--------|
| **Public API** | `SemanticConfig` — dataclass with `from_json(path)`<br>`SemanticVectorizer(config)` — TF-IDF + TruncatedSVD pipeline<br>`fit(documents) → self`<br>`transform(texts) → np.ndarray` |
| **Dependencies** | `scikit-learn`, `numpy`, `scipy` |
| **Risk** | Stateful — `_fitted` flag guards against transform-before-fit. Thread-safe for reads after fit. Needs `from_dict()` factory. |
| **Action** | **Direct migration** — add `from_dict()` to config |

### 2.4 `retrieval/semantic.py`

| Aspect | Detail |
|--------|--------|
| **Public API** | `SemanticIndex.build(documents, item_ids, config) → SemanticIndex`<br>`SemanticIndex.search(query, top_k) → list[SemanticSearchResult]` |
| **Dependencies** | `retrieval/vectorization.py`, `numpy` |
| **Risk** | `_item_vectors` is a numpy array in memory — suitable for 500-10k items; may need batching for larger scale |
| **Action** | **Direct migration** — fine for current scale |

### 2.5 `retrieval/fusion.py`

| Aspect | Detail |
|--------|--------|
| **Public API** | `FusionConfig` — dataclass with `from_json(path)`<br>`build_candidates(bm25_results, semantic_results) → dict`<br>`fuse_rrf(candidates, rrf_k, top_k) → list[FusedSearchResult]`<br>`fuse_linear(candidates, bm25_weight, semantic_weight, top_k) → list[FusedSearchResult]`<br>`compute_diagnostics(...) → dict` |
| **Dependencies** | `retrieval/bm25.py` (SearchResult type), `retrieval/semantic.py` (SemanticSearchResult type) |
| **Risk** | `from_json()` needs `from_dict()` alternative. `SearchResult` type coupling to BM25 module — acceptable for now. |
| **Action** | **Direct migration** — add `from_dict()` to config |

### 2.6 `personalization/profiles.py`

| Aspect | Detail |
|--------|--------|
| **Public API** | `UserProfile` — user behavior profile with category/brand/price affinities<br>`build_profiles(train_events, items, users_map, event_weights, half_life_days) → dict[str, UserProfile]`<br>`load_items(path)`, `load_users_map(path)` — CSV loaders |
| **Dependencies** | Python stdlib (`csv`, `math`, `collections`, `datetime`) |
| **Risk** | `load_items` and `load_users_map` read from CSV paths — will be replaced by DB repository calls in Enterprise. The `build_profiles` logic itself is path-independent. |
| **Action** | **Adaptation needed** — extract `build_profiles` core logic; replace CSV loaders with DB-backed repository |

### 2.7 `personalization/reranker.py`

| Aspect | Detail |
|--------|--------|
| **Public API** | `PersonalizationConfig` — weights and thresholds<br>`rerank_candidates(candidates, profile, items_map, config, ...) → list[RankedItem]` |
| **Dependencies** | `personalization/profiles.py` (UserProfile type) |
| **Risk** | `from_json()` needs `from_dict()`. `items_map` is a plain dict — in Enterprise this will come from DB. |
| **Action** | **Direct migration** — add `from_dict()` to config |

### 2.8 `personalization/split.py`

| Aspect | Detail |
|--------|--------|
| **Public API** | `split_events(events, train_ratio) → (train, test, split_info)`<br>`load_events(path) → list[dict]` |
| **Dependencies** | Python stdlib (`csv`, `datetime`) |
| **Risk** | `load_events` reads CSV from path — replace with DB query. Core split logic is reusable. |
| **Action** | **Adaptation needed** — extract `split_events` logic; replace CSV loader |

### 2.9 `personalization/evaluation.py`

| Aspect | Detail |
|--------|--------|
| **Public API** | `compute_behavior_metrics(results, behavior_grades, positive_items, ks) → dict`<br>`compute_qrels_metrics(results, qrels, ks, relevance_threshold) → dict`<br>`macro_average_dict(metrics_list, keys) → dict`<br>`compute_candidate_coverage(...) → dict` |
| **Dependencies** | Python stdlib (`math`), `personalization/reranker.py` (RankedItem type) |
| **Risk** | None — pure computation |
| **Action** | **Direct migration** |

### 2.10 `evaluation/metrics.py`

| Aspect | Detail |
|--------|--------|
| **Public API** | `MetricResult` — per-query metric values<br>`evaluate_query(results, query_id, query_text, qrels, ks, threshold) → MetricResult`<br>`evaluate_all(all_results, queries, qrels, ks) → list[MetricResult]`<br>`macro_average(metrics) → dict` |
| **Dependencies** | Python stdlib (`math`), `retrieval/bm25.py` (SearchResult type) |
| **Risk** | Uses `SearchResult` type — should be generalized to accept any result with `.item_id` attribute |
| **Action** | **Adaptation needed** — make `evaluate_query` accept a Protocol/ABC instead of concrete `SearchResult` |

---

## 3. Modules: Requires Adaptation

### 3.1 `retrieval/io.py`

| Aspect | Detail |
|--------|--------|
| **Issue** | All functions read CSV from file paths (`load_items`, `load_queries`, `load_qrels`) |
| **Adaptation** | Create equivalent functions that accept `list[dict]` or DB cursor results instead of file paths. Keep CSV loaders as utility scripts only. |
| **Priority** | Phase E2 (when DB models are ready) |

### 3.2 Config `from_json()` pattern

| Aspect | Detail |
|--------|--------|
| **Issue** | All four config dataclasses (`BM25Config`, `SemanticConfig`, `FusionConfig`, `PersonalizationConfig`) use `from_json(path)` which reads from filesystem |
| **Adaptation** | Add `from_dict(d: dict) -> Self` classmethod alongside each `from_json()`. The API layer will inject config from DB or request body, not files. |
| **Priority** | Phase E1 |

### 3.3 `data_generation/` module

| Aspect | Detail |
|--------|--------|
| **Issue** | Full synthetic data generation pipeline — useful for offline data prep, not for API runtime |
| **Adaptation** | Keep as a script under `scripts/` rather than inside the `app/` package. Use it to seed sample data into SQLite during Phase E2. |
| **Priority** | Phase E2 (data import scripts) |

---

## 4. Modules: NOT to Migrate

| Module / File | Reason |
|---------------|--------|
| `data_generation/schemas.py` | Only needed for synthetic data generation — not used at runtime |
| `data_generation/writers.py` | CSV file writer — superseded by SQLAlchemy ORM |
| `data_generation/validation.py` | Offline validation — keep as optional script |
| `notebooks/01_mvp_end_to_end.ipynb` | Jupyter-only demo — not suitable for API server |
| `scripts/build_notebook.py` | Notebook build tooling |
| `scripts/validate_notebook.py` | Notebook validation tooling |
| `scripts/release_check.py` | MVP release validation only |
| `scripts/reproducibility_check.py` | Specific to frozen MVP baseline |
| `outputs/` (all) | Frozen baseline outputs — not reusable |
| `data/sample/` (all CSVs) | Format is reference-worthy; actual data will be regenerated via DB seed scripts |
| `.venv/` (MVP) | MVP's own virtual environment — never copy |
| `dist/` | MVP distribution build artifacts |

---

## 5. Configuration Reuse

| MVP Config | Enterprise Reuse |
|------------|-----------------|
| `configs/bm25.json` | ✅ Copy to `configs/bm25.json` — identical parameters |
| `configs/semantic.json` | ✅ Copy to `configs/semantic.json` — identical parameters |
| `configs/fusion.json` | ✅ Copy to `configs/fusion.json` — identical parameters |
| `configs/personalization.json` | ✅ Copy to `configs/personalization.json` — identical parameters |
| `configs/sample.json` | ✅ Copy to `configs/sample.json` — data gen seed config |
| `pyproject.toml` (deps) | 🔄 Reference — `scikit-learn` needed for LSA retrieval |

---

## 6. Test Migration

| MVP Test | Status |
|----------|--------|
| `tests/test_bm25.py` | ✅ Can adapt for Enterprise (import path change only) |
| `tests/test_semantic.py` | ✅ Can adapt — LSA with scikit-learn |
| `tests/test_fusion.py` | ✅ Can adapt — pure logic, no I/O |
| `tests/test_personalization.py` | ✅ Can adapt — profile/re-rank logic |
| `tests/test_data_generation.py` | ❌ Not for Enterprise API runtime (keep as optional script test) |

Adaptation needed: change import paths from `psr_srs_mvp.xxx` to `app.xxx`.

---

## 7. Path and Data Coupling Risks

### 7.1 Absolute Path Risk

| Finding | Severity |
|---------|----------|
| No hard-coded absolute paths found in source code | ✅ None |
| Config `from_json(path)` accepts `str | Path` — caller controls the path | ✅ Fine |
| CSV loaders accept `str | Path` — caller controls the path | ✅ Fine |

### 7.2 CSV File Coupling

| Finding | Severity |
|---------|----------|
| All retrieval scripts read CSV from CLI args — not hard-coded | ✅ Fine |
| `io.py` functions are pure CSV readers — easily replaceable with DB queries | ⚠️ Low |
| `personalization/profiles.py` has `load_items` and `load_users_map` CSV loaders | ⚠️ Low |

### 7.3 Global State

| Finding | Severity |
|---------|----------|
| `BM25Index` is stateful (inverted index in memory) — not a singleton | ✅ Fine per-request |
| `SemanticVectorizer` is stateful (fitted TF-IDF + SVD) — intended as singleton after build | ⚠️ Medium |
| `SemanticIndex` holds `_item_vectors` numpy array — intended as singleton after build | ⚠️ Medium |
| `UserProfile` instances are per-user — no global mutation | ✅ Fine |

**Recommendation**: Wrap `BM25Index`, `SemanticVectorizer`, and `SemanticIndex` in a service-layer singleton that is built once at startup and reloaded on data updates.

### 7.4 Notebook-Specific Logic

| Finding | Severity |
|---------|----------|
| Notebook uses `PSR_SRS_RECOMPUTE` env var to control cache/compute mode | ❌ Not for API |
| Notebook cells have print-heavy output formatting | ❌ Not for API |
| No notebook logic is imported by or coupled into source modules | ✅ Fine |

---

## 8. Web API Concurrency Risks

| Risk | Detail | Mitigation |
|------|--------|------------|
| **BM25Index.search()** | Reads `_inverted_index` and `_docs` — pure read, no mutation | ✅ Thread-safe for concurrent reads |
| **SemanticIndex.search()** | Reads `_item_vectors` numpy array — pure read, no mutation | ✅ Thread-safe for concurrent reads |
| **SemanticVectorizer.transform()** | Uses scikit-learn transform — sklearn transformers are not guaranteed thread-safe | ⚠️ Use a lock or clone per thread |
| **rerank_candidates()** | Pure function — creates new list, no shared state | ✅ Thread-safe |
| **build_profiles()** | Creates new `UserProfile` dict — no shared state | ✅ Thread-safe per call |

**Recommendation**: Use `threading.Lock` or `asyncio.Lock` around `SemanticVectorizer.transform()` if concurrent search requests are expected. For MVP scale, single-worker uvicorn is sufficient.

---

## 9. Dependency Analysis

```
tokenization.py  ──► bm25.py
                   ──► (used by all retrieval)

numpy, scipy ──► vectorization.py ──► semantic.py

bm25.py ──► fusion.py ◄── semantic.py

evaluation/metrics.py ◄── SearchResult (bm25.py)

profiles.py ──► reranker.py
split.py    ──► (CLI scripts only)

evaluation.py (personalization) ◄── RankedItem (reranker.py)
```

No circular dependencies. Clean layered architecture.

---

## 10. Recommended Migration Order

| Phase | Modules | Rationale |
|-------|---------|-----------|
| **E1** | `retrieval/tokenization.py`<br>`retrieval/bm25.py`<br>`retrieval/vectorization.py`<br>`retrieval/semantic.py`<br>`retrieval/fusion.py` | Core retrieval — zero DB dependency, testable immediately |
| **E1** | `evaluation/metrics.py`<br>`personalization/evaluation.py` | Pure computation — needed for testing retrieval quality |
| **E1** | `personalization/profiles.py`<br>`personalization/reranker.py`<br>`personalization/split.py` | Personalization logic — needed for re-ranking |
| **E2** | DB models, data import, seed scripts | After algorithms are in place |
| **E3** | Service layer wrapping retrieval + personalization | Orchestration |
| **E4** | REST API routes | Expose services |

---

## 11. Summary

| Category | Count | Modules |
|----------|-------|---------|
| **Direct migration** | 7 | tokenization, bm25, vectorization, semantic, fusion, reranker, personalization/evaluation |
| **Minor adaptation** | 3 | io.py, config from_json→from_dict, evaluation/metrics (Protocol) |
| **Major adaptation** | 1 | profiles.py (CSV → DB) |
| **Not migrated** | 8+ | data_gen (5 files), notebooks (2), scripts (5), outputs, dist |
| **Configs reusable** | 5/5 | All JSON configs are reusable |
| **Tests reusable** | 4/5 | BM25, semantic, fusion, personalization (adaptable) |

**Overall assessment**: The MVP codebase is well-structured with clean separation of concerns. ~70% of the core algorithm code can be migrated with import path changes only. The primary adaptation work is replacing file-based CSV I/O with database-backed repositories, and adding dict-based config factories for API compatibility.
