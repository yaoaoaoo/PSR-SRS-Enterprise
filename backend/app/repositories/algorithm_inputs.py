"""Algorithm input adapters.

Bridge between Repository layer (SQLAlchemy ORM) and Algorithm layer
(pure Python dataclasses).  Each adapter function accepts Repository
instances and returns data structures compatible with Phase E1 algorithm
contracts.

No SQLAlchemy types leak into the algorithm layer.
"""

from __future__ import annotations

from app.repositories.event_repository import EventRepository
from app.repositories.item_repository import ItemRepository
from app.repositories.qrel_repository import QrelRepository
from app.repositories.user_repository import UserRepository


def build_indexing_input(item_repo: ItemRepository) -> list[tuple[str, str]]:
    """Produce ``[(item_id, weighted_text), ...]`` for BM25 / semantic index
    construction.

    Returns:
        ``Sequence[tuple[str, str]]`` as expected by ``BM25Index.build()``.
    """
    return item_repo.list_for_indexing()


def build_profile_input(
    event_repo: EventRepository,
    item_repo: ItemRepository,
    user_repo: UserRepository,
) -> tuple[list[dict], dict[str, dict], dict[str, dict]]:
    """Produce inputs for ``build_profiles()``.

    Returns:
        ``(train_events, items_map, users_map)`` where each element
        matches the Phase E1 profile-building contract.
    """
    train_events = event_repo.list_training_events()
    items_map = item_repo.build_items_map()
    users_map = user_repo.build_users_map()
    return train_events, items_map, users_map


def build_rerank_input(
    item_repo: ItemRepository,
) -> dict[str, dict]:
    """Produce ``items_map`` for ``rerank_candidates()``.

    Returns:
        ``{item_id: {category, subcategory, brand, price}}``
    """
    return item_repo.build_items_map()


def build_evaluation_input(
    qrel_repo: QrelRepository,
) -> dict[str, dict[str, int]]:
    """Produce ``qrels_map`` for ``evaluate_query()`` / ``evaluate_all()``.

    Returns:
        ``{query_id: {item_id: relevance_grade}}``
    """
    return qrel_repo.build_qrels_map()
