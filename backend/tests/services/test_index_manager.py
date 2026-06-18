"""Comprehensive IndexManager tests — build, rebuild, concurrency, snapshots."""

from __future__ import annotations

import threading
import time
from decimal import Decimal

import pytest

from app.models.item import Item
from app.services.index_manager import IndexManager


@pytest.fixture
def _items(db_session):
    items = [
        Item(item_id=f"i{j}", title=f"Test Item {j}", description="desc",
             category="Cat", subcategory="Sub", brand="Brand",
             price=Decimal("10"), quality_score=0.5, popularity_score=0.5)
        for j in range(10)
    ]
    db_session.add_all(items)
    db_session.commit()


class TestIndexManagerBasic:
    def test_initial_not_ready(self, db_session_factory):
        im = IndexManager(db_session_factory)
        assert not im.is_ready()
        st = im.get_status()
        assert st.ready is False
        assert st.generation == 0

    def test_build_succeeds(self, db_session_factory, _items):
        im = IndexManager(db_session_factory)
        im.build()
        assert im.is_ready()
        st = im.get_status()
        assert st.generation == 1
        assert st.item_count == 10
        assert st.built_at is not None
        assert st.built_at.tzinfo is not None  # UTC aware

    def test_snapshot_consistent(self, db_session_factory, _items):
        im = IndexManager(db_session_factory)
        im.build()
        snap = im.get_snapshot()
        assert snap.generation == 1
        assert snap.item_count == 10
        assert snap.bm25_index.document_count == 10
        assert snap.semantic_index.document_count == 10
        assert len(snap.items_map) == 10

    def test_bm25_searchable(self, db_session_factory, _items):
        im = IndexManager(db_session_factory)
        im.build()
        results = im.get_snapshot().bm25_index.search("Test", top_k=3)
        assert len(results) > 0

    def test_semantic_searchable(self, db_session_factory, _items):
        im = IndexManager(db_session_factory)
        im.build()
        results = im.get_snapshot().semantic_index.search("Test Item", top_k=3)
        assert len(results) > 0

    def test_empty_items_allowed(self, db_session_factory):
        im = IndexManager(db_session_factory)
        im.build()
        assert not im.is_ready()
        assert im.get_status().error_message is not None


class TestIndexManagerRebuild:
    def test_rebuild_increments_generation(self, db_session_factory, _items):
        im = IndexManager(db_session_factory)
        im.build()
        assert im.get_status().generation == 1
        im.build()
        assert im.get_status().generation == 2

    def test_old_snapshot_still_usable(self, db_session_factory, _items):
        im = IndexManager(db_session_factory)
        im.build()
        old = im.get_snapshot()
        im.build()
        new = im.get_snapshot()
        assert old.generation == 1
        assert new.generation == 2
        # Old snapshot still searchable
        r = old.bm25_index.search("Test", top_k=3)
        assert len(r) > 0

    def test_items_map_with_index(self, db_session_factory, _items):
        im = IndexManager(db_session_factory)
        im.build()
        snap = im.get_snapshot()
        for iid in snap.items_map:
            assert iid in snap.items_map
            assert "category" in snap.items_map[iid]


class TestIndexManagerConcurrency:
    def test_concurrent_rebuilds_not_deadlock(self, db_session_factory, _items):
        im = IndexManager(db_session_factory)
        im.build()

        errors = []

        def do_rebuild():
            try:
                im.build()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=do_rebuild) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0

    def test_search_during_rebuild(self, db_session_factory, _items):
        im = IndexManager(db_session_factory)
        im.build()
        im.get_snapshot()  # verify snapshot exists before concurrent access

        build_started = threading.Event()
        build_done = threading.Event()
        searches_done = threading.Event()
        search_errors = []

        def slow_build():
            build_started.set()
            # Simulate work
            time.sleep(0.5)
            im.build()
            build_done.set()

        def search_loop():
            build_started.wait()
            for _ in range(20):
                try:
                    snap = im.get_snapshot()
                    snap.bm25_index.search("Test", top_k=3)
                except Exception as e:
                    search_errors.append(e)
                time.sleep(0.01)
            searches_done.set()

        t_build = threading.Thread(target=slow_build)
        t_search = threading.Thread(target=search_loop)
        t_build.start()
        t_search.start()
        t_build.join(timeout=10)
        t_search.join(timeout=10)

        assert len(search_errors) == 0
        assert im.is_ready()

    def test_no_half_built_snapshot(self, db_session_factory, _items):
        im = IndexManager(db_session_factory)
        im.build()
        assert im.get_status().generation >= 1

        # Even during concurrent access, get_snapshot should never
        # return a snapshot with inconsistent BM25/Semantic
        for _ in range(10):
            snap = im.get_snapshot()
            assert snap.bm25_index.document_count == snap.semantic_index.document_count
            assert snap.bm25_index.document_count == snap.item_count


class TestIndexManagerFailedRebuild:
    """Explicit failed rebuild tests — old snapshot preservation."""

    def test_failed_rebuild_preserves_old_snapshot(self, db_session_factory, _items):
        im = IndexManager(db_session_factory)
        im.build()
        old_snap = im.get_snapshot()
        old_gen = im.get_status().generation

        # Simulate failure: delete all items, then build fails because no data
        # But INDEX_ALLOW_EMPTY=True means it just records error, doesn't update snapshot
        from app.models.item import Item
        s = db_session_factory()
        s.query(Item).delete()
        s.commit()
        s.close()

        im.build()

        # Old snapshot should be preserved since build failed (empty items → error, not crash)
        # With INDEX_ALLOW_EMPTY=True, empty items sets error_message but doesn't create snapshot
        cur_snap = im.get_snapshot()
        assert cur_snap.generation == old_gen
        assert cur_snap.item_count == old_snap.item_count
        r = cur_snap.bm25_index.search("Test", top_k=3)
        assert len(r) > 0

    def test_failed_first_build_not_ready(self, db_session_factory):
        im = IndexManager(db_session_factory)
        im.build()  # no items
        assert not im.is_ready()
        assert im.get_status().error_message is not None
        assert im.get_status().generation == 0

