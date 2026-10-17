"""C2C marketplace: items for sale and the orders that buy them."""

from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUserId, DbSession, OptionalUserId, PageParams
from app.api.errors import ApiError
from app.schemas.common import Envelope, ok
from app.schemas.market import (
    ItemIn,
    ItemOut,
    ItemPage,
    LongViewResult,
    OrderIn,
    OrderOut,
    OrderPage,
)
from app.services.market import market_service
from app.services.market.market_service import MarketError

router = APIRouter(prefix="/api/market", tags=["market"])


def _api_error(exc: MarketError) -> ApiError:
    return ApiError(exc.code, exc.message, exc.http_status)


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


@router.post("/items", status_code=201, response_model=Envelope[ItemOut])
def create_item(user_id: CurrentUserId, session: DbSession, body: ItemIn | None = None):
    body = body or ItemIn()
    title = body.title.strip()
    if not title:
        raise ApiError(40001, "Field 'title' is required.")
    try:
        price_points = int(body.price_points)
    except (TypeError, ValueError) as exc:
        raise ApiError(40001, "'price_points' must be an integer.") from exc
    try:
        result = market_service.create_item(
            session,
            seller_id=user_id,
            title=title,
            description=body.description or None,
            image_urls_json=body.image_urls_json or None,
            price_points=price_points,
        )
    except MarketError as exc:
        raise _api_error(exc) from exc
    return ok(result)


@router.get("/items", response_model=Envelope[ItemPage])
def list_active_items(session: DbSession, viewer: OptionalUserId, paging: PageParams):
    return ok(
        market_service.list_active_items(
            session, paging.page, paging.per_page, viewer_user_id=viewer
        )
    )


# Registered before /items/{item_id}, which would otherwise try to read "mine"
# as an id.
@router.get("/items/mine", response_model=Envelope[ItemPage])
def list_my_items(user_id: CurrentUserId, session: DbSession, paging: PageParams):
    return ok(market_service.list_my_items(session, user_id, paging.page, paging.per_page))


@router.get("/items/{item_id}", response_model=Envelope[ItemOut])
def get_item(item_id: int, session: DbSession, viewer: OptionalUserId):
    try:
        return ok(market_service.get_item(session, item_id, viewer_user_id=viewer))
    except MarketError as exc:
        raise _api_error(exc) from exc


# reason is only present when nothing was tracked, as before.
@router.post(
    "/items/{item_id}/long-view",
    response_model=Envelope[LongViewResult],
    response_model_exclude_none=True,
)
def record_item_long_view(item_id: int, user_id: CurrentUserId, session: DbSession):
    try:
        result = market_service.record_item_long_view(session, item_id, viewer_user_id=user_id)
    except MarketError as exc:
        raise _api_error(exc) from exc
    return ok(result)


@router.delete("/items/{item_id}", response_model=Envelope[dict[str, Any]])
def remove_item(item_id: int, user_id: CurrentUserId, session: DbSession):
    try:
        market_service.remove_item(session, item_id, operator_user_id=user_id)
    except MarketError as exc:
        raise _api_error(exc) from exc
    return ok({})


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


@router.post("/orders", status_code=201, response_model=Envelope[OrderOut])
def place_order(user_id: CurrentUserId, session: DbSession, body: OrderIn | None = None):
    raw_item_id = (body or OrderIn()).item_id
    if raw_item_id is None:
        raise ApiError(40001, "Field 'item_id' is required.")
    try:
        item_id = int(raw_item_id)
    except (TypeError, ValueError) as exc:
        raise ApiError(40001, "'item_id' must be an integer.") from exc
    try:
        result = market_service.place_order(session, buyer_id=user_id, item_id=item_id)
    except MarketError as exc:
        raise _api_error(exc) from exc
    return ok(result)


@router.get("/orders", response_model=Envelope[OrderPage])
def list_my_orders(
    user_id: CurrentUserId, session: DbSession, paging: PageParams, role: str = "all"
):
    # A plain str, not a Literal: the message stays the one users have seen.
    if role not in ("buyer", "seller", "all"):
        raise ApiError(40001, "'role' must be one of: buyer, seller, all.")
    return ok(
        market_service.list_my_orders(session, user_id, paging.page, paging.per_page, role=role)
    )


@router.patch("/orders/{order_id}/ship", response_model=Envelope[OrderOut])
def ship_order(order_id: int, user_id: CurrentUserId, session: DbSession):
    try:
        return ok(market_service.ship_order(session, order_id, operator_user_id=user_id))
    except MarketError as exc:
        raise _api_error(exc) from exc


@router.patch("/orders/{order_id}/confirm", response_model=Envelope[OrderOut])
def confirm_receipt(order_id: int, user_id: CurrentUserId, session: DbSession):
    try:
        return ok(market_service.confirm_receipt(session, order_id, operator_user_id=user_id))
    except MarketError as exc:
        raise _api_error(exc) from exc


@router.patch("/orders/{order_id}/cancel", response_model=Envelope[OrderOut])
def cancel_order(order_id: int, user_id: CurrentUserId, session: DbSession):
    try:
        return ok(market_service.cancel_order(session, order_id, operator_user_id=user_id))
    except MarketError as exc:
        raise _api_error(exc) from exc
