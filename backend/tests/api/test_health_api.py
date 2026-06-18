"""Health API enhanced tests."""

from __future__ import annotations


class TestHealthAPI:
    def test_health_200(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_readiness_has_details_on_ready(self, client_with_data):
        resp = client_with_data.get("/api/v1/health/ready")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "checks" in data

    def test_health_does_not_depend_on_index(self, client):
        """Health should be 200 even without data."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
