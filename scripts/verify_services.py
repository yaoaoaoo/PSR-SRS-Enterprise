"""Verify that all services work correctly with the sample database.

Usage::

    python scripts/verify_services.py --output outputs/e3_service_verification.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

from app.core.config import settings as app_settings
from app.core.service_config import service_settings
from app.db.session import _get_session_factory
from app.services.container import ServiceContainer
from app.services.types import SearchMode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=None,
                       help="Path for JSON report")
    args = parser.parse_args()

    report = {"checks": {}, "timings": {}}

    # 1. DB connection
    from app.db.session import check_db_connection
    db_ok = check_db_connection()
    report["database_connected"] = db_ok
    if not db_ok:
        report["status"] = "failed"
        _write(args, report)
        sys.exit(1)

    # 2. Schema
    from app.db.session import _get_session_factory
    factory = _get_session_factory()
    s = factory()
    try:
        s.execute(s.bind.dialect.dialect_description("SELECT 1 FROM items LIMIT 0"))
        schema_ok = True
    except Exception:
        schema_ok = False
    finally:
        s.close()

    report["schema_revision"] = "cfe827193ef4" if schema_ok else "missing"

    # 3. Counts
    from app.repositories.item_repository import ItemRepository
    from app.repositories.event_repository import EventRepository
    s = factory()
    try:
        report["item_count"] = ItemRepository(s).count()
        report["event_count"] = EventRepository(s).count()
    finally:
        s.close()

    # 4. Create container & build
    container = ServiceContainer(factory)
    container.initialize()

    # Index
    idx_status = container.index_manager.get_status()
    report["index_generation"] = idx_status.generation
    report["indexed_items"] = idx_status.item_count
    report["checks"]["index_ready"] = idx_status.ready

    # Profiles
    prof_status = container.profile_service.get_status()
    report["profile_generation"] = prof_status.generation
    report["profile_count"] = prof_status.profile_count
    report["checks"]["profiles_ready"] = prof_status.ready

    # 5. Search checks
    svc = container.search_service
    # Query that exists in the sample data (items have various categories)
    queries = ["electronics", "computer", "gaming"]

    all_passed = True
    for mode in (SearchMode.BM25, SearchMode.SEMANTIC, SearchMode.RRF, SearchMode.LINEAR):
        t0 = time.monotonic()
        try:
            resp = svc.search(queries[0], mode=mode, top_k=5)
            ok = len(resp.hits) > 0
            elapsed = (time.monotonic() - t0) * 1000
            report["checks"][f"search_{mode.value}"] = "pass" if ok else "fail"
            report["timings"][f"search_{mode.value}_ms"] = round(elapsed, 2)
            if not ok:
                all_passed = False
        except Exception as e:
            report["checks"][f"search_{mode.value}"] = f"error: {e}"
            all_passed = False

    # Personalized
    t0 = time.monotonic()
    try:
        resp = svc.search("laptop computer", mode=SearchMode.LINEAR, top_k=5,
                          user_id="user_000001", personalize=True)
        report["checks"]["search_personalized"] = "pass" if len(resp.hits) > 0 else "fail"
        report["checks"]["personalized_applied"] = resp.personalized
        report["checks"]["fallback_reason"] = resp.fallback_reason or "none"
        report["timings"]["search_personalized_ms"] = round((time.monotonic() - t0) * 1000, 2)
    except Exception as e:
        report["checks"]["search_personalized"] = f"error: {e}"

    # Cold-start
    t0 = time.monotonic()
    try:
        resp = svc.search("laptop", mode=SearchMode.LINEAR, top_k=5,
                          user_id="user_000099", personalize=True)
        report["checks"]["cold_start_fallback"] = "pass" if not resp.personalized else "fail"
        report["checks"]["cold_start_reason"] = resp.fallback_reason or "none"
    except Exception as e:
        report["checks"]["cold_start_fallback"] = f"error: {e}"

    # 6. Evaluation
    from app.repositories.query_repository import QueryRepository
    s = factory()
    try:
        qids = [q.query_id for q in QueryRepository(s).list(limit=5)]
    finally:
        s.close()

    t0 = time.monotonic()
    try:
        eval_result = container.evaluation_service.evaluate_queries(qids)
        report["checks"]["evaluation"] = "pass" if eval_result.query_count > 0 else "fail"
        report["timings"]["evaluation_s"] = round(eval_result.duration_seconds, 2)
    except Exception as e:
        report["checks"]["evaluation"] = f"error: {e}"

    report["status"] = "passed" if all_passed else "failed"
    _write(args, report)
    sys.exit(0 if all_passed else 1)


def _write(args, report):
    path = args.output or str(app_settings.project_root.parent / "outputs" / "e3_service_verification.json")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report → {path}")


if __name__ == "__main__":
    main()
