"""C2C Marketplace API Blueprint.

Endpoints:
  POST   /api/market/items                    List an item for sale
  GET    /api/market/items                    Browse active items (paginated)
  GET    /api/market/items/mine               My listed items
  GET    /api/market/items/<id>               Item detail
  DELETE /api/market/items/<id>               Remove/delist item (seller only)

  POST   /api/market/orders                   Place an order (buy)
  GET    /api/market/orders                   My orders (buyer+seller, ?role=buyer|seller|all)
  PATCH  /api/market/orders/<id>/ship         Mark as shipped (seller only)
  PATCH  /api/market/orders/<id>/confirm      Confirm receipt (buyer only)
  PATCH  /api/market/orders/<id>/cancel       Cancel order (buyer only, before shipment)
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.services.market import market_service
from app.services.market.market_service import MarketError
from app.utils.auth_identity import (
    UnresolvableJwtIdentityError,
    get_optional_current_user_id,
    get_required_current_user_id,
)
from app.utils.response import fail, ok

market_bp = Blueprint("market", __name__)


def _current_user_id() -> int:
    return get_required_current_user_id()


def _optional_current_user_id() -> int | None:
    return get_optional_current_user_id()


def _parse_pagination() -> tuple[int, int]:
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except (TypeError, ValueError):
        per_page = 20
    return page, per_page


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


@market_bp.post("/market/items")
@jwt_required()
def create_item():
    body = request.get_json(silent=True) or {}
    title = str(body.get("title", "")).strip()
    if not title:
        return fail(40001, "Field 'title' is required.")
    try:
        price_points = int(body.get("price_points", 0))
    except (TypeError, ValueError):
        return fail(40001, "'price_points' must be an integer.")

    try:
        result = market_service.create_item(
            seller_id=_current_user_id(),
            title=title,
            description=body.get("description") or None,
            image_urls_json=body.get("image_urls_json") or None,
            price_points=price_points,
        )
    except MarketError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result, status=201)


@market_bp.get("/market/items")
@jwt_required(optional=True)
def list_active_items():
    page, per_page = _parse_pagination()
    return ok(
        market_service.list_active_items(
            page,
            per_page,
            viewer_user_id=_optional_current_user_id(),
        )
    )


@market_bp.get("/market/items/mine")
@jwt_required()
def list_my_items():
    page, per_page = _parse_pagination()
    return ok(market_service.list_my_items(_current_user_id(), page, per_page))


@market_bp.get("/market/items/<int:item_id>")
@jwt_required(optional=True)
def get_item(item_id: int):
    try:
        return ok(
            market_service.get_item(
                item_id,
                viewer_user_id=_optional_current_user_id(),
            )
        )
    except MarketError as exc:
        return fail(exc.code, exc.message, exc.http_status)


@market_bp.post("/market/items/<int:item_id>/long-view")
@jwt_required()
def record_item_long_view(item_id: int):
    try:
        return ok(market_service.record_item_long_view(item_id, viewer_user_id=_current_user_id()))
    except MarketError as exc:
        return fail(exc.code, exc.message, exc.http_status)


@market_bp.delete("/market/items/<int:item_id>")
@jwt_required()
def remove_item(item_id: int):
    try:
        market_service.remove_item(item_id, operator_user_id=_current_user_id())
    except MarketError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok()


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


@market_bp.post("/market/orders")
@jwt_required()
def place_order():
    body = request.get_json(silent=True) or {}
    item_id = body.get("item_id")
    if item_id is None:
        return fail(40001, "Field 'item_id' is required.")
    try:
        item_id = int(item_id)
    except (TypeError, ValueError):
        return fail(40001, "'item_id' must be an integer.")

    try:
        result = market_service.place_order(
            buyer_id=_current_user_id(),
            item_id=item_id,
        )
    except MarketError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result, status=201)


@market_bp.get("/market/orders")
@jwt_required()
def list_my_orders():
    page, per_page = _parse_pagination()
    role = request.args.get("role", "all")
    if role not in ("buyer", "seller", "all"):
        return fail(40001, "'role' must be one of: buyer, seller, all.")
    return ok(market_service.list_my_orders(_current_user_id(), page, per_page, role=role))


@market_bp.patch("/market/orders/<int:order_id>/ship")
@jwt_required()
def ship_order(order_id: int):
    try:
        result = market_service.ship_order(order_id, operator_user_id=_current_user_id())
    except MarketError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result)


@market_bp.patch("/market/orders/<int:order_id>/confirm")
@jwt_required()
def confirm_receipt(order_id: int):
    try:
        result = market_service.confirm_receipt(order_id, operator_user_id=_current_user_id())
    except MarketError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result)


@market_bp.patch("/market/orders/<int:order_id>/cancel")
@jwt_required()
def cancel_order(order_id: int):
    try:
        result = market_service.cancel_order(order_id, operator_user_id=_current_user_id())
    except MarketError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result)


@market_bp.errorhandler(UnresolvableJwtIdentityError)
def handle_unresolvable_jwt_identity(exc: UnresolvableJwtIdentityError):
    return fail(40100, str(exc), 401)
