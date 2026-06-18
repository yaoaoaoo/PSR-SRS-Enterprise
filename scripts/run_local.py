"""Start backend and frontend for local development.

Usage::

    .venv\\Scripts\\python.exe scripts\\run_local.py
    .venv\\Scripts\\python.exe scripts\\run_local.py --backend-port 8001 --frontend-port 5174
"""

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
PYTHON = PROJECT / ".venv" / "Scripts" / "python.exe"
NPM = "npm.cmd" if sys.platform == "win32" else "npm"
PID_FILE = PROJECT / "outputs" / ".running_pids.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument("--skip-frontend", action="store_true")
    args = parser.parse_args()

    procs = {}

    # Start backend
    print(f"Starting backend on http://127.0.0.1:{args.backend_port}")
    be = subprocess.Popen(
        [str(PYTHON), "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(args.backend_port)],
        cwd=str(PROJECT / "backend"),
    )
    procs["backend"] = be.pid

    # Wait for health
    deadline = time.time() + 30
    health_ok = False
    while time.time() < deadline:
        try:
            import urllib.request
            r = urllib.request.urlopen(
                f"http://127.0.0.1:{args.backend_port}/api/v1/health", timeout=2
            )
            if r.status == 200:
                health_ok = True
                break
        except Exception:
            time.sleep(0.5)

    if not health_ok:
        print("ERROR: Backend failed to start within timeout")
        be.terminate()
        sys.exit(1)

    print(f"  Backend ready: http://127.0.0.1:{args.backend_port}")
    print(f"  Swagger:       http://127.0.0.1:{args.backend_port}/docs")

    # Start frontend
    if not args.skip_frontend:
        print(f"Starting frontend on http://127.0.0.1:{args.frontend_port}")
        fe = subprocess.Popen(
            [NPM, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(args.frontend_port)],
            cwd=str(PROJECT / "frontend"),
        )
        procs["frontend"] = fe.pid
        print(f"  Frontend ready: http://127.0.0.1:{args.frontend_port}")

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(json.dumps(procs))

    print("\nPress Ctrl+C to stop all services.")
    try:
        signal.pause()
    except (KeyboardInterrupt, AttributeError):
        pass
    finally:
        for name, pid in procs.items():
            try:
                import os
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
        PID_FILE.unlink(missing_ok=True)
        print("\nAll services stopped.")


if __name__ == "__main__":
    main()
