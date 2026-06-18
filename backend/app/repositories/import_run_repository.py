"""ImportRunRepository — queries for the import_runs table."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.import_run import ImportRun


class ImportRunRepository:
    """Data access for import runs."""

    def __init__(self, session: Session):
        self._session = session

    def get_latest_completed(self) -> ImportRun | None:
        stmt = (
            select(ImportRun)
            .where(ImportRun.status == "completed")
            .order_by(ImportRun.finished_at.desc())
            .limit(1)
        )
        return self._session.execute(stmt).scalars().first()

    def get_by_fingerprint(self, fingerprint: str) -> ImportRun | None:
        stmt = (
            select(ImportRun)
            .where(ImportRun.dataset_fingerprint == fingerprint)
            .order_by(ImportRun.started_at.desc())
            .limit(1)
        )
        return self._session.execute(stmt).scalars().first()

    def list_all(self, *, limit: int = 20) -> list[ImportRun]:
        stmt = (
            select(ImportRun)
            .order_by(ImportRun.started_at.desc())
            .limit(limit)
        )
        return list(self._session.execute(stmt).scalars().all())
