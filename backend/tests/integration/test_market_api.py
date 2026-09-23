"""Integration tests for C2C Marketplace API endpoints."""

import json

from flask_jwt_extended import create_access_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post_json(client, url, data, headers=None):
    return client.post(url, data=json.dumps(data), content_type="application/json", headers=headers)


def _patch_json(client, url, headers=None):
    return client.patch(url, content_type="application/json", headers=headers)


def _create_item(client, headers, title="Old Bike", price_points=100):
    resp = _post_json(
        client,
        "/api/market/items",
        {"title": title, "price_points": price_points},
        headers,
    )
    assert resp.status_code == 201
    return resp.get_json()["data"]


def _place_order(client, headers, item_id):
    resp = _post_json(client, "/api/market/orders", {"item_id": item_id}, headers)
    assert resp.status_code == 201
    return resp.get_json()["data"]


def _get_notifications(client, headers):
    resp = client.get("/api/notifications", headers=headers)
    assert resp.status_code == 200
    return resp.get_json()["data"]["items"]


# ---------------------------------------------------------------------------
# POST /api/market/items
# ---------------------------------------------------------------------------


class TestCreateItem:
    def test_authenticated_seller_can_list_item(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        resp = _post_json(
            client,
            "/api/market/items",
            {"title": "Bike", "price_points": 200},
            headers,
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["status"] == "active"
        assert data["price_points"] == 200

    def test_missing_title_returns_400(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        resp = _post_json(client, "/api/market/items", {"price_points": 100}, headers)
        assert resp.status_code == 400

    def test_zero_price_returns_400(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        resp = _post_json(client, "/api/market/items", {"title": "X", "price_points": 0}, headers)
        assert resp.status_code == 400

    def test_unauthenticated_returns_401(self, client):
        resp = _post_json(client, "/api/market/items", {"title": "X", "price_points": 100})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/market/items
# ---------------------------------------------------------------------------


class TestListActiveItems:
    def test_anonymous_can_browse(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        _create_item(client, headers)
        resp = client.get("/api/market/items")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["total"] >= 1

    def test_pagination(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        for i in range(5):
            _create_item(client, headers, title=f"Item {i}")
        resp = client.get("/api/market/items?page=1&per_page=3")
        data = resp.get_json()["data"]
        assert data["total"] == 5
        assert len(data["items"]) == 3

    def test_removed_items_excluded(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        item = _create_item(client, headers)
        client.delete(f"/api/market/items/{item['id']}", headers=headers)
        resp = client.get("/api/market/items")
        ids = [i["id"] for i in resp.get_json()["data"]["items"]]
        assert item["id"] not in ids

    def test_authenticated_market_list_allows_personalized_path(self, client, make_auth_headers):
        _, viewer_headers = make_auth_headers()
        _, seller_headers = make_auth_headers()
        _create_item(client, seller_headers)
        resp = client.get("/api/market/items", headers=viewer_headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["total"] >= 1

    def test_authenticated_market_list_excludes_own_items(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, other_headers = make_auth_headers()
        own_item = _create_item(client, seller_headers, title="Mine")
        other_item = _create_item(client, other_headers, title="Other")

        resp = client.get("/api/market/items", headers=seller_headers)

        assert resp.status_code == 200
        ids = [item["id"] for item in resp.get_json()["data"]["items"]]
        assert own_item["id"] not in ids
        assert other_item["id"] in ids

    def test_authenticated_market_list_excludes_items_already_bought_by_viewer(
        self, client, make_auth_headers
    ):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=500)
        bought_item = _create_item(client, seller_headers, title="Bought", price_points=100)
        visible_item = _create_item(client, seller_headers, title="Visible", price_points=110)
        order = _place_order(client, buyer_headers, bought_item["id"])
        cancel_resp = _patch_json(client, f"/api/market/orders/{order['id']}/cancel", buyer_headers)
        assert cancel_resp.status_code == 200

        resp = client.get("/api/market/items", headers=buyer_headers)

        assert resp.status_code == 200
        ids = [item["id"] for item in resp.get_json()["data"]["items"]]
        assert bought_item["id"] not in ids
        assert visible_item["id"] in ids

    def test_legacy_username_token_still_lists_market_items(self, client, app, make_auth_headers):
        _, seller_headers = make_auth_headers(username="seller")
        _, _viewer_headers = make_auth_headers(username="test1")
        item = _create_item(client, seller_headers, title="Legacy market item")

        with app.app_context():
            legacy_token = create_access_token(identity="test1")

        resp = client.get(
            "/api/market/items",
            headers={"Authorization": f"Bearer {legacy_token}"},
        )

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["id"] == item["id"]


# ---------------------------------------------------------------------------
# GET /api/market/items/mine
# ---------------------------------------------------------------------------


class TestListMyItems:
    def test_returns_only_own_items(self, client, make_auth_headers):
        _, h1 = make_auth_headers()
        _, h2 = make_auth_headers()
        _create_item(client, h1, title="Mine")
        _create_item(client, h2, title="Theirs")
        resp = client.get("/api/market/items/mine", headers=h1)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["total"] == 1
        assert resp.get_json()["data"]["items"][0]["title"] == "Mine"


# ---------------------------------------------------------------------------
# GET /api/market/items/<id>
# ---------------------------------------------------------------------------


class TestGetItem:
    def test_get_existing_item(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        item = _create_item(client, headers)
        resp = client.get(f"/api/market/items/{item['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["id"] == item["id"]

    def test_nonexistent_item_returns_404(self, client):
        assert client.get("/api/market/items/99999").status_code == 404

    def test_authenticated_get_item_still_succeeds(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        item = _create_item(client, headers)
        resp = client.get(f"/api/market/items/{item['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["id"] == item["id"]


class TestRecordItemLongView:
    def test_authenticated_user_can_track_market_long_view(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, viewer_headers = make_auth_headers()
        item = _create_item(client, seller_headers)
        resp = client.post(f"/api/market/items/{item['id']}/long-view", headers=viewer_headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["tracked"] is True

    def test_unauthenticated_long_view_returns_401(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        item = _create_item(client, seller_headers)
        resp = client.post(f"/api/market/items/{item['id']}/long-view")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/market/items/<id>
# ---------------------------------------------------------------------------


class TestRemoveItem:
    def test_seller_can_remove(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        item = _create_item(client, headers)
        resp = client.delete(f"/api/market/items/{item['id']}", headers=headers)
        assert resp.status_code == 200
        assert (
            client.get(f"/api/market/items/{item['id']}").get_json()["data"]["status"] == "removed"
        )

    def test_non_seller_gets_403(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, other_headers = make_auth_headers()
        item = _create_item(client, seller_headers)
        resp = client.delete(f"/api/market/items/{item['id']}", headers=other_headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/market/orders  (place order)
# ---------------------------------------------------------------------------


class TestPlaceOrder:
    def test_successful_purchase(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=500)
        item = _create_item(client, seller_headers, price_points=100)
        resp = _post_json(client, "/api/market/orders", {"item_id": item["id"]}, buyer_headers)
        assert resp.status_code == 201
        assert resp.get_json()["data"]["status"] == "paid"

        seller_notifications = _get_notifications(client, seller_headers)
        buyer_notifications = _get_notifications(client, buyer_headers)
        assert len(seller_notifications) == 1
        assert seller_notifications[0]["event_type"] == "item_purchased"
        assert buyer_notifications == []

    def test_insufficient_points_returns_402(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=50)
        item = _create_item(client, seller_headers, price_points=100)
        resp = _post_json(client, "/api/market/orders", {"item_id": item["id"]}, buyer_headers)
        assert resp.status_code == 402

    def test_cannot_buy_own_item(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers(points=500)
        item = _create_item(client, seller_headers, price_points=100)
        resp = _post_json(client, "/api/market/orders", {"item_id": item["id"]}, seller_headers)
        assert resp.status_code == 400

    def test_cannot_buy_inactive_item(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=500)
        item = _create_item(client, seller_headers, price_points=100)
        client.delete(f"/api/market/items/{item['id']}", headers=seller_headers)
        resp = _post_json(client, "/api/market/orders", {"item_id": item["id"]}, buyer_headers)
        assert resp.status_code == 409

    def test_missing_item_id_returns_400(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        resp = _post_json(client, "/api/market/orders", {}, headers)
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# PATCH /api/market/orders/<id>/ship
# ---------------------------------------------------------------------------


class TestShipOrder:
    def test_seller_can_ship(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=500)
        item = _create_item(client, seller_headers, price_points=100)
        order = _place_order(client, buyer_headers, item["id"])
        resp = _patch_json(client, f"/api/market/orders/{order['id']}/ship", seller_headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "shipped"

    def test_buyer_cannot_ship(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=500)
        item = _create_item(client, seller_headers, price_points=100)
        order = _place_order(client, buyer_headers, item["id"])
        resp = _patch_json(client, f"/api/market/orders/{order['id']}/ship", buyer_headers)
        assert resp.status_code == 403

    def test_double_ship_returns_409(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=500)
        item = _create_item(client, seller_headers, price_points=100)
        order = _place_order(client, buyer_headers, item["id"])
        _patch_json(client, f"/api/market/orders/{order['id']}/ship", seller_headers)
        resp = _patch_json(client, f"/api/market/orders/{order['id']}/ship", seller_headers)
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# PATCH /api/market/orders/<id>/confirm
# ---------------------------------------------------------------------------


class TestConfirmReceipt:
    def test_buyer_can_confirm(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=500)
        item = _create_item(client, seller_headers, price_points=100)
        order = _place_order(client, buyer_headers, item["id"])
        _patch_json(client, f"/api/market/orders/{order['id']}/ship", seller_headers)
        resp = _patch_json(client, f"/api/market/orders/{order['id']}/confirm", buyer_headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "completed"

    def test_seller_cannot_confirm(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=500)
        item = _create_item(client, seller_headers, price_points=100)
        order = _place_order(client, buyer_headers, item["id"])
        _patch_json(client, f"/api/market/orders/{order['id']}/ship", seller_headers)
        resp = _patch_json(client, f"/api/market/orders/{order['id']}/confirm", seller_headers)
        assert resp.status_code == 403

    def test_confirm_unshipped_order_returns_409(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=500)
        item = _create_item(client, seller_headers, price_points=100)
        order = _place_order(client, buyer_headers, item["id"])
        resp = _patch_json(client, f"/api/market/orders/{order['id']}/confirm", buyer_headers)
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# PATCH /api/market/orders/<id>/cancel
# ---------------------------------------------------------------------------


class TestCancelOrder:
    def test_buyer_can_cancel_paid_order(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=500)
        item = _create_item(client, seller_headers, price_points=100)
        order = _place_order(client, buyer_headers, item["id"])
        resp = _patch_json(client, f"/api/market/orders/{order['id']}/cancel", buyer_headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "cancelled"

    def test_seller_cannot_cancel(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=500)
        item = _create_item(client, seller_headers, price_points=100)
        order = _place_order(client, buyer_headers, item["id"])
        resp = _patch_json(client, f"/api/market/orders/{order['id']}/cancel", seller_headers)
        assert resp.status_code == 403

    def test_cannot_cancel_shipped_order(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=500)
        item = _create_item(client, seller_headers, price_points=100)
        order = _place_order(client, buyer_headers, item["id"])
        _patch_json(client, f"/api/market/orders/{order['id']}/ship", seller_headers)
        resp = _patch_json(client, f"/api/market/orders/{order['id']}/cancel", buyer_headers)
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# GET /api/market/orders
# ---------------------------------------------------------------------------


class TestListMyOrders:
    def test_list_as_buyer(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=500)
        for _ in range(2):
            item = _create_item(client, seller_headers, price_points=100)
            _place_order(client, buyer_headers, item["id"])
        resp = client.get("/api/market/orders?role=buyer", headers=buyer_headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["total"] == 2

    def test_list_as_seller(self, client, make_auth_headers):
        _, seller_headers = make_auth_headers()
        _, buyer_headers = make_auth_headers(points=500)
        for _ in range(3):
            item = _create_item(client, seller_headers, price_points=100)
            _place_order(client, buyer_headers, item["id"])
        resp = client.get("/api/market/orders?role=seller", headers=seller_headers)
        assert resp.get_json()["data"]["total"] == 3

    def test_invalid_role_returns_400(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        resp = client.get("/api/market/orders?role=admin", headers=headers)
        assert resp.status_code == 400

    def test_unauthenticated_returns_401(self, client):
        assert client.get("/api/market/orders").status_code == 401
