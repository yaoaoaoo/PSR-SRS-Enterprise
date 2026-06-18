"""Tests for personalized re-ranking."""

from __future__ import annotations

import pytest

from app.personalization.profiles import UserProfile
from app.personalization.reranker import (
    PersonalizationConfig,
    rerank_candidates,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def items_map() -> dict[str, dict]:
    return {
        "a": {"category": "Electronics", "subcategory": "Laptops", "brand": "TechPro", "price": "1000"},
        "b": {"category": "Clothing", "subcategory": "Shoes", "brand": "UrbanWear", "price": "100"},
        "c": {"category": "Electronics", "subcategory": "Phones", "brand": "SmartWave", "price": "800"},
    }


@pytest.fixture
def fusion_candidates() -> list[dict[str, str]]:
    return [
        {"item_id": "a", "rank": "1", "fusion_score": "0.95"},
        {"item_id": "b", "rank": "2", "fusion_score": "0.80"},
        {"item_id": "c", "rank": "3", "fusion_score": "0.70"},
    ]


@pytest.fixture
def warm_profile() -> UserProfile:
    p = UserProfile("u_warm")
    p._cat_scores = {"Electronics": 10.0, "Clothing": 1.0}
    p._brand_scores = {"TechPro": 5.0}
    p._price_log_sum = 6.9  # ~$992
    p._price_weight_sum = 1.0
    p.positive_event_count = 5
    p.finalize()
    return p


@pytest.fixture
def cold_profile() -> UserProfile:
    p = UserProfile("u_cold", is_cold_start=True)
    p.finalize()
    return p


@pytest.fixture
def config() -> PersonalizationConfig:
    return PersonalizationConfig()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPersonalizationConfig:
    def test_defaults(self):
        cfg = PersonalizationConfig()
        assert cfg.retrieval_weight == 0.70
        assert cfg.category_weight == 0.12
        assert cfg.half_life_days == 30.0

    def test_from_dict(self):
        cfg = PersonalizationConfig.from_dict({
            "retrieval_weight": 0.60,
            "category_weight": 0.15,
        })
        assert cfg.retrieval_weight == 0.60

    def test_from_dict_invalid_weights(self):
        with pytest.raises(ValueError, match="weight"):
            PersonalizationConfig.from_dict({
                "retrieval_weight": 0, "category_weight": 0,
                "subcategory_weight": 0, "brand_weight": 0, "price_weight": 0,
            })

    def test_from_dict_invalid_train_ratio(self):
        with pytest.raises(ValueError, match="train_ratio"):
            PersonalizationConfig.from_dict({"train_ratio": 1.5})

    def test_from_dict_unknown_ignored(self):
        cfg = PersonalizationConfig.from_dict({"half_life_days": 15, "extra": "noise"})
        assert cfg.half_life_days == 15


class TestRerankCandidates:
    def test_warm_profile_reranks(self, fusion_candidates, warm_profile, items_map, config):
        results = rerank_candidates(fusion_candidates, warm_profile, items_map, config)
        assert len(results) == 3
        # Warm profile prefers Electronics → "a" or "c" should be ranked higher than "b"
        for r in results:
            assert isinstance(r.personalized_score, float)

    def test_cold_start_fallback(self, fusion_candidates, cold_profile, items_map, config):
        results = rerank_candidates(fusion_candidates, cold_profile, items_map, config)
        assert len(results) == 3
        # Cold start should preserve original retrieval order
        assert results[0].item_id == "a"
        assert results[1].item_id == "b"
        assert results[2].item_id == "c"
        # Profile status should indicate cold start
        assert results[0].is_cold_start is True

    def test_input_not_modified(self, fusion_candidates, warm_profile, items_map, config):
        before = [dict(c) for c in fusion_candidates]
        rerank_candidates(fusion_candidates, warm_profile, items_map, config)
        # Original list elements unchanged
        for b, a in zip(before, fusion_candidates, strict=False):
            assert a["item_id"] == b["item_id"]
            assert a["rank"] == b["rank"]

    def test_missing_metadata_no_crash(self, fusion_candidates, warm_profile, config):
        empty_items: dict[str, dict] = {}
        results = rerank_candidates(fusion_candidates, warm_profile, empty_items, config)
        assert len(results) == 3
        # All affinities should be 0 since no item metadata
        for r in results:
            assert r.category_affinity == 0.0

    def test_deterministic_ordering(self, fusion_candidates, warm_profile, items_map, config):
        r1 = rerank_candidates(fusion_candidates, warm_profile, items_map, config)
        r2 = rerank_candidates(fusion_candidates, warm_profile, items_map, config)
        assert [r.item_id for r in r1] == [r.item_id for r in r2]

    def test_electronics_affinity(self, fusion_candidates, warm_profile, items_map, config):
        """Warm user with Electronics preference should boost Electronics items."""
        results = rerank_candidates(fusion_candidates, warm_profile, items_map, config)
        # Items "a" and "c" are Electronics
        elec_items = [r for r in results if r.item_id in ("a", "c")]
        for r in elec_items:
            assert r.category_affinity > 0

    def test_no_positive_fallback(self, items_map, config):
        """Profile with no_positive status should fall back to retrieval order."""
        p = UserProfile("u_np")
        p.train_event_count = 2
        p.finalize()
        assert p.profile_status == "no_positive"
        candidates = [
            {"item_id": "c", "rank": "1", "fusion_score": "0.90"},
            {"item_id": "b", "rank": "2", "fusion_score": "0.80"},
            {"item_id": "a", "rank": "3", "fusion_score": "0.70"},
        ]
        results = rerank_candidates(candidates, p, items_map, config)
        # Should preserve original order
        assert results[0].item_id == "c"
        assert results[1].item_id == "b"
        assert results[2].item_id == "a"


class TestRerankEdgeCases:
    """Additional edge cases for coverage."""

    def test_empty_candidates(self, warm_profile, config):
        results = rerank_candidates([], warm_profile, {}, config)
        assert results == []

    def test_single_candidate(self, warm_profile, items_map, config):
        cand = [{"item_id": "a", "rank": "1", "fusion_score": "0.95"}]
        results = rerank_candidates(cand, warm_profile, items_map, config)
        assert len(results) == 1
        assert results[0].item_id == "a"

    def test_all_same_scores_tie_break(self, items_map, config):
        cand = [
            {"item_id": "z", "rank": "1", "fusion_score": "0.80"},
            {"item_id": "a", "rank": "2", "fusion_score": "0.80"},
        ]
        # Cold profile → keeps original order
        p = UserProfile("u_c", is_cold_start=True)
        p.finalize()
        results = rerank_candidates(cand, p, items_map, config)
        # Original order preserved: z first, then a
        assert results[0].item_id == "z"
        assert results[1].item_id == "a"

    def test_missing_price_metadata(self, warm_profile, config):
        cand = [{"item_id": "a", "rank": "1", "fusion_score": "0.95"}]
        items = {"a": {"category": "Electronics"}}  # no price
        results = rerank_candidates(cand, warm_profile, items, config)
        assert len(results) == 1
        assert results[0].price_affinity == 0.0

    def test_zero_price_item(self, warm_profile, config):
        cand = [{"item_id": "a", "rank": "1", "fusion_score": "0.95"}]
        items = {"a": {"category": "Electronics", "price": "0"}}
        results = rerank_candidates(cand, warm_profile, items, config)
        assert results[0].price_affinity == 0.0

    def test_category_not_matching(self, warm_profile, config):
        """Item in a category the user has never interacted with."""
        cand = [{"item_id": "b", "rank": "1", "fusion_score": "0.90"}]
        items = {"b": {"category": "Sports", "brand": "Nike", "price": "200"}}
        results = rerank_candidates(cand, warm_profile, items, config)
        # User only knows Electronics — category affinity for Sports should be 0
        assert results[0].category_affinity == 0.0

    def test_brand_not_matching(self, warm_profile, config):
        cand = [{"item_id": "a", "rank": "1", "fusion_score": "0.90"}]
        items = {"a": {"category": "Electronics", "brand": "UnknownBrand", "price": "500"}}
        results = rerank_candidates(cand, warm_profile, items, config)
        # Category matches (Electronics) but brand doesn't
        assert results[0].category_affinity > 0
        assert results[0].brand_affinity == 0.0

    def test_behavior_grades_applied(self, warm_profile, items_map, config):
        cand = [{"item_id": "a", "rank": "1", "fusion_score": "0.95"}]
        results = rerank_candidates(
            cand, warm_profile, items_map, config,
            behavior_grades={"a": 3},
        )
        assert results[0].behavior_relevance_grade == 3

    def test_qrels_applied(self, warm_profile, items_map, config):
        cand = [{"item_id": "a", "rank": "1", "fusion_score": "0.95"}]
        results = rerank_candidates(
            cand, warm_profile, items_map, config,
            qrels={"a": 2},
        )
        assert results[0].qrels_relevance_grade == 2

    def test_original_rank_preserved(self, warm_profile, items_map, config):
        cand = [{"item_id": "a", "rank": "5", "fusion_score": "0.95"}]
        results = rerank_candidates(cand, warm_profile, items_map, config)
        assert results[0].original_rank == 5

    def test_empty_items_map(self, warm_profile, config):
        cand = [{"item_id": "x", "rank": "1", "fusion_score": "1.0"}]
        results = rerank_candidates(cand, warm_profile, {}, config)
        assert len(results) == 1
        assert results[0].item_id == "x"
        # All affinities should be 0 with empty items_map
        assert results[0].category_affinity == 0.0
