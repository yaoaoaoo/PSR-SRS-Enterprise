"""Comprehensive config validation tests for all four config dataclasses.

Covers every validation branch to push coverage >= 90%.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from app.personalization.reranker import PersonalizationConfig
from app.retrieval.bm25 import BM25Config
from app.retrieval.fusion import FusionConfig
from app.retrieval.vectorization import SemanticConfig

# ============================================================================
# BM25Config
# ============================================================================

class TestBM25ConfigValidation:
    def test_valid_default(self):
        errs = BM25Config().validate()
        assert errs == []

    def test_k1_zero(self):
        errs = BM25Config(k1=0).validate()
        assert any("k1" in e for e in errs)

    def test_b_out_of_range_high(self):
        errs = BM25Config(b=1.5).validate()
        assert any("b" in e for e in errs)

    def test_b_out_of_range_low(self):
        errs = BM25Config(b=-0.1).validate()
        assert any("b" in e for e in errs)

    def test_empty_top_k_values(self):
        errs = BM25Config(top_k_values=[]).validate()
        assert any("top_k_values" in e for e in errs)

    def test_non_positive_top_k(self):
        errs = BM25Config(top_k_values=[0]).validate()
        assert any("top_k_values" in e for e in errs)

    def test_invalid_relevance_threshold(self):
        errs = BM25Config(relevance_threshold=5).validate()
        assert any("relevance_threshold" in e for e in errs)

    def test_empty_field_weights(self):
        errs = BM25Config(field_weights={}).validate()
        assert any("field_weights" in e for e in errs)

    def test_all_field_weights_zero(self):
        errs = BM25Config(field_weights={"title": 0}).validate()
        assert any("field" in e for e in errs)

    def test_from_json_bad_path(self):
        with pytest.raises(FileNotFoundError):
            BM25Config.from_json("/nonexistent/path.json")


# ============================================================================
# SemanticConfig
# ============================================================================

class TestSemanticConfigValidation:
    def test_valid_default(self):
        errs = SemanticConfig().validate()
        assert errs == []

    def test_word_ngram_single_element(self):
        errs = SemanticConfig(word_ngram_range=[1]).validate()
        assert any("word_ngram" in e for e in errs)

    def test_word_ngram_min_gt_max(self):
        errs = SemanticConfig(word_ngram_range=[3, 1]).validate()
        assert any("word_ngram" in e for e in errs)

    def test_word_ngram_non_positive(self):
        errs = SemanticConfig(word_ngram_range=[0, 2]).validate()
        assert any("word_ngram" in e for e in errs)

    def test_char_ngram_single_element(self):
        errs = SemanticConfig(char_ngram_range=[3]).validate()
        assert any("char_ngram" in e for e in errs)

    def test_char_ngram_min_gt_max(self):
        errs = SemanticConfig(char_ngram_range=[5, 2]).validate()
        assert any("char_ngram" in e for e in errs)

    def test_both_weights_zero(self):
        errs = SemanticConfig(word_weight=0.0, char_weight=0.0).validate()
        assert any("weight" in e for e in errs)

    def test_negative_word_weight(self):
        errs = SemanticConfig(word_weight=-0.5).validate()
        assert any("weight" in e for e in errs)

    def test_negative_char_weight(self):
        errs = SemanticConfig(char_weight=-0.5).validate()
        assert any("weight" in e for e in errs)

    def test_svd_components_too_small(self):
        errs = SemanticConfig(svd_components=1).validate()
        assert any("svd_components" in e for e in errs)

    def test_non_int_random_state(self):
        errs = SemanticConfig(random_state=1.5).validate()  # type: ignore[arg-type]
        assert any("random_state" in e for e in errs)

    def test_empty_top_k_values(self):
        errs = SemanticConfig(top_k_values=[]).validate()
        assert any("top_k_values" in e for e in errs)

    def test_non_positive_top_k(self):
        errs = SemanticConfig(top_k_values=[0]).validate()
        assert any("top_k_values" in e for e in errs)

    def test_invalid_relevance_threshold(self):
        errs = SemanticConfig(relevance_threshold=0).validate()
        assert any("relevance_threshold" in e for e in errs)

    def test_min_df_zero(self):
        errs = SemanticConfig(min_df=0).validate()
        assert any("min_df" in e for e in errs)

    def test_max_df_out_of_range(self):
        errs = SemanticConfig(max_df=0.0).validate()
        assert any("max_df" in e for e in errs)

    def test_max_df_exceeds_one(self):
        errs = SemanticConfig(max_df=1.5).validate()
        assert any("max_df" in e for e in errs)


# ============================================================================
# FusionConfig
# ============================================================================

class TestFusionConfigValidation:
    def test_valid_default(self):
        errs = FusionConfig().validate()
        assert errs == []

    def test_candidate_k_zero(self):
        errs = FusionConfig(candidate_k=0).validate()
        assert any("candidate_k" in e for e in errs)

    def test_candidate_k_less_than_max_k(self):
        errs = FusionConfig(candidate_k=5, top_k_values=[10, 20]).validate()
        assert any("candidate_k" in e for e in errs)

    def test_empty_top_k_values(self):
        errs = FusionConfig(top_k_values=[]).validate()
        assert any("top_k_values" in e for e in errs)

    def test_non_positive_top_k(self):
        errs = FusionConfig(top_k_values=[0]).validate()
        assert any("top_k_values" in e for e in errs)

    def test_rrf_k_zero(self):
        errs = FusionConfig(rrf_k=0).validate()
        assert any("rrf_k" in e for e in errs)

    def test_bm25_weight_negative(self):
        errs = FusionConfig(bm25_weight=-0.1).validate()
        assert any("bm25_weight" in e for e in errs)

    def test_semantic_weight_negative(self):
        errs = FusionConfig(semantic_weight=-0.1).validate()
        assert any("semantic_weight" in e for e in errs)

    def test_both_weights_zero(self):
        errs = FusionConfig(bm25_weight=0.0, semantic_weight=0.0).validate()
        assert any("weight" in e for e in errs)

    def test_invalid_normalization(self):
        errs = FusionConfig(score_normalization="z_score").validate()
        assert any("score_normalization" in e for e in errs)

    def test_invalid_relevance_threshold(self):
        errs = FusionConfig(relevance_threshold=4).validate()
        assert any("relevance_threshold" in e for e in errs)


# ============================================================================
# PersonalizationConfig
# ============================================================================

class TestPersonalizationConfigValidation:
    def test_valid_default(self):
        errs = PersonalizationConfig().validate()
        assert errs == []

    def test_train_ratio_zero(self):
        errs = PersonalizationConfig(train_ratio=0.0).validate()
        assert any("train_ratio" in e for e in errs)

    def test_train_ratio_one(self):
        errs = PersonalizationConfig(train_ratio=1.0).validate()
        assert any("train_ratio" in e for e in errs)

    def test_negative_event_weight(self):
        errs = PersonalizationConfig(event_weights={"click": -1.0}).validate()
        assert any("event_weight" in e for e in errs)

    def test_all_event_weights_zero(self):
        errs = PersonalizationConfig(
            event_weights={"click": 0.0, "purchase": 0.0}
        ).validate()
        assert any("event_weight" in e for e in errs)

    def test_half_life_zero(self):
        errs = PersonalizationConfig(half_life_days=0).validate()
        assert any("half_life_days" in e for e in errs)

    def test_negative_retrieval_weight(self):
        errs = PersonalizationConfig(retrieval_weight=-0.1).validate()
        assert any("retrieval_weight" in e for e in errs)

    def test_all_rerank_weights_zero(self):
        errs = PersonalizationConfig(
            retrieval_weight=0, category_weight=0,
            subcategory_weight=0, brand_weight=0, price_weight=0,
        ).validate()
        assert any("weight" in e for e in errs)

    def test_empty_top_k_values(self):
        errs = PersonalizationConfig(top_k_values=[]).validate()
        assert any("top_k_values" in e for e in errs)

    def test_non_positive_top_k(self):
        errs = PersonalizationConfig(top_k_values=[0]).validate()
        assert any("top_k_values" in e for e in errs)

    def test_negative_behavior_relevance(self):
        errs = PersonalizationConfig(behavior_relevance={"click": -1}).validate()
        assert any("behavior_relevance" in e for e in errs)

    def test_behavior_grade_order_click_gt_favorite(self):
        errs = PersonalizationConfig(
            behavior_relevance={"click": 5, "favorite": 2, "add_to_cart": 6, "purchase": 7}
        ).validate()
        assert any("favorite" in e for e in errs)

    def test_behavior_grade_order_add_to_cart_gt_purchase(self):
        errs = PersonalizationConfig(
            behavior_relevance={"click": 1, "favorite": 2, "add_to_cart": 8, "purchase": 3}
        ).validate()
        assert any("purchase" in e for e in errs)

    def test_from_json_roundtrip(self):
        data = {"half_life_days": 15, "retrieval_weight": 0.60}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            cfg = PersonalizationConfig.from_json(path)
            assert cfg.half_life_days == 15
            assert cfg.retrieval_weight == 0.60
        finally:
            Path(path).unlink()
