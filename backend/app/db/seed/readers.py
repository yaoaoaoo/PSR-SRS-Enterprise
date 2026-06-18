"""CSV readers for sample data files.

Reads CSV files with UTF-8 encoding, BOM handling, and streaming
for large files (events).
"""

from __future__ import annotations

import csv
import logging
from collections.abc import Iterator
from pathlib import Path

logger = logging.getLogger(__name__)

EXPECTED_HEADERS: dict[str, list[str]] = {
    "items.csv": [
        "item_id", "title", "description", "category", "subcategory",
        "brand", "price", "quality_score", "popularity_score",
        "is_cold_start", "created_at",
    ],
    "users.csv": [
        "user_id", "preferred_categories", "preferred_brands",
        "price_preference", "activity_level", "is_cold_start", "created_at",
    ],
    "queries.csv": [
        "query_id", "query_text", "intended_category",
        "semantic_intent", "created_at",
    ],
    "events.csv": [
        "event_id", "event_type", "request_id", "session_id",
        "user_id", "query_id", "query_text", "item_id", "position",
        "timestamp", "click_duration_ms", "add_to_cart_quantity",
        "purchase_amount",
    ],
    "qrels.csv": [
        "query_id", "item_id", "relevance_grade",
    ],
}


def _open_csv(path: Path) -> Iterator[dict[str, str]]:
    """Yield rows from a CSV file, validating the header."""
    with path.open("r", encoding="utf-8-sig", newline="") as f:  # utf-8-sig handles BOM
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV {path.name} has no header row")

        expected = EXPECTED_HEADERS.get(path.name)
        if expected is not None:
            actual = list(reader.fieldnames)
            if actual != expected:
                raise ValueError(
                    f"Header mismatch in {path.name}: "
                    f"expected {expected}, got {actual}"
                )
        yield from reader


def read_items(path: Path) -> list[dict[str, str]]:
    """Read items.csv — small file, load all at once."""
    return list(_open_csv(path))


def read_users(path: Path) -> list[dict[str, str]]:
    """Read users.csv — small file, load all at once."""
    return list(_open_csv(path))


def read_queries(path: Path) -> list[dict[str, str]]:
    """Read queries.csv — small file, load all at once."""
    return list(_open_csv(path))


def read_events(path: Path) -> Iterator[dict[str, str]]:
    """Read events.csv — potentially large, stream row by row."""
    return _open_csv(path)


def read_qrels(path: Path) -> list[dict[str, str]]:
    """Read qrels.csv."""
    return list(_open_csv(path))
