"""Qrel ORM model — corresponds to MVP qrels.csv."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Qrel(Base):
    __tablename__ = "qrels"

    query_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("queries.query_id", ondelete="RESTRICT"),
        primary_key=True, index=True,
    )
    item_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("items.item_id", ondelete="RESTRICT"),
        primary_key=True, index=True,
    )
    relevance_grade: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Relevance grade 1–3 (3 = most relevant)",
    )

    __table_args__ = (
        CheckConstraint(
            "relevance_grade >= 1 AND relevance_grade <= 3",
            name="ck_qrel_relevance_grade_range",
        ),
        # Composite primary key already provides uniqueness;
        # explicit unique constraint for clarity
        UniqueConstraint("query_id", "item_id", name="uq_qrel_query_item"),
    )

    def __repr__(self) -> str:
        return (
            f"<Qrel query={self.query_id!r} item={self.item_id!r} "
            f"grade={self.relevance_grade}>"
        )
