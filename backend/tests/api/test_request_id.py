"""Request ID middleware tests."""

from __future__ import annotations


class TestRequestID:
    def test_no_header_generates_id(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert "X-Request-ID" in resp.headers
        rid = resp.headers["X-Request-ID"]
        assert len(rid) > 0

    def test_client_provided_id_preserved(self, client):
        resp = client.get("/api/v1/health", headers={"X-Request-ID": "my-test-id-123"})
        assert resp.headers["X-Request-ID"] == "my-test-id-123"

    def test_error_response_has_request_id(self, client):
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404
        assert "X-Request-ID" in resp.headers
        data = resp.json()
        assert data.get("meta", {}).get("request_id", "")

    def test_header_body_identical(self, client_with_data):
        # Use search endpoint which returns DataResponse with meta
        resp = client_with_data.post("/api/v1/search", json={"query": "electronics"}, headers={"X-Request-ID": "abc123"})
        hdr = resp.headers["X-Request-ID"]
        body = resp.json().get("meta", {}).get("request_id", "")
        assert hdr == body

    def test_long_id_replaced(self, client):
        long_id = "x" * 200
        resp = client.get("/api/v1/health", headers={"X-Request-ID": long_id})
        assert resp.headers["X-Request-ID"] != long_id

    def test_invalid_chars_replaced(self, client):
        resp = client.get("/api/v1/health", headers={"X-Request-ID": "bad!@#chars"})
        rid = resp.headers["X-Request-ID"]
        assert "!" not in rid  # invalid chars → replaced
