"""Unified error handling tests."""

from __future__ import annotations


class TestErrorHandlers:
    def test_404_unknown_route(self, client):
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "not_found"

    def test_404_item_not_found(self, client):
        resp = client.get("/api/v1/items/nonexistent_item_99999")
        assert resp.status_code == 404

    def test_404_user_not_found(self, client):
        resp = client.get("/api/v1/users/nonexistent_user_99999")
        assert resp.status_code == 404

    def test_422_empty_search_query(self, client):
        resp = client.post("/api/v1/search", json={"query": ""})
        assert resp.status_code in (422, 400)

    def test_422_invalid_mode(self, client):
        resp = client.post("/api/v1/search", json={"query": "test", "mode": "INVALID"})
        assert resp.status_code == 422

    def test_422_top_k_zero(self, client):
        resp = client.post("/api/v1/search", json={"query": "test", "top_k": 0})
        assert resp.status_code == 422

    def test_422_extra_fields(self, client):
        resp = client.post(
            "/api/v1/search",
            json={"query": "test", "hacked_field": "danger"},
        )
        assert resp.status_code == 422

    def test_request_id_present_on_error(self, client):
        resp = client.get("/api/v1/nonexistent")
        data = resp.json()
        assert "meta" in data
        assert len(data["meta"]["request_id"]) > 0
