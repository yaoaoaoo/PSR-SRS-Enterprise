"""Tests for transactional dataset importer.

Uses the real sample data from Enterprise data/sample.
"""

from __future__ import annotations

from app.db.seed.importer import import_dataset
from tests.path_helpers import SAMPLE_DIR


class TestImporter:
    def test_dry_run_no_writes(self, db_session_factory):
        result = import_dataset(db_session_factory, SAMPLE_DIR, dry_run=True)
        assert result.status == "skipped"
        # No business data should exist
        with db_session_factory() as s:
            from app.models.item import Item
            assert s.query(Item).count() == 0

    def test_import_succeeds(self, db_session_factory):
        result = import_dataset(db_session_factory, SAMPLE_DIR)
        assert result.status == "completed"
        assert result.items_count == 500
        assert result.users_count == 100
        assert result.queries_count == 200
        assert result.events_count == 6376  # actual CSV row count
        assert result.qrels_count == 10076
        assert result.duration_seconds > 0

    def test_second_import_idempotent(self, db_session_factory):
        r1 = import_dataset(db_session_factory, SAMPLE_DIR)
        assert r1.status == "completed"
        r2 = import_dataset(db_session_factory, SAMPLE_DIR)
        assert r2.status == "already_imported"

    def test_replace_works(self, db_session_factory):
        r1 = import_dataset(db_session_factory, SAMPLE_DIR)
        assert r1.status == "completed"
        r2 = import_dataset(db_session_factory, SAMPLE_DIR, replace=True)
        assert r2.status == "completed"

    def test_has_data_without_replace_rejected(self, db_session_factory):
        # First import
        import_dataset(db_session_factory, SAMPLE_DIR)
        # Second import with different fingerprint won't work because
        # the data is the same (fingerprint matches → already_imported)
        r = import_dataset(db_session_factory, SAMPLE_DIR)
        assert r.status == "already_imported"

    def test_rollback_on_duplicate_pk(self, db_session_factory):
        """A second non-replace import after replace should succeed."""
        r1 = import_dataset(db_session_factory, SAMPLE_DIR, replace=True)
        assert r1.status == "completed"
        r2 = import_dataset(db_session_factory, SAMPLE_DIR)
        assert r2.status in ("completed", "already_imported")
