"""Shared types for the data import pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImportResult:
    """Immutable result of a dataset import operation."""

    status: str  # "completed", "already_imported", "skipped", "failed"
    dataset_fingerprint: str
    items_count: int = 0
    users_count: int = 0
    queries_count: int = 0
    events_count: int = 0
    qrels_count: int = 0
    duration_seconds: float = 0.0
    error_message: str | None = None
