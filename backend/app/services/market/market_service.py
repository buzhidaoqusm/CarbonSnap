"""C2C Marketplace business logic.

Order state machine:
  (item active) -> place_order -> paid
               -> ship_order   -> shipped
               -> confirm_receipt -> completed

Points flow:
  place_order:      buyer.spend_points  (escrow deducted)
  confirm_receipt:  seller.earn_points  (escrow settled)
  cancel_order:     buyer.earn_points   (refund, only from 'paid' state)

All multi-step mutations (item status + order write + transaction write)
are wrapped in a single db.session commit for atomicity.
"""

from datetime import UTC, datetime, timedelta

from app.extensions.db import db
from app.repositories.ledger.ledger_repository import (
    InsufficientPointsError,
    earn_points,
    spend_points,
)
from app.repositories.market import market_repository
from app.repositories.recommendation import behavior_event_repository
from app.services.ai import memory_service
from app.services.notification import notification_service
from app.services.recommendation import (
    behavior_event_service,
    preference_profile_service,
    topic_mapping_service,
)
from app.services.recommendation.market_recommendation_service import rank_items_for_user


class MarketError(Exception):
    """Known marketplace errors; carries API error code and HTTP status."""

    def __init__(self, message: str, code: int = 40001, http_status: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


MARKET_LONG_VIEW_DEDUP_WINDOW = timedelta(minutes=30)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _ensure_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _refresh_recommendation_state(user_id: int) -> None:
    preference_profile_service.recompute_user_preference_profiles(user_id)
    memory_service.rebuild_user_preferences_summary(user_id)


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


def _serialize_item(item) -> dict:
    return {
        "id": item.id,
        "seller_id": item.seller_id,
        "title": item.title,
        "description": item.description,
        "image_urls_json": item.image_urls_json,
        "price_points": item.price_points,
        "status": item.status,
        "created_at": item.created_at.isoformat(),
    }


def _serialize_order(order) -> dict:
    return {
        "id": order.id,
        "item_id": order.item_id,
        "buyer_id": order.buyer_id,
        "seller_id": order.seller_id,
        "price_points": order.price_points,
        "status": order.status,
        "created_at": order.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Item operations
# ---------------------------------------------------------------------------


def create_item(
    *,
    seller_id: int,
    title: str,
    description: str | None = None,
    image_urls_json: str | None = None,
    price_points: int,
) -> dict:
    if price_points <= 0:
        raise MarketError("'price_points' must be a positive integer.")
    item = market_repository.create_item(
        seller_id=seller_id,
        title=title,
        description=description,
        image_urls_json=image_urls_json,
        price_points=price_points,
    )
    topic_mapping_service.refresh_market_item_topics(
        item_id=item.id,
        title=item.title,
        description=item.description,
    )
    try:
        behavior_event_service.record_market_item_create(user_id=seller_id, item_id=item.id)
        _refresh_recommendation_state(seller_id)
    except Exception:
        pass
    return _serialize_item(item)


def get_item(item_id: int, *, viewer_user_id: int | None = None) -> dict:
    item = market_repository.get_item_by_id(item_id)
    if item is None:
        raise MarketError("Item not found.", code=40400, http_status=404)
    if viewer_user_id is not None and viewer_user_id != item.seller_id:
        try:
            behavior_event_service.record_market_view(user_id=viewer_user_id, item_id=item.id)
            _refresh_recommendation_state(viewer_user_id)
        except Exception:
            pass
    return _serialize_item(item)


def record_item_long_view(item_id: int, *, viewer_user_id: int) -> dict:
    item = market_repository.get_item_by_id(item_id)
    if item is None:
        raise MarketError("Item not found.", code=40400, http_status=404)

    latest_event = behavior_event_repository.get_latest_behavior_event_for_target(
        viewer_user_id,
        domain="market",
        target_type="item",
        target_id=item.id,
        action_types=["long_view"],
    )
    if latest_event is not None:
        latest_created_at = _ensure_aware_utc(latest_event.created_at)
        if (
            latest_created_at is not None
            and (_utc_now() - latest_created_at) < MARKET_LONG_VIEW_DEDUP_WINDOW
        ):
            return {"tracked": False, "reason": "deduplicated"}

    try:
        behavior_event_service.record_market_long_view(user_id=viewer_user_id, item_id=item.id)
        _refresh_recommendation_state(viewer_user_id)
    except Exception:
        return {"tracked": False, "reason": "skipped"}
    return {"tracked": True}


def list_active_items(page: int, per_page: int, *, viewer_user_id: int | None = None) -> dict:
    if viewer_user_id is not None:
        all_items = market_repository.list_all_active_items_excluding_seller(
            seller_id=viewer_user_id
        )
        ordered_item_ids = market_repository.list_ordered_item_ids_by_buyer(viewer_user_id)
        candidate_items = [item for item in all_items if int(item.id) not in ordered_item_ids]
        total = len(candidate_items)
        try:
            ordered_items = rank_items_for_user(items=candidate_items, user_id=viewer_user_id)
        except Exception:
            ordered_items = candidate_items
        start = max((page - 1) * per_page, 0)
        items = ordered_items[start : start + per_page]
    else:
        items, total = market_repository.list_active_items_page(page, per_page)
    return {
        "items": [_serialize_item(i) for i in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def list_my_items(seller_id: int, page: int, per_page: int) -> dict:
    items, total = market_repository.list_items_by_seller(seller_id, page, per_page)
    return {
        "items": [_serialize_item(i) for i in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def remove_item(item_id: int, *, operator_user_id: int) -> None:
    """Seller takes down their own item (only allowed when still active)."""
    item = market_repository.get_item_by_id(item_id)
    if item is None:
        raise MarketError("Item not found.", code=40400, http_status=404)
    if item.seller_id != operator_user_id:
        raise MarketError("You are not the seller of this item.", code=40300, http_status=403)
    if item.status != "active":
        raise MarketError(
            f"Cannot remove an item with status '{item.status}'.",
            code=40901,
            http_status=409,
        )
    market_repository.update_item_status(item, "removed")
    db.session.commit()


# ---------------------------------------------------------------------------
# Order operations
# ---------------------------------------------------------------------------


def place_order(*, buyer_id: int, item_id: int) -> dict:
    """Buyer purchases an item.

    Atomically:
    1. Lock item (check active).
    2. Deduct buyer points (spend transaction).
    3. Mark item as sold_out.
    4. Create order with status='paid'.
    5. Commit.
    """
    item = market_repository.get_item_by_id(item_id)
    if item is None:
        raise MarketError("Item not found.", code=40400, http_status=404)
    if item.status != "active":
        raise MarketError("Item is no longer available.", code=40900, http_status=409)
    if item.seller_id == buyer_id:
        raise MarketError("You cannot buy your own item.", code=40002, http_status=400)

    try:
        spend_txn = spend_points(
            user_id=buyer_id,
            points=item.price_points,
            source_type="market_order",
        )
    except InsufficientPointsError as exc:
        raise MarketError(
            "Insufficient points to purchase this item.",
            code=40200,
            http_status=402,
        ) from exc

    # Mark item sold before creating the order so source_id can be set.
    market_repository.update_item_status(item, "sold_out")

    order = market_repository.create_order(
        item_id=item_id,
        buyer_id=buyer_id,
        seller_id=item.seller_id,
        price_points=item.price_points,
    )
    db.session.flush()  # populate order.id

    # Back-fill source_id on the spend transaction.
    spend_txn.source_id = order.id
    db.session.commit()
    notification_service.on_item_purchased(
        recipient_user_id=item.seller_id,
        order_id=order.id,
        item_title=item.title,
    )
    try:
        behavior_event_service.record_market_order(
            user_id=buyer_id,
            order_id=order.id,
            item_id=item.id,
        )
        _refresh_recommendation_state(buyer_id)
    except Exception:
        pass

    return _serialize_order(order)


def ship_order(order_id: int, *, operator_user_id: int) -> dict:
    """Seller marks the order as shipped."""
    order = market_repository.get_order_by_id(order_id)
    if order is None:
        raise MarketError("Order not found.", code=40400, http_status=404)
    if order.seller_id != operator_user_id:
        raise MarketError("You are not the seller of this order.", code=40300, http_status=403)
    if order.status != "paid":
        raise MarketError(
            f"Order cannot be shipped from status '{order.status}'.",
            code=40901,
            http_status=409,
        )

    market_repository.update_order_status(order, "shipped")
    db.session.commit()

    # Notify buyer.
    notification_service.on_order_shipped(recipient_user_id=order.buyer_id, order_id=order.id)
    return _serialize_order(order)


def confirm_receipt(order_id: int, *, operator_user_id: int) -> dict:
    """Buyer confirms receipt; escrow points settle to the seller.

    Atomically:
    1. Validate order is in 'shipped' state.
    2. Credit seller points (earn transaction).
    3. Mark order 'completed'.
    4. Commit.
    """
    order = market_repository.get_order_by_id(order_id)
    if order is None:
        raise MarketError("Order not found.", code=40400, http_status=404)
    if order.buyer_id != operator_user_id:
        raise MarketError("You are not the buyer of this order.", code=40300, http_status=403)
    if order.status != "shipped":
        raise MarketError(
            f"Cannot confirm receipt for order with status '{order.status}'.",
            code=40901,
            http_status=409,
        )

    earn_points(
        user_id=order.seller_id,
        points=order.price_points,
        source_type="market_order",
        source_id=order.id,
    )
    market_repository.update_order_status(order, "completed")
    db.session.commit()

    try:
        behavior_event_service.record_market_order_completed_as_seller(
            user_id=order.seller_id,
            order_id=order.id,
            item_id=order.item_id,
        )
        _refresh_recommendation_state(order.seller_id)
    except Exception:
        pass

    # Notify seller.
    notification_service.on_order_completed(recipient_user_id=order.seller_id, order_id=order.id)
    return _serialize_order(order)


def cancel_order(order_id: int, *, operator_user_id: int) -> dict:
    """Cancel a 'paid' order and refund buyer points.

    Only the buyer may cancel, and only before shipment.
    """
    order = market_repository.get_order_by_id(order_id)
    if order is None:
        raise MarketError("Order not found.", code=40400, http_status=404)
    if order.buyer_id != operator_user_id:
        raise MarketError("You are not the buyer of this order.", code=40300, http_status=403)
    if order.status != "paid":
        raise MarketError(
            "Only orders in 'paid' state can be cancelled.",
            code=40901,
            http_status=409,
        )

    # Refund buyer.
    earn_points(
        user_id=order.buyer_id,
        points=order.price_points,
        source_type="market_order",
        source_id=order.id,
    )
    # Reinstate item as active so it can be purchased again.
    item = market_repository.get_item_by_id(order.item_id)
    if item is not None and item.status == "sold_out":
        market_repository.update_item_status(item, "active")

    market_repository.update_order_status(order, "cancelled")
    db.session.commit()
    return _serialize_order(order)


def list_my_orders(user_id: int, page: int, per_page: int, *, role: str = "all") -> dict:
    """role: 'buyer' | 'seller' | 'all'"""
    if role == "buyer":
        orders, total = market_repository.list_orders_as_buyer(user_id, page, per_page)
    elif role == "seller":
        orders, total = market_repository.list_orders_as_seller(user_id, page, per_page)
    else:
        orders, total = market_repository.list_orders_by_user(user_id, page, per_page)
    return {
        "items": [_serialize_order(o) for o in orders],
        "total": total,
        "page": page,
        "per_page": per_page,
    }
