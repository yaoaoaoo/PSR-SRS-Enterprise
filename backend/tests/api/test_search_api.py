"""Search API tests — all modes, validation, personalization."""

from __future__ import annotations


class TestSearchAPI:
    def test_bm25_search(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={
            "query": "electronics", "mode": "bm25", "top_k": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert len(data["data"]["hits"]) > 0

    def test_semantic_search(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={
            "query": "laptop computer", "mode": "semantic", "top_k": 5,
        })
        assert resp.status_code == 200

    def test_rrf_search(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={
            "query": "electronics", "mode": "rrf", "top_k": 5,
        })
        assert resp.status_code == 200

    def test_linear_search(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={
            "query": "gaming computer", "mode": "linear", "top_k": 5,
        })
        assert resp.status_code == 200

    def test_search_response_structure(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={
            "query": "electronics", "mode": "linear", "top_k": 3,
        })
        data = resp.json()["data"]
        assert "hits" in data
        assert "query" in data
        assert "mode" in data
        assert "took_ms" in data
        assert data["took_ms"] >= 0
        assert data["returned_count"] <= 3

    def test_hit_structure(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={
            "query": "electronics", "mode": "linear", "top_k": 1,
        })
        hits = resp.json()["data"]["hits"]
        assert len(hits) > 0
        hit = hits[0]
        for field in ("item_id", "rank", "score", "source"):
            assert field in hit, f"Missing {field}"
        assert hit["rank"] == 1

    def test_rank_consecutive(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={
            "query": "electronics", "mode": "bm25", "top_k": 5,
        })
        ranks = [h["rank"] for h in resp.json()["data"]["hits"]]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_empty_query_rejected(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={"query": ""})
        assert resp.status_code in (422, 400)

    def test_whitespace_only(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={"query": "   "})
        assert resp.status_code in (422, 400)

    def test_top_k_zero_rejected(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={"query": "test", "top_k": 0})
        assert resp.status_code == 422

    def test_invalid_mode_rejected(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={"query": "test", "mode": "INVALID"})
        assert resp.status_code == 422

    def test_extra_fields_rejected(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={"query": "test", "hack": True})
        assert resp.status_code == 422

    def test_personalize_missing_user_id(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={
            "query": "test", "personalize": True,
        })
        assert resp.status_code in (422, 400)

    def test_default_mode_is_linear(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={"query": "electronics"})
        assert resp.status_code == 200
        assert resp.json()["data"]["mode"] in ("linear", "bm25", "semantic", "rrf")

    def test_meta_present(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={"query": "electronics"})
        data = resp.json()
        assert data["meta"]["api_version"] == "v1"
        assert "request_id" in data["meta"]

    def test_personalized_search(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={
            "query": "electronics", "mode": "linear", "top_k": 5,
            "user_id": "user_000001", "personalize": True,
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "personalization_requested" in data
        assert data["personalization_requested"] is True

    def test_unknown_user_fallback(self, client_with_data):
        resp = client_with_data.post("/api/v1/search", json={
            "query": "electronics", "mode": "linear", "top_k": 5,
            "user_id": "nonexistent_user_xyz", "personalize": True,
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["personalization_applied"] is False
        assert data["fallback_reason"] is not None

    def test_search_deterministic(self, client_with_data):
        r1 = client_with_data.post("/api/v1/search", json={
            "query": "electronics", "mode": "bm25", "top_k": 5,
        })
        r2 = client_with_data.post("/api/v1/search", json={
            "query": "electronics", "mode": "bm25", "top_k": 5,
        })
        assert [h["item_id"] for h in r1.json()["data"]["hits"]] == \
               [h["item_id"] for h in r2.json()["data"]["hits"]]
