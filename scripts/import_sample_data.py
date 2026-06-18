"""Import the sample dataset into the Enterprise database.

Usage::

    python scripts/import_sample_data.py
    python scripts/import_sample_data.py --dry-run
    python scripts/import_sample_data.py --replace
    python scripts/import_sample_data.py --source path/to/data --report path/to/report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add backend to path so we can import app modules
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))


def main():
    parser = argparse.ArgumentParser(
        description="Import the PSR-SRS Enterprise sample dataset"
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Path to directory containing items/users/queries/events/qrels.csv",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override DATABASE_URL (default: from app config)",
    )
    parser.add_argument(
        "--replace", action="store_true",
        help="Delete existing business data before import",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate CSVs only — do not write to database",
    )
    parser.add_argument(
        "--batch-size", type=int, default=1000,
        help="Number of events per INSERT batch (default: 1000)",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Path for JSON import report",
    )
    args = parser.parse_args()

    import os

    from app.core.config import settings

    # Override database URL if provided
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    from app.db.seed.importer import import_dataset
    from app.db.session import _get_session_factory

    # Determine source directory
    if args.source:
        source_dir = Path(args.source)
    else:
        source_dir = settings.project_root / "data" / "sample"

    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}", file=sys.stderr)
        sys.exit(1)

    # Run import
    print(f"Source:      {source_dir}")
    print(f"Database:    {settings.resolved_database_url}")
    print(f"Mode:        {'dry-run' if args.dry_run else 'replace' if args.replace else 'import'}")
    print()

    session_factory = _get_session_factory()
    result = import_dataset(
        session_factory=session_factory,
        source_dir=source_dir,
        replace=args.replace,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
    )

    # Print summary
    print()
    print(f"Status:       {result.status}")
    print(f"Fingerprint:  {result.dataset_fingerprint[:16]}...")
    if not args.dry_run and result.status not in ("already_imported", "skipped"):
        print(f"Items:        {result.items_count}")
        print(f"Users:        {result.users_count}")
        print(f"Queries:      {result.queries_count}")
        print(f"Events:       {result.events_count}")
        print(f"Qrels:        {result.qrels_count}")
    print(f"Duration:     {result.duration_seconds:.1f}s")
    if result.error_message:
        print(f"Error:        {result.error_message}")

    # Write report
    report_path = args.report
    if report_path is None:
        report_path = str(settings.project_root / "outputs" / "e2_import_report.json")

    report = {
        "status": result.status,
        "dataset_fingerprint": result.dataset_fingerprint,
        "source_path": str(source_dir.resolve()),
        "database_url_sanitized": settings.resolved_database_url.replace(
            str(settings.project_root), "<project_root>"
        ),
        "items_count": result.items_count,
        "users_count": result.users_count,
        "queries_count": result.queries_count,
        "events_count": result.events_count,
        "qrels_count": result.qrels_count,
        "duration_seconds": result.duration_seconds,
        "already_imported": result.status == "already_imported",
        "dry_run": args.dry_run,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    if result.error_message:
        report["error_message"] = result.error_message

    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport: {report_path}")

    sys.exit(0 if result.status in ("completed", "already_imported", "skipped") else 1)


if __name__ == "__main__":
    main()
