"""Bootstrap script — sets up database, migrates, imports sample data.

Usage::

    .venv\\Scripts\\python.exe scripts\\bootstrap_local.py
    .venv\\Scripts\\python.exe scripts\\bootstrap_local.py --reset
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND = PROJECT_ROOT / "backend"
PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
OUTPUT = PROJECT_ROOT / "outputs" / "e8_bootstrap_report.json"


def run(cmd: list[str], cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd or BACKEND))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()

    report = {"status": "pending", "steps": {}}

    # 1. Check Python
    py_ver = run([str(PYTHON), "--version"])
    report["python_version"] = py_ver.stdout.strip()
    report["steps"]["python"] = "ok" if py_ver.returncode == 0 else "fail"

    # 2. Alembic upgrade
    if args.reset:
        run([str(PYTHON), "-m", "alembic", "downgrade", "base"])
    alembic = run([str(PYTHON), "-m", "alembic", "upgrade", "head"])
    report["steps"]["alembic"] = "ok" if alembic.returncode == 0 else f"fail: {alembic.stderr[:200]}"

    # 3. Import sample
    sample = PROJECT_ROOT / "data" / "sample"
    imp = run([
        str(PYTHON), str(PROJECT_ROOT / "scripts" / "import_sample_data.py"),
        "--source", str(sample),
        "--report", str(PROJECT_ROOT / "outputs" / "e2_import_report.json"),
    ])
    report["steps"]["sample_import"] = "ok" if imp.returncode == 0 else f"fail: {imp.stderr[:200]}"

    # Check counts
    from app.repositories.item_repository import ItemRepository
    from app.repositories.user_repository import UserRepository
    from app.repositories.event_repository import EventRepository
    from app.repositories.qrel_repository import QrelRepository
    from app.db.session import _get_session_factory

    s = _get_session_factory()()
    try:
        report["items"] = ItemRepository(s).count()
        report["users"] = UserRepository(s).count()
        report["events"] = EventRepository(s).count()
        report["qrels"] = QrelRepository(s).count()
    finally:
        s.close()

    all_ok = all(v == "ok" for v in report["steps"].values())
    report["status"] = "passed" if all_ok else "failed"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Bootstrap: {report['status']}")
    print(f"  items={report.get('items')} users={report.get('users')} events={report.get('events')}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
