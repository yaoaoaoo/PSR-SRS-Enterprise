"""QueryRepository — queries for the queries table."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.query import Query


class QueryRepository:
    """Data access for queries."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, query_id: str) -> Query | None:
        return self._session.get(Query, query_id)

    def count(self) -> int:
        from sqlalchemy import func, select
        stmt = select(func.count()).select_from(Query)
        return self._session.execute(stmt).scalar_one()

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        category: str | None = None,
    ) -> list[Query]:
        stmt = select(Query).order_by(Query.query_id)
        if category:
            stmt = stmt.where(Query.intended_category == category)
        return list(
            self._session.execute(stmt.offset(offset).limit(limit)).scalars().all()
        )

    def get_many_by_ids(self, query_ids: list[str]) -> list[Query]:
        if not query_ids:
            return []
        stmt = (
            select(Query)
            .where(Query.query_id.in_(query_ids))
            .order_by(Query.query_id)
        )
        return list(self._session.execute(stmt).scalars().all())
