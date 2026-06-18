"""MVP vs Enterprise algorithm parity verification — subprocess isolation.

Runs Enterprise and MVP algorithms in separate subprocesses, compares
JSON outputs with explicit tolerances.

Exit code 0 = passed, non-zero = unexpected differences or failures.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ABS_TOL = 1e-6
REL_TOL = 1e-6
SUBPROCESS_TIMEOUT = 60  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_enterprise(python_exe: str, fixture_path: str) -> tuple[int, str, str]:
    """Run Enterprise algorithms via subprocess."""
    runner = Path(__file__).resolve().parent / "parity" / "run_enterprise_case.py"
    proc = subprocess.run(
        [python_exe, str(runner), "--fixture", fixture_path],
        capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _run_mvp(python_exe: str, mvp_root: str, fixture_path: str) -> tuple[int, str, str]:
    """Run MVP algorithms via subprocess using an auto-generated runner script."""
    import textwrap

    mvp_runner = textwrap.dedent(f"""\
import importlib.util
import json
import sys
from pathlib import Path

MVP_SRC = Path(r"{mvp_root}") / "src"

def _load(mod_path):
    file_part = mod_path.replace(".", "/") + ".py"
    full_path = str(MVP_SRC / file_part)
    spec = importlib.util.spec_from_file_location(
        mod_path.replace("/", ".").replace("\\\\", "."),
        full_path
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules[mod_path] = m
    spec.loader.exec_module(m)
    return m

fixture = json.loads(Path(r"{fixture_path}").read_text(encoding="utf-8"))

# -- Tokenization --
tok_mod = _load("psr_srs_mvp.retrieval.tokenization")
tok_results = []
for case in fixture.get("tokenization", []):
    tokens = tok_mod.tokenize(case["text"], remove_stopwords=case["remove_stopwords"])
    tok_results.append({{"input": case["text"], "tokens": tokens}})
for case in fixture.get("build_item_text", []):
    w = case.pop("weights", None)
    text = tok_mod.build_item_text(**case, weights=w)
    tok_results.append({{"input": str(case), "built_text": text}})

# -- BM25 --
bm25_mod = _load("psr_srs_mvp.retrieval.bm25")
bm25_cfg = fixture["bm25"]
docs = [bm25_mod.Document(item_id=iid, tokens=bm25_mod.tokenize(text), length=len(bm25_mod.tokenize(text))) for iid, text in bm25_cfg["documents"]]
bm25_idx = bm25_mod.BM25Index.build(docs, k1=bm25_cfg["k1"], b=bm25_cfg["b"])
bm25_queries = {{}}
for q in bm25_cfg["queries"]:
    results = bm25_idx.search(q["query"], top_k=q["top_k"])
    bm25_queries[q["query"]] = [{{"item_id": r.item_id, "score": round(r.score, 10), "rank": r.rank}} for r in results]
bm25_result = {{"vocabulary_size": bm25_idx.vocabulary_size, "queries": bm25_queries}}

# -- Semantic --
vec_mod = _load("psr_srs_mvp.retrieval.vectorization")
sem_mod = _load("psr_srs_mvp.retrieval.semantic")
sem_cfg = fixture["semantic"]
config = vec_mod.SemanticConfig(**sem_cfg["config"])
ids = [f"item_{{i}}" for i in range(len(sem_cfg["documents"]))]
sem_idx = sem_mod.SemanticIndex.build(sem_cfg["documents"], ids, config)
sem_queries = {{}}
for q in sem_cfg["queries"]:
    results = sem_idx.search(q["query"], top_k=q["top_k"])
    sem_queries[q["query"]] = [{{"item_id": r.item_id, "score": round(r.score, 10), "rank": r.rank}} for r in results]
sem_result = {{"document_count": sem_idx.document_count, "queries": sem_queries}}

# -- Fusion --
fus_mod = _load("psr_srs_mvp.retrieval.fusion")
fus_cfg = fixture["fusion"]
def _make_mvp_results(items, cls_name):
    cls = bm25_mod.SearchResult if cls_name == "bm25" else sem_mod.SemanticSearchResult
    return [cls(score=score, item_id=iid, rank=rank) for iid, score, rank in items]
bm25_r = _make_mvp_results(fus_cfg["bm25"], "bm25")
sem_r = _make_mvp_results(fus_cfg["semantic"], "semantic")
cand = fus_mod.build_candidates(bm25_r, sem_r)
rrf = fus_mod.fuse_rrf(cand, fus_cfg["rrf_k"], fus_cfg["top_k"])
linear = fus_mod.fuse_linear(cand, fus_cfg["bm25_weight"], fus_cfg["semantic_weight"], fus_cfg["top_k"])
fus_result = {{
    "rrf": [{{"item_id": r.item_id, "fusion_score": round(r.fusion_score, 10), "rank": r.rank}} for r in rrf],
    "linear": [{{"item_id": r.item_id, "fusion_score": round(r.fusion_score, 10), "rank": r.rank}} for r in linear],
}}

# -- Profiles --
prof_mod = _load("psr_srs_mvp.personalization.profiles")
prof_cfg = fixture["profiles"]
profiles = prof_mod.build_profiles(
    prof_cfg["train_events"], prof_cfg["items"], prof_cfg["users_map"],
    prof_cfg["event_weights"], prof_cfg["half_life_days"],
)
prof_result = {{}}
for uid, p in profiles.items():
    prof_result[uid] = {{
        "profile_status": p.profile_status,
        "positive_event_count": p.positive_event_count,
        "category_weights": dict(p.category_weights),
        "brand_weights": dict(p.brand_weights),
        "mean_log_price": round(p.mean_log_price, 10) if p.mean_log_price is not None else None,
    }}

output = {{
    "tokenization": tok_results,
    "bm25": bm25_result,
    "semantic": sem_result,
    "fusion": fus_result,
    "profiles": prof_result,
}}
print(json.dumps(output, ensure_ascii=False))
""")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8",
    ) as f:
        f.write(mvp_runner)
        tmp_path = f.name

    try:
        proc = subprocess.run(
            [python_exe, tmp_path],
            capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _compare_tokenization(ent: Any, mvp: Any, checks: dict, diffs: list):
    if ent == mvp:
        checks["tokenization"] = {"parity": "pass", "detail": "Tokenization outputs match"}
    else:
        checks["tokenization"] = {"parity": "diff", "enterprise": ent, "mvp": mvp}
        diffs.append("tokenization")


def _compare_bm25(ent: dict, mvp: dict, checks: dict, diffs: list):
    ent_queries = ent.get("queries", {})
    mvp_queries = mvp.get("queries", {})

    all_match = True
    details = {}
    for q in ent_queries:
        e_items = [r["item_id"] for r in ent_queries[q]]
        m_items = [r["item_id"] for r in mvp_queries.get(q, [])]
        if e_items != m_items:
            all_match = False
            diffs.append(f"bm25 ranking: {q}")
        e_scores = [r["score"] for r in ent_queries[q]]
        m_scores = [r["score"] for r in mvp_queries.get(q, [])]
        for i, (es, ms) in enumerate(zip(e_scores, m_scores)):
            if not math.isclose(es, ms, rel_tol=REL_TOL, abs_tol=ABS_TOL):
                all_match = False
                diffs.append(f"bm25 score: {q} rank {i} → ent={es} mvp={ms}")
        details[q] = {"ent_items": e_items, "mvp_items": m_items}

    checks["bm25"] = {
        "parity": "pass" if all_match else "diff",
        "details": details,
    }


def _compare_semantic(ent: dict, mvp: dict, checks: dict, diffs: list):
    ent_queries = ent.get("queries", {})
    mvp_queries = mvp.get("queries", {})

    all_match = True
    for q in ent_queries:
        e_items = [r["item_id"] for r in ent_queries[q]]
        m_items = [r["item_id"] for r in mvp_queries.get(q, [])]
        if e_items != m_items:
            all_match = False
            diffs.append(f"semantic ranking: {q}")

    checks["semantic"] = {"parity": "pass" if all_match else "diff"}


def _compare_fusion(ent: dict, mvp: dict, checks: dict, diffs: list):
    all_match = True
    for method in ("rrf", "linear"):
        e_items = [r["item_id"] for r in ent.get(method, [])]
        m_items = [r["item_id"] for r in mvp.get(method, [])]
        if e_items != m_items:
            all_match = False
            diffs.append(f"fusion {method}")

    checks["fusion"] = {"parity": "pass" if all_match else "diff"}


def _compare_profiles(ent: dict, mvp: dict, checks: dict, diffs: list):
    all_match = True
    for uid in ent:
        ep = ent[uid]
        mp = mvp.get(uid, {})
        if ep.get("profile_status") != mp.get("profile_status"):
            all_match = False
            diffs.append(f"profile status: {uid}")
        if ep.get("positive_event_count") != mp.get("positive_event_count"):
            all_match = False
            diffs.append(f"profile count: {uid}")

    checks["profiles"] = {"parity": "pass" if all_match else "diff"}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="MVP-Enterprise algorithm parity verification"
    )
    parser.add_argument("--mvp-root", required=True)
    parser.add_argument("--enterprise-root", required=True)
    parser.add_argument("--output", default="outputs/e1_parity_report.json")
    args = parser.parse_args()

    python_exe = sys.executable
    fixture_path = str(
        Path(__file__).resolve().parent / "parity" / "parity_fixture.json"
    )

    # Run Enterprise
    ent_code, ent_out, ent_err = _run_enterprise(python_exe, fixture_path)

    # Run MVP
    mvp_code, mvp_out, mvp_err = _run_mvp(python_exe, args.mvp_root, fixture_path)

    report: dict[str, Any] = {
        "status": "unknown",
        "mvp_root": args.mvp_root,
        "enterprise_root": args.enterprise_root,
        "tolerances": {"absolute": ABS_TOL, "relative": REL_TOL},
        "subprocesses": {
            "mvp_return_code": mvp_code,
            "enterprise_return_code": ent_code,
        },
        "checks": {},
        "unexpected_differences": [],
    }

    # Parse outputs
    ent_data: dict = {}
    mvp_data: dict = {}

    if ent_code == 0 and ent_out:
        try:
            ent_data = json.loads(ent_out)
        except json.JSONDecodeError:
            report["subprocesses"]["enterprise_error"] = "invalid JSON"
    else:
        report["subprocesses"]["enterprise_stderr"] = ent_err[:500]

    if mvp_code == 0 and mvp_out:
        try:
            mvp_data = json.loads(mvp_out)
        except json.JSONDecodeError:
            report["subprocesses"]["mvp_error"] = "invalid JSON"
    else:
        report["subprocesses"]["mvp_stderr"] = mvp_err[:500]

    # Compare if both succeeded
    diffs: list[str] = []
    if ent_data and mvp_data:
        _compare_tokenization(
            ent_data.get("tokenization"), mvp_data.get("tokenization"),
            report["checks"], diffs,
        )
        _compare_bm25(
            ent_data.get("bm25", {}), mvp_data.get("bm25", {}),
            report["checks"], diffs,
        )
        _compare_semantic(
            ent_data.get("semantic", {}), mvp_data.get("semantic", {}),
            report["checks"], diffs,
        )
        _compare_fusion(
            ent_data.get("fusion", {}), mvp_data.get("fusion", {}),
            report["checks"], diffs,
        )
        _compare_profiles(
            ent_data.get("profiles", {}), mvp_data.get("profiles", {}),
            report["checks"], diffs,
        )
    else:
        diffs.append("subprocess_failure")
        report["checks"]["subprocess"] = {
            "parity": "missing",
            "enterprise_ok": bool(ent_data),
            "mvp_ok": bool(mvp_data),
        }

    report["unexpected_differences"] = diffs

    if not diffs and ent_code == 0 and mvp_code == 0:
        report["status"] = "passed"
    else:
        report["status"] = "failed"

    # Write report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    print(f"Parity report → {output_path}")
    print(f"Status: {report['status']}")
    print(f"Unexpected differences: {len(diffs)}")

    if diffs:
        for d in diffs:
            print(f"  - {d}")

    sys.exit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
