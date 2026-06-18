"""ItemRepository — queries for the items table."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.item import Item
from app.retrieval.tokenization import build_item_text


class ItemRepository:
    """Data access for items."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, item_id: str) -> Item | None:
        return self._session.get(Item, item_id)

    def count(self) -> int:
        stmt = select(func.count()).select_from(Item)
        return self._session.execute(stmt).scalar_one()

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        category: str | None = None,
    ) -> list[Item]:
        stmt = select(Item).order_by(Item.item_id)
        if category:
            stmt = stmt.where(Item.category == category)
        return list(
            self._session.execute(stmt.offset(offset).limit(limit)).scalars().all()
        )

    def get_many_by_ids(self, item_ids: list[str]) -> list[Item]:
        if not item_ids:
            return []
        stmt = (
            select(Item)
            .where(Item.item_id.in_(item_ids))
            .order_by(Item.item_id)
        )
        return list(self._session.execute(stmt).scalars().all())

    def list_for_indexing(self) -> list[tuple[str, str]]:
        """Return ``(item_id, weighted_text)`` pairs for building
        BM25 and semantic retrieval indices."""
        items = self._session.execute(
            select(Item).order_by(Item.item_id)
        ).scalars().all()

        result: list[tuple[str, str]] = []
        for item in items:
            text = build_item_text(
                title=item.title,
                description=item.description,
                category=item.category,
                subcategory=item.subcategory,
                brand=item.brand,
            )
            result.append((item.item_id, text))
        return result

    def build_items_map(self) -> dict[str, dict]:
        """Return ``{item_id: {category, subcategory, brand, price}}``."""
        items = self._session.execute(
            select(Item).order_by(Item.item_id)
        ).scalars().all()

        return {
            item.item_id: {
                "category": item.category,
                "subcategory": item.subcategory,
                "brand": item.brand,
                "price": str(item.price),
            }
            for item in items
        }
