"""Items API tests."""

from __future__ import annotations


class TestItemsAPI:
    def test_list_default(self, client_with_data):
        resp = client_with_data.get("/api/v1/items")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["returned"] > 0

    def test_list_pagination(self, client_with_data):
        resp = client_with_data.get("/api/v1/items")
        pg = resp.json()["pagination"]
        assert pg["total"] >= pg["returned"]
        assert pg["returned"] <= 100

    def test_item_detail_exists(self, client_with_data):
        resp = client_with_data.get("/api/v1/items/item_000001")
        assert resp.status_code == 200
        item = resp.json()["data"]
        assert item["item_id"] == "item_000001"
        assert "title" in item
        assert "price" in item

    def test_item_detail_not_found(self, client_with_data):
        resp = client_with_data.get("/api/v1/items/nonexistent_item")
        assert resp.status_code == 404

    def test_item_price_is_string(self, client_with_data):
        resp = client_with_data.get("/api/v1/items/item_000001")
        price = resp.json()["data"]["price"]
        assert isinstance(price, str)

    def test_meta_present(self, client_with_data):
        resp = client_with_data.get("/api/v1/items")
        data = resp.json()
        assert data["meta"]["api_version"] == "v1"
