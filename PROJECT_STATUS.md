# Project Status

```text
Project:   PSR-SRS Enterprise
Version:   1.0.0-rc.1
Status:    Feature Frozen / Release Candidate
Date:      2026-06-19
```

## Freeze Rules

1. No new business features will be added.
2. Only the following changes are accepted:
   - Critical bug fixes (`fix:`)
   - Security fixes (`security:`)
   - Documentation fixes (`docs:`)
   - Build/CI fixes (`build:`, `ci:`)
   - Reproducibility fixes
3. New features must go into a future version plan.
4. The current architecture boundary will not expand under "enterprise" pretext.
5. Redis, Kafka, real-time streaming are NOT part of this RC.
6. Any post-freeze modification MUST re-run the full regression suite.

## Current Baseline

```
Backend tests:  567 passed, 0 failed
Frontend tests:  50 passed, 0 failed
Ruff:            0 errors
TypeScript:      passed
ESLint:          passed
Frontend build:  passed
```

## Known Limitations

- SQLite for local demo
- In-memory profile snapshots rebuilt from DB events on restart
- Synchronous batch profile refresh
- No real-time event listener
- No historical profile versions
- Profile refresh API is for trusted local environments only
- No authentication system
- Time decay not enabled
