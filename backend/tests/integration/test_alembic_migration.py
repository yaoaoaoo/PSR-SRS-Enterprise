"""Tests for Alembic migrations on SQLite - fresh DB, upgrade, downgrade."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent.parent
PYTHON = sys.executable


def _run_alembic(db_url: str, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": db_url}
    return subprocess.run(
        [PYTHON, "-m", "alembic", *args],
        capture_output=True, text=True, timeout=30,
        cwd=str(BACKEND), env=env,
    )


def _temp_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_alembic_")
    os.close(fd)
    return f"sqlite:///{path}"


def _cleanup(db_url: str):
    path = db_url.replace("sqlite:///", "")
    for suffix in ("", "-journal", "-wal", "-shm"):
        p = Path(path + suffix)
        if p.exists():
            p.unlink()


class TestAlembicMigration:
    def test_empty_db_to_head(self):
        db = _temp_db()
        try:
            r = _run_alembic(db, "upgrade", "head")
            assert r.returncode == 0, (
                f"upgrade failed:\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"
            )
            r2 = _run_alembic(db, "current")
            assert r2.returncode == 0
            assert "1d69fffd1e6b" in r2.stdout or "head" in r2.stdout.lower()
        finally:
            _cleanup(db)

    def test_upgrade_downgrade_cycle(self):
        db = _temp_db()
        try:
            r = _run_alembic(db, "upgrade", "head")
            assert r.returncode == 0, (
                f"upgrade failed:\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"
            )
            r2 = _run_alembic(db, "downgrade", "cfe827193ef4")
            assert r2.returncode == 0, (
                f"downgrade failed:\nstdout:\n{r2.stdout}\nstderr:\n{r2.stderr}"
            )
            r3 = _run_alembic(db, "upgrade", "head")
            assert r3.returncode == 0, (
                f"re-upgrade failed:\nstdout:\n{r3.stdout}\nstderr:\n{r3.stderr}"
            )
        finally:
            _cleanup(db)

    def test_client_event_id_column_exists(self):
        db = _temp_db()
        try:
            r = _run_alembic(db, "upgrade", "head")
            assert r.returncode == 0
            from sqlalchemy import create_engine, text
            engine = create_engine(db, echo=False)
            try:
                with engine.connect() as conn:
                    columns = [
                        row[1] for row in
                        conn.execute(text("PRAGMA table_info('events')")).fetchall()
                    ]
                    assert "client_event_id" in columns, f"Missing column, got: {columns}"
            finally:
                engine.dispose()
        finally:
            _cleanup(db)

    def test_no_sqlite_syntax_error(self):
        """Verify the migration executes without SQLite syntax errors."""
        db = _temp_db()
        try:
            r = _run_alembic(db, "upgrade", "head")
            assert r.returncode == 0, (
                f"Migration produced error:\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"
            )
        finally:
            _cleanup(db)

    def test_data_preserved_across_migration(self):
        """Insert user, item, query, event at 0001, upgrade, verify all intact."""
        db = _temp_db()
        try:
            # Upgrade to 0001
            r = _run_alembic(db, "upgrade", "cfe827193ef4")
            assert r.returncode == 0, f"0001 upgrade failed: {r.stderr[:500]}"

            from sqlalchemy import create_engine, text
            engine = create_engine(db, echo=False)
            try:
                with engine.connect() as conn:
                    conn.execute(text(
                        "INSERT INTO users "
                        "(user_id, preferred_categories, preferred_brands, "
                        "price_preference, activity_level, is_cold_start, created_at) "
                        "VALUES "
                        "('u_test', '[]', '[]', 'mid_range', 'low', 0, '2026-01-01T00:00:00Z')"
                    ))
                    conn.execute(text(
                        "INSERT INTO items "
                        "(item_id, title, description, category, subcategory, brand, "
                        "price, quality_score, popularity_score, is_cold_start, created_at) "
                        "VALUES "
                        "('i_test', 'Test Item', '', 'Electronics', 'Sub', 'Brand', "
                        "10, 0.5, 0.5, 0, '2026-01-01T00:00:00Z')"
                    ))
                    conn.execute(text(
                        "INSERT INTO queries (query_id, query_text, created_at) "
                        "VALUES ('q_test', 'test query', '2026-01-01T00:00:00Z')"
                    ))
                    conn.execute(text(
                        "INSERT INTO events "
                        "(event_id, event_type, request_id, session_id, "
                        "user_id, item_id, timestamp) "
                        "VALUES "
                        "('ev_test', 'click', 'req_1', 'sess_1', "
                        "'u_test', 'i_test', '2026-01-01T00:00:00Z')"
                    ))
                    conn.commit()
                engine.dispose()

                # Upgrade to head
                r2 = _run_alembic(db, "upgrade", "head")
                assert r2.returncode == 0, f"upgrade failed: {r2.stderr[:500]}"

                engine2 = create_engine(db, echo=False)
                try:
                    with engine2.connect() as conn:
                        # User preserved
                        u = conn.execute(text(
                            "SELECT user_id, price_preference FROM users WHERE user_id='u_test'"
                        )).fetchone()
                        assert u is not None, "User lost"
                        assert u[1] == 'mid_range', f"price_preference changed: {u[1]!r}"

                        # Event preserved
                        e = conn.execute(text(
                            "SELECT event_id FROM events WHERE event_id='ev_test'"
                        )).fetchone()
                        assert e is not None, "Event lost"

                        # client_event_id column exists, old event has NULL
                        cols = [
                            row[1] for row in
                            conn.execute(text("PRAGMA table_info('events')")).fetchall()
                        ]
                        assert "client_event_id" in cols, f"No client_event_id in {cols}"
                        cei = conn.execute(text(
                            "SELECT client_event_id FROM events WHERE event_id='ev_test'"
                        )).fetchone()
                        assert cei[0] is None, f"Expected NULL, got {cei[0]!r}"

                        # price_preference type is now String
                        user_cols = {
                            r[1]: r[2] for r in
                            conn.execute(text("PRAGMA table_info('users')")).fetchall()
                        }
                        pp_type = user_cols.get('price_preference', '').upper()
                        assert 'VARCHAR' in pp_type or 'TEXT' in pp_type or 'STRING' in pp_type, (
                            f"price_preference not String: {user_cols.get('price_preference')}"
                        )

                        # Unique index on client_event_id exists
                        indexes = [
                            row[1] for row in
                            conn.execute(text(
                                "SELECT * FROM sqlite_master WHERE type='index' AND tbl_name='events'"
                            )).fetchall()
                        ]
                        has_cei_idx = any('client_event_id' in (idx or '') for idx in indexes)
                        assert has_cei_idx, f"No client_event_id index found in: {indexes}"
                finally:
                    engine2.dispose()
            finally:
                if 'engine' in dir() and engine:
                    import contextlib
                    with contextlib.suppress(Exception):
                        engine.dispose()
        finally:
            _cleanup(db)
