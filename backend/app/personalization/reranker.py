"""Personalized re-ranking of Linear Hybrid candidates.

Identical algorithm to PSR-SRS-MVP.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from app.personalization.profiles import UserProfile
from app.personalization.types import RankedItem


@dataclass
class PersonalizationConfig:
    """Typed configuration for personalized re-ranking."""

    train_ratio: float = 0.8
    event_weights: dict[str, float] = field(default_factory=lambda: {
        "click": 1.0, "favorite": 2.0, "add_to_cart": 3.0, "purchase": 5.0,
    })
    half_life_days: float = 30.0
    retrieval_weight: float = 0.70
    category_weight: float = 0.12
    subcategory_weight: float = 0.06
    brand_weight: float = 0.06
    price_weight: float = 0.06
    top_k_values: list[int] = field(default_factory=lambda: [5, 10, 20])
    behavior_relevance: dict[str, int] = field(default_factory=lambda: {
        "click": 1, "favorite": 2, "add_to_cart": 3, "purchase": 4,
    })

    @property
    def max_k(self) -> int:
        return max(self.top_k_values) if self.top_k_values else 20

    def validate(self) -> list[str]:
        """Return a list of validation errors (empty if valid)."""
        errors: list[str] = []
        if not (0 < self.train_ratio < 1):
            errors.append("train_ratio must be in (0, 1)")
        for etype, w in self.event_weights.items():
            if w < 0 or not math.isfinite(w):
                errors.append(f"event_weight.{etype} must be non-negative finite")
        if sum(1 for w in self.event_weights.values() if w > 0) == 0:
            errors.append("at least one event_weight must be > 0")
        if self.half_life_days <= 0:
            errors.append("half_life_days must be > 0")
        rw = self.retrieval_weight
        cw = self.category_weight
        sw = self.subcategory_weight
        bw = self.brand_weight
        pw = self.price_weight
        for name, w in [("retrieval", rw), ("category", cw), ("subcategory", sw),
                         ("brand", bw), ("price", pw)]:
            if w < 0 or not math.isfinite(w):
                errors.append(f"{name}_weight must be non-negative finite")
        total = rw + cw + sw + bw + pw
        if total <= 0:
            errors.append("sum of re-ranking weights must be > 0")
        if not self.top_k_values:
            errors.append("top_k_values must not be empty")
        for k in self.top_k_values:
            if k <= 0 or not isinstance(k, int):
                errors.append(f"top_k_values {k} invalid")
        for etype, g in self.behavior_relevance.items():
            if g < 1 or not isinstance(g, int):
                errors.append(f"behavior_relevance.{etype} must be positive int")
        if self.behavior_relevance.get("purchase", 0) < self.behavior_relevance.get("add_to_cart", 0):
            errors.append("purchase grade must be >= add_to_cart grade")
        if self.behavior_relevance.get("add_to_cart", 0) < self.behavior_relevance.get("favorite", 0):
            errors.append("add_to_cart grade must be >= favorite grade")
        if self.behavior_relevance.get("favorite", 0) < self.behavior_relevance.get("click", 0):
            errors.append("favorite grade must be >= click grade")
        return errors

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> PersonalizationConfig:
        """Create a validated config from a dictionary."""
        valid_keys = set(cls.__dataclass_fields__.keys())
        kwargs = {k: v for k, v in data.items() if k in valid_keys}
        cfg = cls(**kwargs)  # type: ignore[arg-type]
        errs = cfg.validate()
        if errs:
            raise ValueError("\n".join(errs))
        return cfg

    @classmethod
    def from_json(cls, path: str | Path) -> PersonalizationConfig:
        """Load config from a JSON file (convenience for offline scripts)."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)


def rerank_candidates(
    candidates: list[dict[str, str]],
    profile: UserProfile,
    items_map: dict[str, dict],
    config: PersonalizationConfig,
    behavior_grades: dict[str, int] | None = None,
    qrels: dict[str, int] | None = None,
) -> list[RankedItem]:
    """Re-rank Linear Hybrid candidates using personalized affinity scores.

    If the profile is cold-start, empty, or has no positive events,
    returns candidates in original retrieval order.

    Args:
        candidates: Fused result dicts with keys ``item_id``, ``rank``, ``fusion_score``.
        profile: The requesting user's ``UserProfile``.
        items_map: ``{item_id: {category, subcategory, brand, price, ...}}``.
        config: Personalization configuration.
        behavior_grades: Optional per-item behavior grades.
        qrels: Optional per-item qrels relevance grades.

    Returns:
        List of ``RankedItem`` sorted by personalized score descending.
    """
    if not candidates:
        return []

    # Normalize retrieval scores
    fscores = [float(c["fusion_score"]) for c in candidates]
    fmin, fmax = min(fscores), max(fscores)
    norms = (
        [(s - fmin) / (fmax - fmin) for s in fscores]
        if fmax > fmin
        else [1.0] * len(fscores)
    )

    # Normalize reranking weights
    total_w = (config.retrieval_weight + config.category_weight +
               config.subcategory_weight + config.brand_weight + config.price_weight)
    wr = config.retrieval_weight / total_w
    wc = config.category_weight / total_w
    ws = config.subcategory_weight / total_w
    wb = config.brand_weight / total_w
    wp = config.price_weight / total_w

    # Deduplicate by item_id (keep first occurrence by original rank)
    seen: set[str] = set()
    unique_candidates = []
    for c in sorted(candidates, key=lambda c: int(c.get("rank", "999"))):
        if c["item_id"] not in seen:
            seen.add(c["item_id"])
            unique_candidates.append(c)

    scored: list[tuple[float, int, float, float, float, float, float, int, int]] = []
    for i, c in enumerate(unique_candidates):
        iid = c["item_id"]
        item = items_map.get(iid, {})
        cat = item.get("category", "")
        subcat = item.get("subcategory", "")
        brand = item.get("brand", "")

        # Affinities
        cat_aff = profile.category_weights.get(cat, 0.0)
        sub_aff = profile.subcategory_weights.get(subcat, 0.0)
        brand_aff = profile.brand_weights.get(brand, 0.0)

        # Price affinity
        price_aff = 0.0
        if profile.mean_log_price is not None:
            try:
                price = float(item.get("price", 0))
            except (ValueError, TypeError):
                price = 0
            if price > 0:
                dist = abs(math.log(price) - profile.mean_log_price)
                scale = max(profile.price_std, 0.1)
                price_aff = math.exp(-dist / scale)

        # Cold-start / empty → use original retrieval order
        if profile.profile_status in ("cold_start", "no_history", "empty", "no_positive"):
            pscore = norms[i]
            cat_aff = sub_aff = brand_aff = price_aff = 0.0
        else:
            pscore = wr * norms[i] + wc * cat_aff + ws * sub_aff + wb * brand_aff + wp * price_aff

        behavior_g = (behavior_grades or {}).get(iid, 0)
        qrels_g = (qrels or {}).get(iid, 0)

        scored.append((pscore, i, cat_aff, sub_aff, brand_aff, price_aff, norms[i],
                       behavior_g, qrels_g))

    # Sort: personalized_score descending, then original_rank ascending, then item_id ascending
    scored.sort(key=lambda x: (-x[0], int(candidates[x[1]]["rank"]), candidates[x[1]]["item_id"]))

    results = []
    for rank, (pscore, idx, ca, sa, ba, pa, nrs, bg, qg) in enumerate(scored, start=1):
        c = candidates[idx]
        results.append(RankedItem(
            item_id=c["item_id"],
            rank=rank,
            original_rank=int(c["rank"]),
            original_fusion_score=float(c["fusion_score"]),
            normalized_retrieval_score=nrs,
            category_affinity=ca,
            subcategory_affinity=sa,
            brand_affinity=ba,
            price_affinity=pa,
            personalized_score=pscore,
            profile_status=profile.profile_status,
            is_cold_start=profile.is_cold_start,
            behavior_relevance_grade=bg,
            qrels_relevance_grade=qg,
        ))
    return results
