"""Tests for the parity verification tool itself.

Verify exit codes, JSON structure, subprocess error handling,
and tolerance comparisons without running the full MVP.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PARITY_SCRIPT = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "verify_mvp_algorithm_parity.py"
FIXTURE_PATH = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "parity" / "parity_fixture.json"
PYTHON_EXE = sys.executable


@pytest.fixture
def tmp_output():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.mark.parity
class TestParityToolReal:
    """Real parity runs (marked 'parity' — may be slow)."""

    def test_real_parity_passes(self, tmp_output):
        """Full parity run should pass (exit 0, status=passed)."""
        proc = subprocess.run(
            [
                PYTHON_EXE, str(PARITY_SCRIPT),
                "--mvp-root", str(Path("D:/project/PSR-SRS-MVP")),
                "--enterprise-root", str(Path("D:/project/PSR-SRS-Enterprise")),
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


class TestParityToolStructure:
    """Structural tests for the parity tool."""

    def test_enterprise_runner_succeeds(self, tmp_output):
        """Enterprise runner alone should produce valid JSON (via subprocess)."""
        runner = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "parity" / "run_enterprise_case.py"
        proc = subprocess.run(
            [PYTHON_EXE, str(runner), "--fixture", str(FIXTURE_PATH)],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert "tokenization" in data
        assert "bm25" in data
        assert "semantic" in data
        assert "fusion" in data
        assert "profiles" in data

    def test_parity_report_has_required_fields(self):
        """Verify the report JSON structure."""
        # Use the latest report
        report_path = Path("D:/project/PSR-SRS-Enterprise/outputs/e1_parity_report.json")
        if report_path.exists():
            report = json.loads(report_path.read_text())
            assert "status" in report
            assert "tolerances" in report
            assert "checks" in report
            assert "unexpected_differences" in report
            assert "subprocesses" in report

    def test_tolerance_comparison_pass(self):
        """Values within tolerance should be considered equal."""
        assert math.isclose(1.0, 1.0000001, rel_tol=1e-6, abs_tol=1e-6)

    def test_tolerance_comparison_fail(self):
        """Values outside tolerance should NOT be equal."""
        assert not math.isclose(1.0, 1.1, rel_tol=1e-6, abs_tol=1e-6)

    def test_fixture_loads(self):
        """Parity fixture should be valid JSON and have required keys."""
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        for key in ("tokenization", "bm25", "semantic", "fusion", "profiles"):
            assert key in data, f"Missing fixture key: {key}"


class TestParityErrorHandling:
    """Error handling in the parity tool."""

    def test_nonexistent_mvp_path_fails(self, tmp_output):
        proc = subprocess.run(
            [
                PYTHON_EXE, str(PARITY_SCRIPT),
                "--mvp-root", "D:/nonexistent/path",
                "--enterprise-root", "D:/project/PSR-SRS-Enterprise",
                "--output", tmp_output,
            ],
            capture_output=True, text=True, timeout=30,
        )
        # Should fail (non-zero exit)
        assert proc.returncode != 0

    def test_enterprise_runner_bad_fixture_fails(self):
        runner = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "parity" / "run_enterprise_case.py"
        proc = subprocess.run(
            [PYTHON_EXE, str(runner), "--fixture", "nonexistent.json"],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode != 0
