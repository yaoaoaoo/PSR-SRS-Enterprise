"""Tests for the parity verification tool itself.

Verify exit codes, JSON structure, subprocess error handling,
and tolerance comparisons.  Real MVP parity requires the
``PSR_SRS_MVP_ROOT`` environment variable pointing to a local
MVP checkout; without it the real parity test is skipped.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from tests.path_helpers import ENTERPRISE_ROOT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PARENT = Path(__file__).resolve().parent.parent.parent.parent
PARITY_SCRIPT = _PARENT / "scripts" / "verify_mvp_algorithm_parity.py"
FIXTURE_PATH = _PARENT / "scripts" / "parity" / "parity_fixture.json"
PYTHON_EXE = sys.executable


def _mvp_root() -> Path | None:
    raw = os.getenv("PSR_SRS_MVP_ROOT")
    if not raw:
        return None
    p = Path(raw).expanduser().resolve()
    return p if p.is_dir() else None


@pytest.fixture
def tmp_output():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Real parity — requires external MVP repo
# ---------------------------------------------------------------------------

@pytest.mark.parity
class TestParityToolReal:
    """Real parity runs (marked 'parity' — may be slow)."""

    def test_real_parity_passes(self, tmp_output):
        mvp_root = _mvp_root()
        if not mvp_root:
            pytest.skip(
                "PSR_SRS_MVP_ROOT env var not set or path does not exist; "
                "set it to your local MVP checkout to run real parity"
            )
        proc = subprocess.run(
            [
                PYTHON_EXE, str(PARITY_SCRIPT),
                "--mvp-root", str(mvp_root),
                "--enterprise-root", str(ENTERPRISE_ROOT),
                "--output", tmp_output,
            ],
            capture_output=True, text=True, timeout=120,
        )
        assert proc.returncode == 0, f"stderr: {proc.stderr[:500]}"
        report = json.loads(Path(tmp_output).read_text())
        assert report["status"] == "passed"
        assert report["unexpected_differences"] == []
        assert report["subprocesses"]["mvp_return_code"] == 0
        assert report["subprocesses"]["enterprise_return_code"] == 0


# ---------------------------------------------------------------------------
# Structure / unit tests (no external MVP needed)
# ---------------------------------------------------------------------------

class TestParityToolStructure:
    def test_enterprise_runner_succeeds(self, tmp_output):
        runner = _PARENT / "scripts" / "parity" / "run_enterprise_case.py"
        proc = subprocess.run(
            [PYTHON_EXE, str(runner), "--fixture", str(FIXTURE_PATH)],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        for k in ("tokenization", "bm25", "semantic", "fusion", "profiles"):
            assert k in data, f"Missing: {k}"

    def test_parity_report_has_required_fields(self):
        report_path = ENTERPRISE_ROOT / "outputs" / "e1_parity_report.json"
        if report_path.exists():
            report = json.loads(report_path.read_text())
            for k in ("status", "tolerances", "checks", "unexpected_differences", "subprocesses"):
                assert k in report, f"Missing: {k}"

    def test_tolerance_comparison_pass(self):
        assert math.isclose(1.0, 1.0000001, rel_tol=1e-6, abs_tol=1e-6)

    def test_tolerance_comparison_fail(self):
        assert not math.isclose(1.0, 1.1, rel_tol=1e-6, abs_tol=1e-6)

    def test_fixture_loads(self):
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        for key in ("tokenization", "bm25", "semantic", "fusion", "profiles"):
            assert key in data, f"Missing fixture key: {key}"


class TestParityErrorHandling:
    def test_nonexistent_mvp_path_fails(self, tmp_output):
        proc = subprocess.run(
            [
                PYTHON_EXE, str(PARITY_SCRIPT),
                "--mvp-root", "D:/nonexistent/path",
                "--enterprise-root", str(ENTERPRISE_ROOT),
                "--output", tmp_output,
            ],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode != 0

    def test_enterprise_runner_bad_fixture_fails(self):
        runner = _PARENT / "scripts" / "parity" / "run_enterprise_case.py"
        proc = subprocess.run(
            [PYTHON_EXE, str(runner), "--fixture", "nonexistent.json"],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode != 0
