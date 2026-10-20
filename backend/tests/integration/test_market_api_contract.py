"""Error messages, response shapes and tokens of the market API.

Pinned against the Flask routes before they moved to FastAPI and kept
unchanged across the move.
"""

from __future__ import annotations

import datetime as dt
import re

import jwt as pyjwt
import pytest

from app.core.config import get_settings

NAIVE_ISO = r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?"
ITEM_FIELDS = {
    "id",
    "seller_id",
    "title",
    "description",
    "image_urls_json",
    "price_points",
    "status",
    "created_at",
}
ORDER_FIELDS = {"id", "item_id", "buyer_id", "seller_id", "price_points", "status", "created_at"}


def _item(client, headers, **overrides) -> dict:
    body = {"title": "Old bike", "price_points": 50}
    body.update(overrides)
    response = client.post("/api/market/items", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _order(client, headers, item_id) -> dict:
    response = client.post("/api/market/orders", json={"item_id": item_id}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _assert_error(response, status: int, code: int, message: str) -> None:
    assert response.status_code == status, response.text
    assert response.json() == {"code": code, "message": message, "data": {}}


@pytest.fixture
def trade(client, make_auth_headers):
    """A seller, a buyer with points, and one active item."""
    seller_id, seller = make_auth_headers(username="seller")
    buyer_id, buyer = make_auth_headers(username="buyer", points=200)
    item = _item(client, seller)
    return {
        "seller_id": seller_id,
        "seller": seller,
        "buyer_id": buyer_id,
        "buyer": buyer,
        "item": item,
    }


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


class TestItems:
    def test_item_shape(self, client, make_auth_headers):
        seller_id, seller = make_auth_headers()

        item = _item(
            client,
            seller,
            description="Blue, 26 inch.",
            image_urls_json='["/api/uploads/forum/a.png"]',
            price_points="70",
        )

        assert set(item) == ITEM_FIELDS
        assert item["seller_id"] == seller_id
        assert (item["description"], item["image_urls_json"]) == (
            "Blue, 26 inch.",
            '["/api/uploads/forum/a.png"]',
        )
        assert (item["price_points"], item["status"]) == (70, "active")
        assert re.fullmatch(NAIVE_ISO, item["created_at"])

    @pytest.mark.parametrize(
        ("body", "message"),
        [
            ({"title": "  ", "price_points": 5}, "Field 'title' is required."),
            ({"title": "Bike", "price_points": "lots"}, "'price_points' must be an integer."),
            ({"title": "Bike", "price_points": -1}, "'price_points' must be a positive integer."),
        ],
        ids=["title", "price-not-int", "price-negative"],
    )
    def test_create_validation(self, client, make_auth_headers, body, message):
        _, seller = make_auth_headers()

        response = client.post("/api/market/items", json=body, headers=seller)

        _assert_error(response, 400, 40001, message)

    def test_lists(self, client, trade):
        browse = client.get("/api/market/items").json()["data"]
        mine = client.get("/api/market/items/mine", headers=trade["seller"]).json()["data"]

        for page in (browse, mine):
            assert set(page) == {"items", "total", "page", "per_page"}
            assert (page["page"], page["per_page"], page["total"]) == (1, 20, 1)
            assert set(page["items"][0]) == ITEM_FIELDS

    def test_detail_not_found(self, client):
        _assert_error(client.get("/api/market/items/999999"), 404, 40400, "Item not found.")

    def test_long_view(self, client, trade):
        path = f"/api/market/items/{trade['item']['id']}/long-view"

        first = client.post(path, headers=trade["buyer"])
        again = client.post(path, headers=trade["buyer"])

        assert (first.status_code, first.json()["data"]) == (200, {"tracked": True})
        assert again.json()["data"] == {"tracked": False, "reason": "deduplicated"}
        _assert_error(
            client.post("/api/market/items/999999/long-view", headers=trade["buyer"]),
            404,
            40400,
            "Item not found.",
        )

    def test_remove(self, client, trade):
        path = f"/api/market/items/{trade['item']['id']}"

        _assert_error(
            client.delete(path, headers=trade["buyer"]),
            403,
            40300,
            "You are not the seller of this item.",
        )
        removed = client.delete(path, headers=trade["seller"])
        assert removed.json() == {"code": 0, "message": "ok", "data": {}}
        _assert_error(
            client.delete(path, headers=trade["seller"]),
            409,
            40901,
            "Cannot remove an item with status 'removed'.",
        )
        _assert_error(
            client.delete("/api/market/items/999999", headers=trade["seller"]),
            404,
            40400,
            "Item not found.",
        )


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


class TestOrders:
    def test_order_shape(self, client, trade):
        order = _order(client, trade["buyer"], trade["item"]["id"])

        assert set(order) == ORDER_FIELDS
        assert (order["buyer_id"], order["seller_id"], order["item_id"]) == (
            trade["buyer_id"],
            trade["seller_id"],
            trade["item"]["id"],
        )
        assert (order["price_points"], order["status"]) == (50, "paid")
        assert re.fullmatch(NAIVE_ISO, order["created_at"])

    @pytest.mark.parametrize(
        ("body", "message"),
        [({}, "Field 'item_id' is required."), ({"item_id": "x"}, "'item_id' must be an integer.")],
        ids=["missing", "not-int"],
    )
    def test_place_validation(self, client, trade, body, message):
        response = client.post("/api/market/orders", json=body, headers=trade["buyer"])

        _assert_error(response, 400, 40001, message)

    def test_place_errors(self, client, trade, make_auth_headers):
        item_id = trade["item"]["id"]
        _, poor = make_auth_headers(username="poor", points=10)

        _assert_error(
            client.post("/api/market/orders", json={"item_id": 999999}, headers=trade["buyer"]),
            404,
            40400,
            "Item not found.",
        )
        _assert_error(
            client.post("/api/market/orders", json={"item_id": item_id}, headers=trade["seller"]),
            400,
            40002,
            "You cannot buy your own item.",
        )
        _assert_error(
            client.post("/api/market/orders", json={"item_id": item_id}, headers=poor),
            402,
            40200,
            "Insufficient points to purchase this item.",
        )
        _order(client, trade["buyer"], item_id)
        _assert_error(
            client.post("/api/market/orders", json={"item_id": item_id}, headers=trade["buyer"]),
            409,
            40900,
            "Item is no longer available.",
        )

    def test_transition_errors(self, client, trade):
        order_id = _order(client, trade["buyer"], trade["item"]["id"])["id"]
        base = f"/api/market/orders/{order_id}"

        _assert_error(
            client.patch(f"{base}/ship", headers=trade["buyer"]),
            403,
            40300,
            "You are not the seller of this order.",
        )
        _assert_error(
            client.patch(f"{base}/confirm", headers=trade["seller"]),
            403,
            40300,
            "You are not the buyer of this order.",
        )
        _assert_error(
            client.patch(f"{base}/confirm", headers=trade["buyer"]),
            409,
            40901,
            "Cannot confirm receipt for order with status 'paid'.",
        )
        shipped = client.patch(f"{base}/ship", headers=trade["seller"])
        assert (shipped.status_code, shipped.json()["data"]["status"]) == (200, "shipped")
        assert set(shipped.json()["data"]) == ORDER_FIELDS
        _assert_error(
            client.patch(f"{base}/ship", headers=trade["seller"]),
            409,
            40901,
            "Order cannot be shipped from status 'shipped'.",
        )
        _assert_error(
            client.patch(f"{base}/cancel", headers=trade["buyer"]),
            409,
            40901,
            "Only orders in 'paid' state can be cancelled.",
        )
        _assert_error(
            client.patch(f"{base}/cancel", headers=trade["seller"]),
            403,
            40300,
            "You are not the buyer of this order.",
        )
        confirmed = client.patch(f"{base}/confirm", headers=trade["buyer"])
        assert confirmed.json()["data"]["status"] == "completed"
        for action in ("ship", "confirm", "cancel"):
            _assert_error(
                client.patch(f"/api/market/orders/999999/{action}", headers=trade["buyer"]),
                404,
                40400,
                "Order not found.",
            )

    def test_my_orders(self, client, trade):
        _order(client, trade["buyer"], trade["item"]["id"])

        page = client.get("/api/market/orders?role=buyer", headers=trade["buyer"]).json()["data"]

        assert set(page) == {"items", "total", "page", "per_page"}
        assert set(page["items"][0]) == ORDER_FIELDS
        _assert_error(
            client.get("/api/market/orders?role=everyone", headers=trade["buyer"]),
            400,
            40001,
            "'role' must be one of: buyer, seller, all.",
        )


# ---------------------------------------------------------------------------
# Tokens on routes where login is optional
# ---------------------------------------------------------------------------


class TestOptionalLogin:
    @pytest.mark.parametrize("path", ["/api/market/items", "/api/market/items/{id}"])
    def test_bad_token_is_a_401(self, client, trade, path):
        response = client.get(
            path.format(id=trade["item"]["id"]), headers={"Authorization": "Bearer garbage"}
        )

        assert response.status_code == 401
        assert response.json()["code"] == 40100

    @pytest.mark.parametrize("path", ["/api/market/items", "/api/market/items/{id}"])
    def test_token_for_an_unknown_user_is_a_401(self, client, trade, path):
        # Was served as anonymous; now the same rule as every optional route:
        # a token that is sent must identify a user.
        token = pyjwt.encode(
            {
                "sub": "nobody",
                "type": "access",
                "exp": dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
            },
            get_settings().jwt_secret_key,
            algorithm="HS256",
        )

        response = client.get(
            path.format(id=trade["item"]["id"]), headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 401
