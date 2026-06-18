"""Mid-import failure rollback test — inject exception and verify cleanup."""

from __future__ import annotations

from unittest.mock import patch

from app.db.seed.importer import import_dataset

SAMPLE_DIR = __import__("pathlib").Path("D:/project/PSR-SRS-Enterprise/data/sample")


class TestMidImportRollback:
    def test_failure_after_partial_writes_rolls_back(self, db_session_factory):
        """Inject failure during event insertion, verify all business tables empty."""
        with patch(
            "app.db.seed.importer._bulk_insert",
            side_effect=[
                100,  # users — OK
                500,  # items — OK
                200,  # queries — OK
                10076,  # qrels — OK
                RuntimeError("simulated event insert failure"),  # events — FAIL
            ],
        ):
            result = import_dataset(db_session_factory, SAMPLE_DIR)

        assert result.status == "failed"

        # Verify no business data remains
        with db_session_factory() as s:
            from app.models.event import Event
            from app.models.item import Item
            from app.models.qrel import Qrel
            from app.models.query import Query
            from app.models.user import User
            assert s.query(Item).count() == 0
            assert s.query(User).count() == 0
            assert s.query(Query).count() == 0
            assert s.query(Event).count() == 0
            assert s.query(Qrel).count() == 0

    def test_failed_import_run_recorded(self, db_session_factory):
        """Failed ImportRun should be recorded."""
        with patch(
            "app.db.seed.importer._bulk_insert",
            side_effect=RuntimeError("inject"),
        ):
            import_dataset(db_session_factory, SAMPLE_DIR)

        with db_session_factory() as s:
            from app.models.import_run import ImportRun
            runs = s.query(ImportRun).filter(ImportRun.status == "failed").all()
            assert len(runs) >= 1
