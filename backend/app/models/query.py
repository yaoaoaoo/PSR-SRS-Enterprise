"""Query ORM model — corresponds to MVP queries.csv."""

from __future__ import annotations

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Query(TimestampMixin, Base):
    __tablename__ = "queries"

    query_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    query_text: Mapped[str] = mapped_column(
        String(512), nullable=False, index=True,
    )
    intended_category: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True,
    )
    semantic_intent: Mapped[str | None] = mapped_column(
        String(128), nullable=True,
    )

    __table_args__ = (
        Index("ix_queries_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Query {self.query_id!r} text={self.query_text[:40]!r}>"
