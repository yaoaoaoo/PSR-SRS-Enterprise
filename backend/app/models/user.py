"""User ORM model — corresponds to MVP users.csv."""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    preferred_categories: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="JSON array of preferred category strings",
    )
    preferred_brands: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="JSON array of preferred brand strings",
    )
    price_preference: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="Preferred price tier (e.g. budget, mid_range, premium)",
    )
    activity_level: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True,
        comment="Activity level (e.g. low, medium, high)",
    )
    is_cold_start: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True,
    )

    def __repr__(self) -> str:
        return f"<User {self.user_id!r} cold_start={self.is_cold_start}>"
