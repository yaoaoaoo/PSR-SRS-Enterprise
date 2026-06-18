"""QrelRepository — queries for the qrels table."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.qrel import Qrel


class QrelRepository:
    """Data access for qrels."""

    def __init__(self, session: Session):
        self._session = session

    def count(self) -> int:
        from sqlalchemy import func, select
        stmt = select(func.count()).select_from(Qrel)
        return self._session.execute(stmt).scalar_one()

    def list_for_query(self, query_id: str) -> list[Qrel]:
        stmt = (
            select(Qrel)
            .where(Qrel.query_id == query_id)
            .order_by(Qrel.item_id)
        )
        return list(self._session.execute(stmt).scalars().all())

    def build_qrels_map(self) -> dict[str, dict[str, int]]:
        """Return ``{query_id: {item_id: relevance_grade}}`` for evaluation."""
        all_qrels = self._session.execute(
            select(Qrel).order_by(Qrel.query_id, Qrel.item_id)
        ).scalars().all()

        result: dict[str, dict[str, int]] = {}
        for q in all_qrels:
            result.setdefault(q.query_id, {})[q.item_id] = q.relevance_grade
        return result
