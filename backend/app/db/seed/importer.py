"""Transactional dataset importer.

Imports parsed CSV data into the database within a single transaction.
Supports dry-run, idempotent re-import, and replace mode.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.seed.fingerprint import compute_fingerprint
from app.db.seed.readers import read_events, read_items, read_qrels, read_queries, read_users
from app.db.seed.types import ImportResult
from app.db.seed.validator import (
    ValidationError,
    validate_events,
    validate_items,
    validate_qrels,
    validate_queries,
    validate_users,
)
from app.models.event import Event
from app.models.import_run import ImportRun
from app.models.item import Item
from app.models.qrel import Qrel
from app.models.query import Query
from app.models.user import User

logger = logging.getLogger(__name__)

# Delete order respects foreign-key constraints (children first).
_DELETE_ORDER = (Event, Qrel, Query, Item, User)


def _check_existing(session: Session, fingerprint: str) -> str | None:
    """Return status if a completed import with this fingerprint exists."""
    existing = (
        session.execute(
            select(ImportRun).where(
                ImportRun.dataset_fingerprint == fingerprint,
                ImportRun.status == "completed",
            )
        )
        .scalars()
        .first()
    )
    if existing:
        return "already_imported"
    return None


def _has_business_data(session: Session) -> bool:
    """Check if any business tables contain data."""
    for model in (Item, User, Query, Event, Qrel):
        row = session.execute(select(model).limit(1)).first()
        if row is not None:
            return True
    return False


def _delete_business_data(session: Session) -> None:
    """Delete all rows from business tables in foreign-key-safe order."""
    for model in _DELETE_ORDER:
        session.execute(delete(model))
    session.flush()


def _write_import_run(
    session: Session,
    fingerprint: str,
    source_path: str | None,
    status: str,
    counts: dict[str, int],
    started_at: datetime,
    error_message: str | None = None,
) -> ImportRun:
    run = ImportRun(
        dataset_name="sample",
        dataset_fingerprint=fingerprint,
        source_path=source_path,
        status=status,
        items_count=counts.get("items_count", 0),
        users_count=counts.get("users_count", 0),
        queries_count=counts.get("queries_count", 0),
        events_count=counts.get("events_count", 0),
        qrels_count=counts.get("qrels_count", 0),
        started_at=started_at,
        finished_at=datetime.now(UTC),
        error_message=error_message,
    )
    session.add(run)
    session.flush()
    return run


def _bulk_insert(session: Session, model_cls, rows: list[dict[str, Any]], batch_size: int) -> int:
    """Insert rows in batches.  Returns total count."""
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        session.execute(model_cls.__table__.insert(), batch)
        total += len(batch)
    session.flush()
    return total


def _record_failure(
    session_factory: sessionmaker[Session],
    fingerprint: str,
    source_path: str,
    counts: dict,
    started_at: datetime,
    error_msg: str,
) -> None:
    """Record a failed import run in a separate transaction."""
    try:
        fail_session = session_factory()
        try:
            _write_import_run(
                fail_session, fingerprint, source_path, "failed",
                counts, started_at, error_message=error_msg,
            )
            fail_session.commit()
        except Exception:
            fail_session.rollback()
            raise
        finally:
            fail_session.close()
    except Exception:
        logger.exception("Failed to record ImportRun failure")


def import_dataset(
    session_factory: sessionmaker[Session],
    source_dir: Path,
    *,
    replace: bool = False,
    dry_run: bool = False,
    batch_size: int = 1000,
) -> ImportResult:
    """Import the sample dataset from *source_dir*.

    Args:
        session_factory: SQLAlchemy sessionmaker.
        source_dir: Directory containing the five CSV files.
        replace: If True, delete existing business data before import.
        dry_run: If True, validate only — do not write to database.
        batch_size: Number of events per INSERT batch.

    Returns:
        ``ImportResult`` summarising the operation.
    """
    started_at = datetime.now(UTC)
    source_path = str(source_dir.resolve())

    # 1. Compute fingerprint
    fingerprint = compute_fingerprint(source_dir)
    logger.info("Dataset fingerprint: %s", fingerprint[:16])

    # 2. Read and validate CSVs
    items_raw = read_items(source_dir / "items.csv")
    users_raw = read_users(source_dir / "users.csv")
    queries_raw = read_queries(source_dir / "queries.csv")
    events_raw = list(read_events(source_dir / "events.csv"))
    qrels_raw = read_qrels(source_dir / "qrels.csv")

    items_parsed = validate_items(items_raw)
    users_parsed = validate_users(users_raw)
    queries_parsed = validate_queries(queries_raw)

    item_ids = {r["item_id"] for r in items_parsed}
    user_ids = {r["user_id"] for r in users_parsed}
    query_ids = {r["query_id"] for r in queries_parsed}

    events_parsed = validate_events(events_raw, user_ids, item_ids, query_ids)
    qrels_parsed = validate_qrels(qrels_raw, query_ids, item_ids)

    counts = {
        "items_count": len(items_parsed),
        "users_count": len(users_parsed),
        "queries_count": len(queries_parsed),
        "events_count": len(events_parsed),
        "qrels_count": len(qrels_parsed),
    }

    if dry_run:
        logger.info("Dry-run validation passed — no data written.")
        return ImportResult(
            status="skipped",
            dataset_fingerprint=fingerprint,
            duration_seconds=(datetime.now(UTC) - started_at).total_seconds(),
            **counts,
        )

    # 3. Import with transaction
    session = session_factory()
    try:
        # Check for existing completed import (skip if replacing)
        if not replace:
            existing_status = _check_existing(session, fingerprint)
            if existing_status == "already_imported":
                session.rollback()
                duration = (datetime.now(UTC) - started_at).total_seconds()
                logger.info("Dataset already imported (fingerprint match).")
                return ImportResult(
                    status="already_imported",
                    dataset_fingerprint=fingerprint,
                    duration_seconds=duration,
                    **counts,
                )

        # Check for conflicting data
        if _has_business_data(session) and not replace:
            session.rollback()
            raise ValidationError([
                "Database already contains business data. "
                "Use --replace to overwrite, or clear the database first."
            ])

        # Replace: delete existing data
        if replace:
            _delete_business_data(session)
            session.execute(delete(ImportRun))

        # Write ImportRun (running)
        import_run = _write_import_run(
            session, fingerprint, source_path, "running", counts, started_at,
        )

        # Insert data in dependency order
        _bulk_insert(session, User, users_parsed, batch_size)
        _bulk_insert(session, Item, items_parsed, batch_size)
        _bulk_insert(session, Query, queries_parsed, batch_size)
        _bulk_insert(session, Qrel, qrels_parsed, batch_size)
        _bulk_insert(session, Event, events_parsed, batch_size)

        # Mark as completed
        import_run.status = "completed"
        import_run.finished_at = datetime.now(UTC)
        session.commit()

        duration = (datetime.now(UTC) - started_at).total_seconds()
        logger.info(
            "Import completed: %d items, %d users, %d queries, %d events, %d qrels (%.1fs)",
            counts["items_count"], counts["users_count"], counts["queries_count"],
            counts["events_count"], counts["qrels_count"], duration,
        )

        return ImportResult(
            status="completed",
            dataset_fingerprint=fingerprint,
            duration_seconds=duration,
            **counts,
        )

    except Exception as exc:
        session.rollback()
        duration = (datetime.now(UTC) - started_at).total_seconds()
        error_msg = str(exc)[:2000]

        # Try to record the failure in a separate transaction
        _record_failure(session_factory, fingerprint, source_path, counts, started_at, error_msg)

        logger.error("Import failed: %s", error_msg)
        return ImportResult(
            status="failed",
            dataset_fingerprint=fingerprint,
            duration_seconds=duration,
            error_message=error_msg,
            **counts,
        )
    finally:
        session.close()
