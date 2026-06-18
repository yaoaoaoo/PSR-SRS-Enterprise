"""IndexManager — thread-safe, atomic index lifecycle.

Builds and manages BM25 + Semantic indices from repository data.
Uses atomic snapshot replacement: a new index is built fully before
it replaces the currently-serving one.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import sessionmaker

from app.core.service_config import service_settings
from app.repositories.item_repository import ItemRepository
from app.retrieval.bm25 import BM25Config, BM25Index
from app.retrieval.fusion import FusionConfig
from app.retrieval.semantic import SemanticIndex
from app.retrieval.vectorization import SemanticConfig
from app.services.errors import IndexNotReadyError
from app.services.types import IndexStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IndexSnapshot:
    """Immutable snapshot of retrieval indices and item metadata."""

    generation: int
    built_at: datetime
    item_count: int
    bm25_index: BM25Index
    semantic_index: SemanticIndex
    items_map: dict[str, dict[str, Any]]


class IndexManager:
    """Manages BM25 and LSA retrieval indices with atomic swap."""

    def __init__(
        self,
        session_factory: sessionmaker,
        bm25_config: BM25Config | None = None,
        semantic_config: SemanticConfig | None = None,
        fusion_config: FusionConfig | None = None,
    ):
        self._session_factory = session_factory
        self._bm25_config = bm25_config or BM25Config()
        self._semantic_config = semantic_config or SemanticConfig()
        self._fusion_config = fusion_config or FusionConfig()

        self._lock = threading.RLock()
        self._snapshot: IndexSnapshot | None = None
        self._generation: int = 0
        self._error_message: str | None = None

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> None:
        """Build indices from the database.  Blocks until complete."""
        with self._lock:
            self._build_unlocked()

    def rebuild(self) -> None:
        """Alias for build — rebuild from scratch."""
        self.build()

    def _build_unlocked(self) -> None:
        """Assumes external lock."""
        logger.info("Index build started")
        t0 = datetime.now(UTC)

        session = self._session_factory()
        try:
            repo = ItemRepository(session)
            indexing_pairs = repo.list_for_indexing()
            items_map = repo.build_items_map()
        finally:
            session.close()

        if not indexing_pairs:
            msg = "No items to index"
            if service_settings.INDEX_ALLOW_EMPTY:
                logger.warning(msg)
                self._error_message = msg
                return
            self._error_message = msg
            raise IndexNotReadyError(msg)

        try:
            # Build BM25
            bm25 = BM25Index.build(
                [(iid, text) for iid, text in indexing_pairs],
                k1=self._bm25_config.k1, b=self._bm25_config.b,
            )

            # Build Semantic
            texts = [text for _, text in indexing_pairs]
            ids = [iid for iid, _ in indexing_pairs]
            sem = SemanticIndex.build(texts, ids, self._semantic_config)

        except Exception:
            self._error_message = "Index build failed — previous snapshot preserved"
            logger.exception(self._error_message)
            return

        self._generation += 1
        snapshot = IndexSnapshot(
            generation=self._generation,
            built_at=datetime.now(UTC),
            item_count=bm25.document_count,
            bm25_index=bm25,
            semantic_index=sem,
            items_map=items_map,
        )
        self._snapshot = snapshot
        self._error_message = None
        elapsed = (datetime.now(UTC) - t0).total_seconds()
        logger.info(
            "Index build completed | generation=%d items=%d duration=%.2fs",
            self._generation, bm25.document_count, elapsed,
        )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_snapshot(self) -> IndexSnapshot:
        """Return the current index snapshot.

        Raises ``IndexNotReadyError`` if no index has been built.
        """
        with self._lock:
            snap = self._snapshot
        if snap is None:
            raise IndexNotReadyError("No index built — call build() first")
        return snap

    def get_status(self) -> IndexStatus:
        with self._lock:
            snap = self._snapshot
            gen = self._generation
            err = self._error_message
        if snap is not None:
            return IndexStatus(
                ready=True, generation=snap.generation,
                built_at=snap.built_at, item_count=snap.item_count,
            )
        return IndexStatus(
            ready=False, generation=gen,
            built_at=None, item_count=0, error_message=err,
        )

    def is_ready(self) -> bool:
        return self.get_status().ready
