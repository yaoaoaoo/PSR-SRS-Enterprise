"""Tests for dataset fingerprint computation."""

from __future__ import annotations

import pytest

from app.db.seed.fingerprint import compute_file_hashes, compute_fingerprint


@pytest.fixture
def mini_source(tmp_path):
    """Create minimal data files for fingerprint testing."""
    (tmp_path / "events.csv").write_text("event_id\n", encoding="utf-8")
    (tmp_path / "items.csv").write_text("item_id\n", encoding="utf-8")
    (tmp_path / "queries.csv").write_text("query_id\n", encoding="utf-8")
    (tmp_path / "qrels.csv").write_text("query_id,item_id\n", encoding="utf-8")
    (tmp_path / "users.csv").write_text("user_id\n", encoding="utf-8")
    return tmp_path


class TestFingerprint:
    def test_same_content_same_hash(self, mini_source):
        fp1 = compute_fingerprint(mini_source)
        fp2 = compute_fingerprint(mini_source)
        assert fp1 == fp2
        assert len(fp1) == 64

    def test_different_content_different_hash(self, mini_source):
        fp1 = compute_fingerprint(mini_source)
        (mini_source / "items.csv").write_text("item_id\nitem_001\n", encoding="utf-8")
        fp2 = compute_fingerprint(mini_source)
        assert fp1 != fp2

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            compute_fingerprint(tmp_path)

    def test_file_hashes(self, mini_source):
        hashes = compute_file_hashes(mini_source)
        assert len(hashes) == 5
        for fn in ("items.csv", "users.csv", "queries.csv", "events.csv", "qrels.csv"):
            assert fn in hashes
            assert len(hashes[fn]) == 64
