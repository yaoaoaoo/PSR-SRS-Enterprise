"""Integration test: full sample dataset import and verification."""

from __future__ import annotations

import pytest

from app.db.seed.importer import import_dataset
from tests.path_helpers import SAMPLE_DIR


@pytest.mark.integration
class TestSampleDatasetImport:
    def test_full_import_and_counts(self, db_session_factory):
        result = import_dataset(db_session_factory, SAMPLE_DIR)
        assert result.status == "completed"
        assert result.items_count == 500
        assert result.users_count == 100
        assert result.queries_count == 200
        assert result.events_count == 6376  # actual CSV row count
        assert result.qrels_count == 10076

    def test_event_type_distribution(self, db_session_factory):
        import_dataset(db_session_factory, SAMPLE_DIR, replace=True)
        with db_session_factory() as s:
            from app.repositories.event_repository import EventRepository
            repo = EventRepository(s)
            counts = repo.count_by_type()
            # Actual CSV distribution: 5752 impressions, 529 clicks, etc.
            assert counts["impression"] == 5752
            assert counts["click"] == 529
            assert counts["favorite"] == 47
            assert counts["add_to_cart"] == 40
            assert counts["purchase"] == 8
            total = sum(counts.values())
            assert total == 6376

    def test_idempotent_reimport(self, db_session_factory):
        r1 = import_dataset(db_session_factory, SAMPLE_DIR)
        assert r1.status == "completed"
        r2 = import_dataset(db_session_factory, SAMPLE_DIR)
        assert r2.status == "already_imported"

    def test_dry_run_no_business_data(self, db_session_factory):
        result = import_dataset(db_session_factory, SAMPLE_DIR, dry_run=True)
        assert result.status == "skipped"
        with db_session_factory() as s:
            from app.models.item import Item
            assert s.query(Item).count() == 0
