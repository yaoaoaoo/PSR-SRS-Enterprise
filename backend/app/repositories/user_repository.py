"""UserRepository — queries for the users table."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Data access for users."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, user_id: str) -> User | None:
        return self._session.get(User, user_id)

    def count(self) -> int:
        from sqlalchemy import func, select
        stmt = select(func.count()).select_from(User)
        return self._session.execute(stmt).scalar_one()

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        is_cold_start: bool | None = None,
    ) -> list[User]:
        stmt = select(User).order_by(User.user_id)
        if is_cold_start is not None:
            stmt = stmt.where(User.is_cold_start == is_cold_start)
        return list(
            self._session.execute(stmt.offset(offset).limit(limit)).scalars().all()
        )

    def get_many_by_ids(self, user_ids: list[str]) -> list[User]:
        if not user_ids:
            return []
        stmt = (
            select(User)
            .where(User.user_id.in_(user_ids))
            .order_by(User.user_id)
        )
        return list(self._session.execute(stmt).scalars().all())

    def build_users_map(self) -> dict[str, dict]:
        """Return ``{user_id: {is_cold_start, ...}}`` for profile building."""
        users = self._session.execute(
            select(User).order_by(User.user_id)
        ).scalars().all()

        return {
            user.user_id: {
                "is_cold_start": str(user.is_cold_start).lower(),
            }
            for user in users
        }
