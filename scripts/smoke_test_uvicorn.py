"""Real Uvicorn HTTP smoke test — starts, tests, stops.

Usage::

    python scripts/smoke_test_uvicorn.py --output outputs/e4_uvicorn_smoke_report.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

PYTHON = sys.executable
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
STARTUP_TIMEOUT = 30


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    host = DEFAULT_HOST
    port = args.port
    base = f"http://{host}:{port}"

    # Find an open port
    import socket
    for _ in range(10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((host, port)) != 0:
                break
            port += 1
        break

    base = f"http://{host}:{port}"

    report = {
        "status": "pending",
        "host": host,
        "port": port,
        "process_started": False,
        "health_status": 0,
        "readiness_status": 0,
        "swagger_status": 0,
        "openapi_status": 0,
        "search_status": 0,
        "search_result_count": 0,
        "items_status": 0,
        "system_status": 0,
        "request_id_verified": False,
        "process_stopped": False,
        "failed_checks": [],
    }

    # Start Uvicorn
    proc = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "app.main:app",
         "--host", host, "--port", str(port)],
        cwd=str(_BACKEND),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    report["process_started"] = True
    print(f"Uvicorn started on {base}")

    # Wait for health
    deadline = time.time() + STARTUP_TIMEOUT
    health_ok = False
    while time.time() < deadline:
        try:
            r = urllib_request.urlopen(f"{base}/api/v1/health", timeout=2)
            if r.status == 200:
                health_ok = True
                break
        except URLError:
            time.sleep(0.5)

    if not health_ok:
        report["failed_checks"].append("startup_timeout")
        proc.terminate()
        proc.wait(timeout=5)
        report["status"] = "failed"
        _write(args, report)
        sys.exit(1)

    def _ok(status, expect):
        if isinstance(expect, tuple):
            return status in expect
        return status == expect

    def http_get(path, key, expect=200):
        try:
            r = urllib_request.urlopen(f"{base}{path}", timeout=5)
            report[key] = r.status
            if not _ok(r.status, expect):
                report["failed_checks"].append(f"{key}={r.status}")
            return r
        except HTTPError as e:
            report[key] = e.code
            if not _ok(e.code, expect):
                report["failed_checks"].append(f"{key}={e.code}")
            return None
        except Exception as e:
            report[key] = 0
            report["failed_checks"].append(f"{key} error: {e}")
            return None

    def http_post(path, body_dict, key, expect=200):
        try:
            data = json.dumps(body_dict).encode("utf-8")
            req = urllib_request.Request(f"{base}{path}", data=data,
                                         headers={"Content-Type": "application/json"})
            r = urllib_request.urlopen(req, timeout=5)
            report[key] = r.status
            if not _ok(r.status, expect):
                report["failed_checks"].append(f"{key}={r.status}")
            return r
        except HTTPError as e:
            report[key] = e.code
            if not _ok(e.code, expect):
                report["failed_checks"].append(f"{key}={e.code}")
            return None
        except Exception as e:
            report[key] = 0
            report["failed_checks"].append(f"{key} error: {e}")
            return None

    # Verify endpoints
    http_get("/api/v1/health", "health_status")
    r = http_get("/api/v1/health/ready", "readiness_status", expect=(200, 503))
    # 503 is acceptable when schema/index not ready
    http_get("/docs", "swagger_status")
    http_get("/api/v1/openapi.json", "openapi_status")

    r = http_post("/api/v1/search",
                  {"query": "electronics", "mode": "linear", "top_k": 5},
                  "search_status")
    if r and r.status == 200:
        data = json.loads(r.read())
        hits = data.get("data", {}).get("hits", [])
        report["search_result_count"] = len(hits)
        if len(hits) == 0:
            report["failed_checks"].append("search_no_results")

    http_get("/api/v1/items?limit=1", "items_status")
    http_get("/api/v1/system/status", "system_status")

    # Request ID
    r = http_get("/api/v1/health", "health_status_rid")
    if r:
        rid = r.headers.get("X-Request-Id", "")
        report["request_id_verified"] = len(rid) > 0

    # Stop
    proc.terminate()
    try:
        proc.wait(timeout=10)
        report["process_stopped"] = True
        print("Uvicorn stopped successfully")
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        report["process_stopped"] = True

    report["status"] = "passed" if not report["failed_checks"] else "failed"
    _write(args, report)
    print(f"Status: {report['status']}")
    if report["failed_checks"]:
        print(f"Failed checks: {report['failed_checks']}")

    sys.exit(0 if report["status"] == "passed" else 1)


def _write(args, report):
    path = args.output
    if path is None:
        path = str(Path(__file__).resolve().parent.parent / "outputs" / "e4_uvicorn_smoke_report.json")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report -> {path}")


if __name__ == "__main__":
    main()
