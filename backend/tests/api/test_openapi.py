"""OpenAPI documentation tests."""

from __future__ import annotations


class TestOpenAPI:
    def test_openapi_json_200(self, client):
        resp = client.get("/api/v1/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    def test_all_expected_paths_present(self, client):
        data = client.get("/api/v1/openapi.json").json()
        paths = data.get("paths", {})
        expected = [
            "/api/v1/health",
            "/api/v1/health/ready",
            "/api/v1/search",
            "/api/v1/items",
            "/api/v1/items/{item_id}",
            "/api/v1/users",
            "/api/v1/users/{user_id}",
            "/api/v1/users/{user_id}/profile",
            "/api/v1/evaluation/queries",
            "/api/v1/evaluation/candidate-coverage",
            "/api/v1/system/status",
            "/api/v1/system/index",
            "/api/v1/system/profiles",
        ]
        for p in expected:
            assert p in paths, f"Missing path: {p}"

    def test_swagger_200(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_operation_ids_unique(self, client):
        data = client.get("/api/v1/openapi.json").json()
        op_ids = []
        for path_obj in data.get("paths", {}).values():
            for method in path_obj.values():
                if "operationId" in method:
                    op_ids.append(method["operationId"])
        assert len(op_ids) == len(set(op_ids)), f"Duplicate operationIds: {op_ids}"
