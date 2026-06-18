"""EvaluationService — offline retrieval evaluation via repositories."""

from __future__ import annotations

import logging
import time

from sqlalchemy.orm import sessionmaker

from app.evaluation.metrics import evaluate_all, macro_average
from app.repositories.algorithm_inputs import build_evaluation_input
from app.repositories.qrel_repository import QrelRepository
from app.repositories.query_repository import QueryRepository
from app.retrieval.fusion import build_candidates, fuse_linear
from app.retrieval.types import SearchResult
from app.services.index_manager import IndexManager
from app.services.types import EvaluationReport

logger = logging.getLogger(__name__)


class EvaluationService:
    """Offline evaluation using qrels and the current retrieval index."""

    def __init__(
        self,
        index_manager: IndexManager,
        session_factory: sessionmaker,
    ):
        self._index_manager = index_manager
        self._session_factory = session_factory

    def evaluate_queries(
        self,
        query_texts: list[str],
        ks: list[int] | None = None,
    ) -> EvaluationReport:
        """Run retrieval for each query and evaluate against qrels."""
        t0 = time.monotonic()

        if ks is None:
            ks = [5, 10, 20]

        snapshot = self._index_manager.get_snapshot()
        session = self._session_factory()
        try:
            qrel_repo = QrelRepository(session)
            query_repo = QueryRepository(session)
            qrels_map = build_evaluation_input(qrel_repo)

            all_results: dict[str, list[SearchResult]] = {}
            queries_data: list[dict[str, str]] = []

            for qid in query_texts:
                q = query_repo.get_by_id(qid)
                query_text = q.query_text if q else qid
                queries_data.append({"query_id": qid, "query_text": query_text})

                bm25_raw = snapshot.bm25_index.search(query_text, top_k=100)
                sem_raw = snapshot.semantic_index.search(query_text, top_k=100)

                bm25_alg = [
                    SearchResult(item_id=r.item_id, score=r.score, rank=r.rank or 0, source="bm25")
                    for r in bm25_raw
                ]
                sem_alg = [
                    SearchResult(
                        item_id=r.item_id, score=r.score, rank=r.rank or 0, source="semantic"
                    )
                    for r in sem_raw
                ]
                cand = build_candidates(bm25_alg, sem_alg)
                fused = fuse_linear(cand, bm25_weight=0.5, semantic_weight=0.5, top_k=100)
                all_results[qid] = fused
        finally:
            session.close()

        metrics = evaluate_all(all_results, queries_data, qrels_map, ks=ks)
        avg = macro_average(metrics)
        elapsed = time.monotonic() - t0

        return EvaluationReport(
            query_count=len(query_texts),
            metrics={"macro_average": avg},
            duration_seconds=round(elapsed, 2),
        )
