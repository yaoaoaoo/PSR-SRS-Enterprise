"""Item ORM model — corresponds to MVP items.csv."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Item(TimestampMixin, Base):
    __tablename__ = "items"

    item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(String(2048), nullable=False, default="")
    category: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    subcategory: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False,
        comment="Item price in arbitrary currency units",
    )
    quality_score: Mapped[float] = mapped_column(nullable=False)
    popularity_score: Mapped[float] = mapped_column(nullable=False)
    is_cold_start: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True,
    )

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_item_price_non_negative"),
        CheckConstraint(
            "quality_score >= 0 AND quality_score <= 1",
            name="ck_item_quality_score_range",
        ),
        CheckConstraint(
            "popularity_score >= 0 AND popularity_score <= 1",
            name="ck_item_popularity_score_range",
        ),
        Index("ix_items_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Item {self.item_id!r} title={self.title[:30]!r}>"
