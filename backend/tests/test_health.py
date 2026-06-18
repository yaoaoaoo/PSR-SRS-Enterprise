"""Tests for health and readiness endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealthCheck:
    """Tests for GET /api/v1/health."""

    def test_health_returns_200(self, client: TestClient):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_health_has_status_ok(self, client: TestClient):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_has_service_field(self, client: TestClient):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "service" in data
        assert len(data["service"]) > 0

    def test_health_has_version_field(self, client: TestClient):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert data["version"] == "0.1.0"

    def test_health_has_environment_field(self, client: TestClient):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "environment" in data

    def test_health_has_timestamp_iso(self, client: TestClient):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "timestamp" in data
        # Should be a valid ISO 8601 string
        from datetime import datetime
        datetime.fromisoformat(data["timestamp"])


class TestReadinessCheck:
    """Tests for GET /api/v1/health/ready."""

    def test_ready_returns_200_or_503(self, client: TestClient):
        resp = client.get("/api/v1/health/ready")
        assert resp.status_code in (200, 503)

    def test_ready_has_service_field(self, client: TestClient):
        resp = client.get("/api/v1/health/ready")
        data = resp.json()
        assert "service" in data

    def test_ready_has_checks_section(self, client: TestClient):
        resp = client.get("/api/v1/health/ready")
        data = resp.json()
        assert "checks" in data
        assert "config_loaded" in data["checks"]
        assert data["checks"]["config_loaded"] is True

    def test_ready_has_database_check(self, client: TestClient):
        resp = client.get("/api/v1/health/ready")
        data = resp.json()
        assert "database" in data["checks"]
        assert "database_connected" in data["checks"]["database"]


class TestUnknownRoutes:
    """Tests that unknown routes return structured errors."""

    def test_unknown_route_returns_404(self, client: TestClient):
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404

    def test_unknown_route_returns_error_structure(self, client: TestClient):
        resp = client.get("/api/v1/not/found")
        data = resp.json()
        assert "error" in data or "detail" in data
        assert "code" in data.get("error", {}) or "detail" in data
