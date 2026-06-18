"""Users API tests."""

from __future__ import annotations


class TestUsersAPI:
    def test_list(self, client_with_data):
        resp = client_with_data.get("/api/v1/users")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) > 0

    def test_detail_exists(self, client_with_data):
        resp = client_with_data.get("/api/v1/users/user_000001")
        assert resp.status_code == 200
        user = resp.json()["data"]
        assert user["user_id"] == "user_000001"

    def test_detail_not_found(self, client_with_data):
        resp = client_with_data.get("/api/v1/users/nonexistent_user")
        assert resp.status_code == 404

    def test_categories_is_list(self, client_with_data):
        resp = client_with_data.get("/api/v1/users/user_000001")
        cats = resp.json()["data"]["preferred_categories"]
        assert isinstance(cats, list)

    def test_brands_is_list(self, client_with_data):
        resp = client_with_data.get("/api/v1/users/user_000001")
        brands = resp.json()["data"]["preferred_brands"]
        assert isinstance(brands, list)

    def test_profile_warm_user(self, client_with_data):
        resp = client_with_data.get("/api/v1/users/user_000001/profile")
        assert resp.status_code == 200
        profile = resp.json()["data"]
        assert profile["user_id"] == "user_000001"

    def test_profile_has_weights(self, client_with_data):
        resp = client_with_data.get("/api/v1/users/user_000001/profile")
        profile = resp.json()["data"]
        assert "category_weights" in profile
        assert "brand_weights" in profile
