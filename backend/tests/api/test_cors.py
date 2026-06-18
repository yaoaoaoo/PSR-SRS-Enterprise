"""CORS tests."""

from __future__ import annotations


class TestCORS:
    def test_localhost_origin_allowed(self, client):
        resp = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert resp.status_code == 200

    def test_localhost_ip_allowed(self, client):
        resp = client.get(
            "/api/v1/health",
            headers={"Origin": "http://127.0.0.1:5173"},
        )
        assert resp.status_code == 200

    def test_disallowed_origin_no_cors_header(self, client):
        resp = client.get(
            "/api/v1/health",
            headers={"Origin": "http://evil.com"},
        )
        # Should not have Access-Control-Allow-Origin for disallowed origins
        acao = resp.headers.get("access-control-allow-origin", "")
        if acao:
            assert "evil.com" not in acao

    def test_options_preflight(self, client):
        resp = client.options(
            "/api/v1/search",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert resp.status_code == 200

    def test_x_request_id_header_present(self, client):
        resp = client.get("/api/v1/health")
        # X-Request-ID is always set by middleware
        assert "X-Request-ID" in resp.headers
