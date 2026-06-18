"""Evaluation API tests."""

from __future__ import annotations


class TestEvaluationAPI:
    def test_evaluate_single_query(self, client_with_data):
        resp = client_with_data.post("/api/v1/evaluation/queries", json={
            "queries": [{"query_id": "query_000001", "query_text": "electronics"}],
            "ks": [5, 10],
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["query_count"] == 1
        assert "metrics" in data

    def test_evaluate_empty_ks_rejected(self, client_with_data):
        resp = client_with_data.post("/api/v1/evaluation/queries", json={
            "queries": [{"query_id": "q1"}],
            "ks": [],
        })
        assert resp.status_code == 422

    def test_evaluate_empty_queries_rejected(self, client_with_data):
        resp = client_with_data.post("/api/v1/evaluation/queries", json={
            "queries": [],
        })
        assert resp.status_code == 422

    def test_candidate_coverage_basic(self, client_with_data):
        resp = client_with_data.post("/api/v1/evaluation/candidate-coverage", json={
            "requests": [
                {"request_id": "r1", "query_id": "q1",
                 "candidate_item_ids": ["item_000001", "item_000002"]},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["eligible_requests"] == 1
        assert data["took_ms"] >= 0

    def test_candidate_coverage_empty(self, client_with_data):
        resp = client_with_data.post("/api/v1/evaluation/candidate-coverage", json={
            "requests": [],
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["eligible_requests"] == 0

    def test_candidate_coverage_extra_fields_rejected(self, client_with_data):
        resp = client_with_data.post("/api/v1/evaluation/candidate-coverage", json={
            "requests": [], "hacked": True,
        })
        assert resp.status_code == 422
