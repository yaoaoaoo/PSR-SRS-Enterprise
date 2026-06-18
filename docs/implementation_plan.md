# PSR-SRS Enterprise — Implementation Plan

> **Current**: Phase E0 complete (foundation)  
> **Next**: Phase E1 (core algorithm migration)

---

## Phase E0 — Foundation (COMPLETE)

**Objective**: Project skeleton, minimal backend, health checks, test infrastructure.

**Completed**:
- Virtual environment at `D:\project\PSR-SRS-Enterprise\.venv`
- FastAPI application with lifespan, CORS, exception handlers
- `/api/v1/health` and `/api/v1/health/ready` endpoints
- SQLite database connection with lazy engine creation
- Pydantic-settings configuration with `.env` support
- Structured logging
- 25 passing tests, 89% coverage, ruff clean
- MVP audit document (`docs/mvp_reuse_audit.md`)
- Architecture document (`docs/architecture.md`)

**Deliverables**: Running FastAPI app, passing test suite, clean lint.

---

## Phase E1 — Core Algorithm Migration

**Objective**: Migrate MVP retrieval, personalization, and evaluation algorithms into the Enterprise backend.

### Retrieval Migration

| Source (MVP) | Target (Enterprise) | Changes |
|-------------|---------------------|---------|
| `retrieval/tokenization.py` | `backend/app/retrieval/tokenization.py` | Import path only |
| `retrieval/bm25.py` | `backend/app/retrieval/bm25.py` | Add `BM25Config.from_dict()` |
| `retrieval/vectorization.py` | `backend/app/retrieval/vectorization.py` | Add `SemanticConfig.from_dict()` |
| `retrieval/semantic.py` | `backend/app/retrieval/semantic.py` | Import path only |
| `retrieval/fusion.py` | `backend/app/retrieval/fusion.py` | Add `FusionConfig.from_dict()` |

### Personalization Migration

| Source (MVP) | Target (Enterprise) | Changes |
|-------------|---------------------|---------|
| `personalization/split.py` | `backend/app/personalization/split.py` | Extract `load_events` as optional utility |
| `personalization/profiles.py` | `backend/app/personalization/profiles.py` | Replace CSV loaders with dict-based inputs |
| `personalization/reranker.py` | `backend/app/personalization/reranker.py` | Add `PersonalizationConfig.from_dict()` |
| `personalization/evaluation.py` | `backend/app/personalization/evaluation.py` | Import path only |

### Evaluation Migration

| Source (MVP) | Target (Enterprise) | Changes |
|-------------|---------------------|---------|
| `evaluation/metrics.py` | `backend/app/evaluation/metrics.py` | Generalize `SearchResult` type |

### Tests

- Adapt MVP tests (`test_bm25.py`, `test_semantic.py`, `test_fusion.py`, `test_personalization.py`)
- Change import paths from `psr_srs_mvp.xxx` to `app.xxx`
- Add `ml` extras: `pip install -e ".[dev,ml]"`

### Configs

- Already copied to `configs/` (bm25.json, semantic.json, fusion.json, personalization.json)

### Acceptance Criteria

- All 4 migrated test files pass (50+ tests)
- Can instantiate and query BM25Index, SemanticIndex
- Can run hybrid fusion end-to-end
- Can build user profiles and re-rank results
- Coverage ≥ 85%

### Excluded

- No API routes (Phase E4)
- No database persistence (Phase E2)
- No data generation migration (script-only in Phase E2)

---

## Phase E2 — Database Models & Data Import

**Objective**: Define SQLAlchemy ORM models and import sample data.

### Models

```python
# backend/app/models/
├── item.py          # Item: item_id, title, description, category, subcategory, brand, price
├── user.py          # User: user_id, is_cold_start
├── query.py         # Query: query_id, query_text
├── event.py         # Event: event_id, event_type, user_id, query_id, item_id, timestamp, ...
├── qrel.py          # Qrel: query_id, item_id, relevance_grade
└── user_profile.py  # UserProfile: user_id, category_weights(JSON), brand_weights(JSON), ...
```

### Data Import Scripts

- Adapt MVP `generate_data.py` → `scripts/seed_data.py`
- Import MVP sample CSVs into SQLite via SQLAlchemy
- Run Alembic migration to create schema

### Acceptance Criteria

- `alembic upgrade head` creates all tables
- `python scripts/seed_data.py` populates DB with sample data
- Repository methods can query items, users, events
- Tests verify CRUD operations

---

## Phase E3 — Search & Personalization Services

**Objective**: Service layer wrapping retrieval and personalization engines.

### Services

```
backend/app/services/
├── search_service.py          # Orchestrates BM25 → LSA → Fusion → Re-rank
├── index_service.py           # Build/manage BM25 and LSA indices
├── profile_service.py         # Build/update user profiles from events
└── evaluation_service.py      # Run offline evaluation on result sets
```

### Key Design Decisions

- BM25Index and SemanticIndex are singletons (built at startup, reloaded on index update)
- UserProfile cache (dict in memory, optionally Redis later)
- Thread-safe read access to indices

### Acceptance Criteria

- Search pipeline runs end-to-end from query string to ranked results
- Personalization re-ranking produces different orderings for different users
- Cold-start fallback returns baseline order
- Service tests with mock repositories

---

## Phase E4 — REST API

**Objective**: Expose search, item, user, and query endpoints.

### API Routes

```
POST   /api/v1/search          # Search with optional personalization
GET    /api/v1/items/{id}      # Item detail
GET    /api/v1/items           # Item listing with filters
GET    /api/v1/queries/{id}    # Query detail
POST   /api/v1/evaluate        # Offline evaluation run
```

### Schemas

- `SearchRequest` / `SearchResponse` (Pydantic v2)
- `ItemResponse`
- `EvaluationRequest` / `EvaluationReport`

### Acceptance Criteria

- All endpoints return correct JSON with proper HTTP status codes
- Request validation errors return structured 422 responses
- Swagger docs available at `/docs`
- API tests with TestClient cover all routes

---

## Phase E5 — React Frontend

**Objective**: Single-page app for search and results exploration.

### Pages

- Search page (query input, results with scores)
- Item detail page
- Simple dashboard (query stats)

### Tech Stack

- React 18 + TypeScript
- Vite
- React Router v6
- CSS Modules or plain CSS

### Acceptance Criteria

- Can type a query and see ranked results
- Results show relevance scores and personalization indicators
- Frontend dev server proxies API to backend

---

## Phase E6 — Behavior Feedback & Statistics

**Objective**: Record user behavior events and compute statistics.

### Features

- POST `/api/v1/events` — record click, favorite, cart, purchase
- GET `/api/v1/stats/overview` — aggregate statistics
- GET `/api/v1/stats/items/{id}` — per-item stats

### Acceptance Criteria

- Events are persisted to SQLite
- Statistics endpoint returns meaningful aggregates
- Event recording does not block search response

---

## Phase E7 — Testing, Scripts & Documentation

**Objective**: Polish — full test coverage, startup scripts, final docs.

### Tasks

- Integration tests covering end-to-end search flow
- Shell/batch scripts for one-command startup
- Update all documentation
- Freeze dependencies

---

## Phase E8 — Final Acceptance

**Objective**: Verify everything works from clean checkout.

### Acceptance Criteria

1. `git clone` + create `.venv` + install deps → all tests pass
2. `python scripts/seed_data.py` → sample data in DB
3. `python -m uvicorn app.main:app` → health + search endpoints work
4. Full search pipeline returns results within benchmark threshold
5. Frontend can search and display results
6. Documentation is complete and accurate
