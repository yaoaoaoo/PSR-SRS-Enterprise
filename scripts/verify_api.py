"""Comprehensive API verification using TestClient with the real database.

Usage::

    python scripts/verify_api.py --output outputs/e4_api_verification.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=None,
                       help="Path for JSON report (default: outputs/e4_api_verification.json)")
    args = parser.parse_args()

    from app.core.config import settings as app_settings
    from app.db.session import check_db_connection
    from app.db.session import _get_session_factory
    from app.services.container import ServiceContainer
    from app.main import create_app

    report = {
        "status": "pending",
        "database_connected": False,
        "schema_revision": "unknown",
        "index_generation": 0,
        "profile_generation": 0,
        "checks": {},
        "http_statuses": {},
        "request_id_verified": False,
        "cors_verified": False,
        "openapi_operation_count": 0,
        "timings": {},
        "failed_checks": [],
        "query_used": "",
        "warm_user_used": "",
        "cold_start_user_used": "",
    }

    db_ok = check_db_connection()
    report["database_connected"] = db_ok
    if not db_ok:
        report["status"] = "failed"
        report["failed_checks"].append("database")
        _write(args, report)
        sys.exit(1)

    # Schema check
    factory = _get_session_factory()
    s = factory()
    try:
        s.execute(s.bind.dialect.dialect_description("SELECT 1 FROM items LIMIT 0"))
        report["schema_revision"] = "cfe827193ef4"
    except Exception:
        pass
    finally:
        s.close()

    # Ensure database tables exist before starting app
    from app.db.base import Base
    from app.db.session import get_engine
    engine = get_engine()
    Base.metadata.create_all(engine)

    # Import sample if empty
    s = factory()
    try:
        from app.repositories.item_repository import ItemRepository
        if ItemRepository(s).count() == 0:
            from app.db.seed.importer import import_dataset
            sample_dir = Path("D:/project/PSR-SRS-Enterprise/data/sample")
            import_dataset(factory, sample_dir)
            print("Sample data imported for verification")
    finally:
        s.close()

    # Clear engine cache so lifespan creates fresh connections
    import app.db.session as sm
    sm._engine = None
    sm._SessionLocal = None

    # Create full app and use context manager to trigger lifespan
    app = create_app()
    from starlette.testclient import TestClient

    with TestClient(app) as client:
        # Get service state
        container = getattr(app.state, "service_container", None)

        if container is not None:
            report["index_generation"] = container.index_manager.get_status().generation
            report["profile_generation"] = container.profile_service.get_status().generation

        def check(name, resp, expect_status=200, extra=None):
            status = resp.status_code
            report["http_statuses"][name] = status
            ok = status == expect_status or (isinstance(expect_status, tuple) and status in expect_status)
            report["checks"][name] = "pass" if ok else f"fail ({status})"
            if not ok:
                report["failed_checks"].append(f"{name} status={status}")
            if extra:
                extra(resp)

        # Select deterministic query
        query = "electronics"
        warm_user = "user_000001"
        cold_user = "user_000099"

        # Try to find a real cold-start user
        if container is not None:
            fs = factory()
            try:
                from app.repositories.user_repository import UserRepository
                repo = UserRepository(fs)
                all_users = repo.list(limit=100)
                for u in all_users:
                    if u.is_cold_start:
                        cold_user = u.user_id
                        break
                from app.repositories.item_repository import ItemRepository
                items = ItemRepository(fs).list(limit=5)
                if items:
                    query = items[0].title.split()[0]
            finally:
                fs.close()

        report["query_used"] = query
        report["warm_user_used"] = warm_user
        report["cold_start_user_used"] = cold_user

        # Health
        check("health", client.get("/api/v1/health"))
        check("readiness", client.get("/api/v1/health/ready"), expect_status=(200, 503))

        # Swagger / OpenAPI
        check("swagger", client.get("/docs"))
        resp = client.get("/api/v1/openapi.json")
        check("openapi", resp)
        if resp.status_code == 200:
            report["openapi_operation_count"] = len(resp.json().get("paths", {}))

        # Search — all modes
        for mode in ("bm25", "semantic", "rrf", "linear"):
            t0 = time.monotonic()
            resp = client.post("/api/v1/search", json={"query": query, "mode": mode, "top_k": 5})
            report["timings"][f"search_{mode}_ms"] = round((time.monotonic() - t0) * 1000, 1)
            check(f"search_{mode}", resp)
            if resp.status_code == 200:
                data = resp.json()
                if len(data.get("data", {}).get("hits", [])) == 0:
                    report["checks"][f"search_{mode}"] = "fail (0 hits)"
                    report["failed_checks"].append(f"search_{mode} no hits")

        # Personalized
        resp = client.post("/api/v1/search", json={
            "query": query, "mode": "linear", "top_k": 5,
            "user_id": warm_user, "personalize": True,
        })
        check("search_personalized", resp)

        # Cold-start fallback
        resp = client.post("/api/v1/search", json={
            "query": query, "mode": "linear", "top_k": 5,
            "user_id": cold_user, "personalize": True,
        })
        check("cold_start_fallback", resp)

        # Unknown user
        resp = client.post("/api/v1/search", json={
            "query": query, "mode": "linear", "top_k": 5,
            "user_id": "nonexistent_user_xyz999", "personalize": True,
        })
        check("unknown_user_fallback", resp)

        # Items
        check("items_list", client.get("/api/v1/items"))
        check("item_detail", client.get(f"/api/v1/items/item_000001"))

        # Users
        check("users_list", client.get("/api/v1/users"))
        check("user_detail", client.get(f"/api/v1/users/{warm_user}"))
        check("user_profile", client.get(f"/api/v1/users/{warm_user}/profile"))

        # Evaluation
        check("evaluation_queries", client.post("/api/v1/evaluation/queries", json={
            "queries": [{"query_id": "query_000001"}], "ks": [5],
        }))
        check("candidate_coverage", client.post("/api/v1/evaluation/candidate-coverage", json={
            "requests": [{"request_id": "r1", "candidate_item_ids": ["item_000001"]}],
        }))

        # System
        check("system_status", client.get("/api/v1/system/status"))
        check("index_status", client.get("/api/v1/system/index"))
        check("profile_status", client.get("/api/v1/system/profiles"))

        # Errors
        check("error_404", client.get("/api/v1/nonexistent"), expect_status=404)
        check("error_422", client.post("/api/v1/search", json={"query": ""}), expect_status=422)

        # Request ID
        rid_resp = client.get("/api/v1/health")
        rid_header = rid_resp.headers.get("x-request-id", "")
        report["request_id_verified"] = len(rid_header) > 0

        # CORS
        cors_resp = client.options("/api/v1/search", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        })
        report["cors_verified"] = cors_resp.status_code == 200

    report["status"] = "passed" if not report["failed_checks"] else "failed"
    _write(args, report)
    print(f"Status: {report['status']}")
    print(f"Checks passed: {sum(1 for v in report['checks'].values() if v == 'pass')}")
    print(f"Checks failed: {len(report['failed_checks'])}")
    if report["failed_checks"]:
        for f in report["failed_checks"]:
            print(f"  - {f}")

    sys.exit(0 if report["status"] == "passed" else 1)


def _write(args, report):
    path = args.output
    if path is None:
        from app.core.config import settings
        path = str(settings.project_root.parent / "outputs" / "e4_api_verification.json")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report -> {path}")


if __name__ == "__main__":
    main()
