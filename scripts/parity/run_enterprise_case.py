"""Subprocess runner — Enterprise algorithms only.

Reads a parity fixture from stdin (or --fixture path), runs all checks,
writes JSON to stdout.

Usage::

    python run_enterprise_case.py --fixture parity_fixture.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def run_tokenization(fixture: dict) -> list[dict]:
    from app.retrieval.tokenization import build_item_text, tokenize

    results = []
    for case in fixture.get("tokenization", []):
        tok = tokenize(case["text"], remove_stopwords=case["remove_stopwords"])
        results.append({"input": case["text"], "tokens": tok})

    for case in fixture.get("build_item_text", []):
        w = case.pop("weights", None)
        text = build_item_text(**case, weights=w)
        results.append({"input": str(case), "built_text": text})

    return results


def run_bm25(fixture: dict) -> dict:
    from app.retrieval.bm25 import BM25Index

    cfg = fixture["bm25"]
    docs = [(iid, text) for iid, text in cfg["documents"]]
    idx = BM25Index.build(docs, k1=cfg["k1"], b=cfg["b"])

    query_results = {}
    for q in cfg["queries"]:
        results = idx.search(q["query"], top_k=q["top_k"])
        query_results[q["query"]] = [
            {"item_id": r.item_id, "score": round(r.score, 10), "rank": r.rank}
            for r in results
        ]

    return {"vocabulary_size": idx.vocabulary_size, "queries": query_results}


def run_semantic(fixture: dict) -> dict:
    from app.retrieval.semantic import SemanticIndex
    from app.retrieval.vectorization import SemanticConfig

    cfg = fixture["semantic"]
    config = SemanticConfig.from_dict(cfg["config"])
    ids = [f"item_{i}" for i in range(len(cfg["documents"]))]
    idx = SemanticIndex.build(cfg["documents"], ids, config)

    query_results = {}
    for q in cfg["queries"]:
        results = idx.search(q["query"], top_k=q["top_k"])
        query_results[q["query"]] = [
            {"item_id": r.item_id, "score": round(r.score, 10), "rank": r.rank}
            for r in results
        ]

    return {"document_count": idx.document_count, "vector_dim": idx.vector_dim, "queries": query_results}


def run_fusion(fixture: dict) -> dict:
    from app.retrieval.fusion import build_candidates, fuse_linear, fuse_rrf
    from app.retrieval.types import SearchResult

    cfg = fixture["fusion"]

    def make_results(items, source):
        return [
            SearchResult(item_id=iid, score=score, rank=rank, source=source)
            for iid, score, rank in items
        ]

    bm25 = make_results(cfg["bm25"], "bm25")
    sem = make_results(cfg["semantic"], "semantic")
    cand = build_candidates(bm25, sem)

    rrf = fuse_rrf(cand, cfg["rrf_k"], cfg["top_k"])
    linear = fuse_linear(cand, cfg["bm25_weight"], cfg["semantic_weight"], cfg["top_k"])

    return {
        "rrf": [{"item_id": r.item_id, "fusion_score": round(r.fusion_score, 10), "rank": r.rank} for r in rrf],
        "linear": [{"item_id": r.item_id, "fusion_score": round(r.fusion_score, 10), "rank": r.rank} for r in linear],
    }


def run_profiles(fixture: dict) -> dict:
    from app.personalization.profiles import build_profiles

    cfg = fixture["profiles"]
    profiles = build_profiles(
        cfg["train_events"], cfg["items"], cfg["users_map"],
        cfg["event_weights"], cfg["half_life_days"],
    )

    result = {}
    for uid, p in profiles.items():
        result[uid] = {
            "profile_status": p.profile_status,
            "is_cold_start": p.is_cold_start,
            "positive_event_count": p.positive_event_count,
            "category_weights": dict(p.category_weights),
            "brand_weights": dict(p.brand_weights),
            "mean_log_price": round(p.mean_log_price, 10) if p.mean_log_price is not None else None,
        }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True, help="Path to parity fixture JSON")
    args = parser.parse_args()

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))

    report = {
        "tokenization": run_tokenization(fixture),
        "bm25": run_bm25(fixture),
        "semantic": run_semantic(fixture),
        "fusion": run_fusion(fixture),
        "profiles": run_profiles(fixture),
    }

    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
