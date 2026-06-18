# Release Checklist — v1.0.0-rc.1

| # | Check | Status |
|---|-------|--------|
| 1 | Version consistent across backend/frontend/OpenAPI | passed |
| 2 | LICENSE present | passed |
| 3 | README complete | passed |
| 4 | CHANGELOG updated | passed |
| 5 | .env.example has no secrets | passed |
| 6 | Alembic upgrade succeeds | passed |
| 7 | Fresh database migration works | passed |
| 8 | Sample import succeeds (500 items, 100 users, 6376 events) | passed |
| 9 | Sample import idempotent on repeat | passed |
| 10 | Backend tests >= 567 passed | passed |
| 11 | Frontend tests >= 50 passed | passed |
| 12 | Ruff 0 errors | passed |
| 13 | TypeScript passes | passed |
| 14 | ESLint passes | passed |
| 15 | Frontend production build succeeds | passed |
| 16 | OpenAPI JSON generated at /api/v1/openapi.json | passed |
| 17 | Profile status API returns real data | passed |
| 18 | Profile refresh API works | passed |
| 19 | Profile impact API works | passed |
| 20 | Profile deterministic rebuild verified | passed |
| 21 | BM25 search works | passed |
| 22 | Semantic search works | passed |
| 23 | RRF search works | passed |
| 24 | Linear search works | passed |
| 25 | Personalized search works | passed |
| 26 | Behavior event capture works (E6) | passed |
| 27 | Activity page shows events | passed |
| 28 | No absolute paths in runtime code | passed |
| 29 | No secrets in committed files | passed |
| 30 | No reference to old PSR-SRS directory | passed |
| 31 | MVP project unchanged | passed |
| 32 | Frontend build has no CDN dependencies | passed |
| 33 | pip check: no broken requirements | passed |
| 34 | npm dependency tree valid | passed |
