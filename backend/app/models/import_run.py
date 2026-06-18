"""ImportRun model — audit trail for dataset imports."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ImportRun(Base):
    __tablename__ = "import_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_name: Mapped[str] = mapped_column(
        String(128), nullable=False,
        comment="Human-readable dataset label",
    )
    dataset_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="SHA-256 hex digest of dataset content",
    )
    source_path: Mapped[str | None] = mapped_column(
        String(1024), nullable=True,
        comment="Directory path used for import (audit only)",
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="running",
    )
    items_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    users_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    queries_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    events_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qrels_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        String(2048), nullable=True,
        comment="Error details if status is 'failed'",
    )

    __table_args__ = (
        Index("ix_import_runs_fingerprint_status", "dataset_fingerprint", "status"),
        Index("ix_import_runs_started_at", "started_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ImportRun id={self.id} fingerprint={self.dataset_fingerprint[:12]}... "
            f"status={self.status!r}>"
        )
