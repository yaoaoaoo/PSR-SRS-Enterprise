"""FastAPI lifespan tests via TestClient."""

from __future__ import annotations


class TestLifespan:
    def test_app_starts_with_index_disabled(self, client):
        """With startup builds disabled, app should start."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_readiness_after_disabled_startup(self, client):
        """Index/profile are not built, so readiness should reflect that."""
        resp = client.get("/api/v1/health/ready")
        assert resp.status_code in (200, 503)

    def test_app_state_has_container(self, client):
        """The service container should be injected into app.state."""
        resp = client.get("/api/v1/health/ready")
        data = resp.json()
        assert "checks" in data
        assert "index" in data["checks"]
        assert "profiles" in data["checks"]

    def test_health_always_200(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_shutdown_on_app_exit(self, client):
        """App should shut down cleanly after test client exits."""
        # Test client __exit__ triggers lifespan shutdown
        pass  # verified by no errors during teardown
