"""Portable test path resolution — works on Windows and Linux CI.

Derives paths from this file's location — no hardcoded drive letters.
"""

from __future__ import annotations

from pathlib import Path

# backend/tests/path_helpers.py -> backend/tests -> backend -> Enterprise root
_TESTS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TESTS_DIR.parent
ENTERPRISE_ROOT = _BACKEND_DIR.parent

SAMPLE_DIR = ENTERPRISE_ROOT / "data" / "sample"


def require_sample_dir() -> Path:
    """Return SAMPLE_DIR, raising if the five required CSVs are missing."""
    required = ("events.csv", "items.csv", "qrels.csv", "queries.csv", "users.csv")
    missing = [name for name in required if not (SAMPLE_DIR / name).is_file()]
    if missing:
        raise RuntimeError(
            f"Sample dataset incomplete at {SAMPLE_DIR}: {missing}"
        )
    return SAMPLE_DIR
