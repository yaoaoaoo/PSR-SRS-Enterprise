"""System API tests."""

from __future__ import annotations


class TestSystemAPI:
    def test_status_200(self, client_with_data):
        resp = client_with_data.get("/api/v1/system/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "service" in data
        assert "index_ready" in data

    def test_index_status(self, client_with_data):
        resp = client_with_data.get("/api/v1/system/index")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "generation" in data
        assert "item_count" in data

    def test_profile_status(self, client_with_data):
        resp = client_with_data.get("/api/v1/system/profiles")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "generation" in data
        assert "profile_count" in data

    def test_no_database_url_exposed(self, client_with_data):
        resp = client_with_data.get("/api/v1/system/status")
        text = resp.text.lower()
        assert "sqlite" not in text or "database" in text
