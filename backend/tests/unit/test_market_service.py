"""Unit tests for services/market/market_service.py.

Covers: create_item, list/get item, remove_item, place_order,
        ship_order, confirm_receipt, cancel_order, list_my_orders.
"""

import pytest
from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.user import User
from app.services.market import market_service
from app.services.market.market_service import MarketError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username="alice", email="alice@example.com", points=0):
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash("pw"),
        current_points=points,
    )
    db.session.add(user)
    db.session.flush()
    return user


def _create_item(seller, price=100):
    return market_service.create_item(
        seller_id=seller.id,
        title="Old Bike",
        description="Good condition",
        price_points=price,
    )


# ---------------------------------------------------------------------------
# Item operations
# ---------------------------------------------------------------------------

class TestCreateItem:
    def test_creates_item_with_active_status(self):
        seller = _make_user()
        item = _create_item(seller)
        assert item["status"] == "active"
        assert item["price_points"] == 100
        assert item["seller_id"] == seller.id

    def test_create_item_triggers_market_topic_assignment(self, monkeypatch):
        seller = _make_user("topic-seller", "topic-seller@example.com")
        captured = {}

        monkeypatch.setattr(
            market_service.topic_mapping_service,
            "refresh_market_item_topics",
            lambda **kwargs: captured.update(kwargs) or [],
        )

        item = market_service.create_item(
            seller_id=seller.id,
            title="DIY bottle lamp",
            description="Made from reused plastic bottle parts.",
            price_points=30,
        )

        assert item["id"] > 0
        assert captured == {
            "item_id": item["id"],
            "title": "DIY bottle lamp",
            "description": "Made from reused plastic bottle parts.",
        }

    def test_zero_price_raises(self):
        seller = _make_user()
        with pytest.raises(MarketError):
            market_service.create_item(
                seller_id=seller.id, title="X", price_points=0
            )

    def test_negative_price_raises(self):
        seller = _make_user()
        with pytest.raises(MarketError):
            market_service.create_item(
                seller_id=seller.id, title="X", price_points=-10
            )


class TestGetItem:
    def test_get_existing_item(self):
        seller = _make_user()
        item = _create_item(seller)
        fetched = market_service.get_item(item["id"])
        assert fetched["id"] == item["id"]

    def test_get_item_records_market_view_for_authenticated_viewer(self, monkeypatch):
        seller = _make_user("seller", "seller@example.com")
        buyer = _make_user("buyer", "buyer@example.com")
        item = _create_item(seller)
        captured = {}
        refreshed = []

        monkeypatch.setattr(
            market_service.behavior_event_service,
            "record_market_view",
            lambda **kwargs: captured.update(kwargs) or object(),
        )
        monkeypatch.setattr(
            market_service,
            "_refresh_recommendation_state",
            lambda user_id: refreshed.append(user_id),
        )

        fetched = market_service.get_item(item["id"], viewer_user_id=buyer.id)

        assert fetched["id"] == item["id"]
        assert captured == {"user_id": buyer.id, "item_id": item["id"]}
        assert refreshed == [buyer.id]

    def test_get_nonexistent_item_raises(self):
        with pytest.raises(MarketError) as exc_info:
            market_service.get_item(99999)
        assert exc_info.value.http_status == 404


class TestListActiveItems:
    def test_only_active_items_returned(self):
        seller = _make_user()
        i1 = _create_item(seller)
        i2 = _create_item(seller)
        market_service.remove_item(i2["id"], operator_user_id=seller.id)
        result = market_service.list_active_items(page=1, per_page=10)
        ids = [i["id"] for i in result["items"]]
        assert i1["id"] in ids
        assert i2["id"] not in ids

    def test_pagination_envelope(self):
        seller = _make_user()
        for _ in range(5):
            _create_item(seller)
        result = market_service.list_active_items(page=1, per_page=3)
        assert result["total"] == 5
        assert len(result["items"]) == 3

    def test_authenticated_user_uses_personalized_order(self, monkeypatch):
        seller = _make_user("personal-seller", "personal-seller@example.com")
        viewer = _make_user("personal-viewer", "personal-viewer@example.com")
        first = _create_item(seller, price=100)
        second = market_service.create_item(
            seller_id=seller.id,
            title="Second",
            description="Another item",
            price_points=110,
        )

        monkeypatch.setattr(
            market_service,
            "rank_items_for_user",
            lambda items, user_id: list(reversed(items)),
        )

        result = market_service.list_active_items(page=1, per_page=10, viewer_user_id=viewer.id)
        assert [item["id"] for item in result["items"]] == [first["id"], second["id"]]

    def test_authenticated_market_list_excludes_viewer_own_items(self):
        seller = _make_user("self-seller", "self-seller@example.com")
        other = _make_user("other-seller", "other-seller@example.com")
        own_item = _create_item(seller, price=100)
        other_item = market_service.create_item(
            seller_id=other.id,
            title="Other item",
            description="Other description",
            price_points=120,
        )

        result = market_service.list_active_items(page=1, per_page=10, viewer_user_id=seller.id)

        ids = [item["id"] for item in result["items"]]
        assert own_item["id"] not in ids
        assert other_item["id"] in ids
        assert result["total"] == 1

    def test_authenticated_market_list_excludes_items_already_ordered_by_viewer(self):
        seller = _make_user("ordered-seller", "ordered-seller@example.com")
        buyer = _make_user("ordered-buyer", "ordered-buyer@example.com", points=500)
        bought_item = _create_item(seller, price=100)
        visible_item = market_service.create_item(
            seller_id=seller.id,
            title="Visible item",
            description="Still visible",
            price_points=90,
        )
        order = market_service.place_order(buyer_id=buyer.id, item_id=bought_item["id"])
        market_service.cancel_order(order["id"], operator_user_id=buyer.id)

        result = market_service.list_active_items(page=1, per_page=10, viewer_user_id=buyer.id)

        ids = [item["id"] for item in result["items"]]
        assert bought_item["id"] not in ids
        assert visible_item["id"] in ids
        assert result["total"] == 1


class TestRecordItemLongView:
    def test_records_long_view_and_recomputes_profile(self, monkeypatch):
        seller = _make_user("long-seller", "long-seller@example.com")
        viewer = _make_user("long-viewer", "long-viewer@example.com")
        item = _create_item(seller)
        captured = {}
        refreshed = []

        monkeypatch.setattr(
            market_service.behavior_event_repository,
            "get_latest_behavior_event_for_target",
            lambda *args, **kwargs: None,
        )
        monkeypatch.setattr(
            market_service.behavior_event_service,
            "record_market_long_view",
            lambda **kwargs: captured.update(kwargs) or object(),
        )
        monkeypatch.setattr(
            market_service,
            "_refresh_recommendation_state",
            lambda user_id: refreshed.append(user_id),
        )

        result = market_service.record_item_long_view(item["id"], viewer_user_id=viewer.id)

        assert result == {"tracked": True}
        assert captured == {"user_id": viewer.id, "item_id": item["id"]}
        assert refreshed == [viewer.id]

    def test_skips_duplicate_long_view_inside_dedup_window(self, monkeypatch):
        seller = _make_user("dedup-seller", "dedup-seller@example.com")
        viewer = _make_user("dedup-viewer", "dedup-viewer@example.com")
        item = _create_item(seller)
        latest_event = type(
            "Event",
            (),
            {"created_at": market_service._utc_now() - market_service.MARKET_LONG_VIEW_DEDUP_WINDOW / 2},
        )()

        monkeypatch.setattr(
            market_service.behavior_event_repository,
            "get_latest_behavior_event_for_target",
            lambda *args, **kwargs: latest_event,
        )
        monkeypatch.setattr(
            market_service.behavior_event_service,
            "record_market_long_view",
            lambda **kwargs: pytest.fail("should not record duplicate market long-view"),
        )

        result = market_service.record_item_long_view(item["id"], viewer_user_id=viewer.id)

        assert result == {"tracked": False, "reason": "deduplicated"}


class TestRemoveItem:
    def test_seller_can_remove(self):
        seller = _make_user()
        item = _create_item(seller)
        market_service.remove_item(item["id"], operator_user_id=seller.id)
        fetched = market_service.get_item(item["id"])
        assert fetched["status"] == "removed"

    def test_non_seller_cannot_remove(self):
        seller = _make_user("s", "s@x.com")
        other = _make_user("o", "o@x.com")
        item = _create_item(seller)
        with pytest.raises(MarketError) as exc_info:
            market_service.remove_item(item["id"], operator_user_id=other.id)
        assert exc_info.value.http_status == 403

    def test_cannot_remove_sold_item(self):
        seller = _make_user("s", "s@x.com", points=0)
        buyer = _make_user("b", "b@x.com", points=200)
        item = _create_item(seller, price=100)
        market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        with pytest.raises(MarketError) as exc_info:
            market_service.remove_item(item["id"], operator_user_id=seller.id)
        assert exc_info.value.http_status == 409


# ---------------------------------------------------------------------------
# Order lifecycle
# ---------------------------------------------------------------------------

class TestPlaceOrder:
    def test_successful_purchase_deducts_buyer_points(self):
        seller = _make_user("s", "s@x.com", points=0)
        buyer = _make_user("b", "b@x.com", points=200)
        item = _create_item(seller, price=100)
        order = market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        assert order["status"] == "paid"
        db.session.refresh(buyer)
        assert buyer.current_points == 100

    def test_item_marked_sold_out_after_purchase(self):
        seller = _make_user("s", "s@x.com")
        buyer = _make_user("b", "b@x.com", points=200)
        item = _create_item(seller, price=100)
        market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        fetched = market_service.get_item(item["id"])
        assert fetched["status"] == "sold_out"

    def test_insufficient_points_raises(self):
        seller = _make_user("s", "s@x.com")
        buyer = _make_user("b", "b@x.com", points=50)
        item = _create_item(seller, price=100)
        with pytest.raises(MarketError) as exc_info:
            market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        assert exc_info.value.http_status == 402

    def test_cannot_buy_own_item(self):
        seller = _make_user(points=500)
        item = _create_item(seller, price=100)
        with pytest.raises(MarketError) as exc_info:
            market_service.place_order(buyer_id=seller.id, item_id=item["id"])
        assert exc_info.value.http_status == 400

    def test_cannot_buy_inactive_item(self):
        seller = _make_user("s", "s@x.com")
        buyer = _make_user("b", "b@x.com", points=500)
        item = _create_item(seller, price=100)
        market_service.remove_item(item["id"], operator_user_id=seller.id)
        with pytest.raises(MarketError) as exc_info:
            market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        assert exc_info.value.http_status == 409

    def test_place_order_records_buyer_market_order_signal(self, monkeypatch):
        seller = _make_user("order-seller", "order-seller@example.com")
        buyer = _make_user("order-buyer", "order-buyer@example.com", points=500)
        item = _create_item(seller, price=100)
        captured = {}
        refreshed = []

        monkeypatch.setattr(
            market_service.behavior_event_service,
            "record_market_order",
            lambda **kwargs: captured.update(kwargs) or object(),
        )
        monkeypatch.setattr(
            market_service,
            "_refresh_recommendation_state",
            lambda user_id: refreshed.append(user_id),
        )

        order = market_service.place_order(buyer_id=buyer.id, item_id=item["id"])

        assert order["status"] == "paid"
        assert captured == {
            "user_id": buyer.id,
            "order_id": order["id"],
            "item_id": item["id"],
        }
        assert refreshed == [buyer.id]


class TestShipOrder:
    def test_seller_can_ship(self):
        seller = _make_user("s", "s@x.com", points=0)
        buyer = _make_user("b", "b@x.com", points=200)
        item = _create_item(seller, price=100)
        order = market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        result = market_service.ship_order(order["id"], operator_user_id=seller.id)
        assert result["status"] == "shipped"

    def test_non_seller_cannot_ship(self):
        seller = _make_user("s", "s@x.com", points=0)
        buyer = _make_user("b", "b@x.com", points=200)
        item = _create_item(seller, price=100)
        order = market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        with pytest.raises(MarketError) as exc_info:
            market_service.ship_order(order["id"], operator_user_id=buyer.id)
        assert exc_info.value.http_status == 403

    def test_cannot_ship_already_shipped_order(self):
        seller = _make_user("s", "s@x.com", points=0)
        buyer = _make_user("b", "b@x.com", points=200)
        item = _create_item(seller, price=100)
        order = market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        market_service.ship_order(order["id"], operator_user_id=seller.id)
        with pytest.raises(MarketError) as exc_info:
            market_service.ship_order(order["id"], operator_user_id=seller.id)
        assert exc_info.value.http_status == 409


class TestConfirmReceipt:
    def test_buyer_confirms_and_seller_earns_points(self):
        seller = _make_user("s", "s@x.com", points=0)
        buyer = _make_user("b", "b@x.com", points=200)
        item = _create_item(seller, price=100)
        order = market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        market_service.ship_order(order["id"], operator_user_id=seller.id)
        result = market_service.confirm_receipt(order["id"], operator_user_id=buyer.id)
        assert result["status"] == "completed"
        db.session.refresh(seller)
        assert seller.current_points == 100

    def test_non_buyer_cannot_confirm(self):
        seller = _make_user("s", "s@x.com", points=0)
        buyer = _make_user("b", "b@x.com", points=200)
        item = _create_item(seller, price=100)
        order = market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        market_service.ship_order(order["id"], operator_user_id=seller.id)
        with pytest.raises(MarketError) as exc_info:
            market_service.confirm_receipt(order["id"], operator_user_id=seller.id)
        assert exc_info.value.http_status == 403

    def test_cannot_confirm_unshipped_order(self):
        seller = _make_user("s", "s@x.com", points=0)
        buyer = _make_user("b", "b@x.com", points=200)
        item = _create_item(seller, price=100)
        order = market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        with pytest.raises(MarketError) as exc_info:
            market_service.confirm_receipt(order["id"], operator_user_id=buyer.id)
        assert exc_info.value.http_status == 409

    def test_confirm_receipt_records_seller_completion_signal(self, monkeypatch):
        seller = _make_user("complete-seller", "complete-seller@example.com", points=0)
        buyer = _make_user("complete-buyer", "complete-buyer@example.com", points=200)
        item = _create_item(seller, price=100)
        order = market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        market_service.ship_order(order["id"], operator_user_id=seller.id)
        captured = {}
        refreshed = []

        monkeypatch.setattr(
            market_service.behavior_event_service,
            "record_market_order_completed_as_seller",
            lambda **kwargs: captured.update(kwargs) or object(),
        )
        monkeypatch.setattr(
            market_service,
            "_refresh_recommendation_state",
            lambda user_id: refreshed.append(user_id),
        )

        result = market_service.confirm_receipt(order["id"], operator_user_id=buyer.id)

        assert result["status"] == "completed"
        assert captured == {
            "user_id": seller.id,
            "order_id": order["id"],
            "item_id": item["id"],
        }
        assert refreshed == [seller.id]


class TestCancelOrder:
    def test_buyer_can_cancel_paid_order_and_gets_refund(self):
        seller = _make_user("s", "s@x.com", points=0)
        buyer = _make_user("b", "b@x.com", points=200)
        item = _create_item(seller, price=100)
        order = market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        result = market_service.cancel_order(order["id"], operator_user_id=buyer.id)
        assert result["status"] == "cancelled"
        db.session.refresh(buyer)
        assert buyer.current_points == 200  # fully refunded

    def test_item_reinstated_after_cancel(self):
        seller = _make_user("s", "s@x.com", points=0)
        buyer = _make_user("b", "b@x.com", points=200)
        item = _create_item(seller, price=100)
        order = market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        market_service.cancel_order(order["id"], operator_user_id=buyer.id)
        fetched = market_service.get_item(item["id"])
        assert fetched["status"] == "active"

    def test_cannot_cancel_shipped_order(self):
        seller = _make_user("s", "s@x.com", points=0)
        buyer = _make_user("b", "b@x.com", points=200)
        item = _create_item(seller, price=100)
        order = market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        market_service.ship_order(order["id"], operator_user_id=seller.id)
        with pytest.raises(MarketError) as exc_info:
            market_service.cancel_order(order["id"], operator_user_id=buyer.id)
        assert exc_info.value.http_status == 409

    def test_non_buyer_cannot_cancel(self):
        seller = _make_user("s", "s@x.com", points=0)
        buyer = _make_user("b", "b@x.com", points=200)
        item = _create_item(seller, price=100)
        order = market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        with pytest.raises(MarketError) as exc_info:
            market_service.cancel_order(order["id"], operator_user_id=seller.id)
        assert exc_info.value.http_status == 403


class TestListMyOrders:
    def test_list_as_buyer(self):
        seller = _make_user("s", "s@x.com", points=0)
        buyer = _make_user("b", "b@x.com", points=500)
        for _ in range(2):
            item = _create_item(seller, price=100)
            market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        result = market_service.list_my_orders(buyer.id, 1, 10, role="buyer")
        assert result["total"] == 2

    def test_list_as_seller(self):
        seller = _make_user("s", "s@x.com", points=0)
        buyer = _make_user("b", "b@x.com", points=500)
        for _ in range(3):
            item = _create_item(seller, price=100)
            market_service.place_order(buyer_id=buyer.id, item_id=item["id"])
        result = market_service.list_my_orders(seller.id, 1, 10, role="seller")
        assert result["total"] == 3

    def test_list_all_roles(self):
        u1 = _make_user("u1", "u1@x.com", points=500)
        u2 = _make_user("u2", "u2@x.com", points=500)
        item_a = _create_item(u1, price=100)
        item_b = market_service.create_item(seller_id=u2.id, title="B", price_points=100)
        market_service.place_order(buyer_id=u2.id, item_id=item_a["id"])
        market_service.place_order(buyer_id=u1.id, item_id=item_b["id"])
        result = market_service.list_my_orders(u1.id, 1, 10, role="all")
        assert result["total"] == 2
