from sqlalchemy import func, or_, select

from app.extensions.db import db
from app.models.market import MarketItem, Order

# ---------------------------------------------------------------------------
# Market Items
# ---------------------------------------------------------------------------


def create_item(
    *,
    seller_id: int,
    title: str,
    description: str | None,
    image_urls_json: str | None,
    price_points: int,
) -> MarketItem:
    item = MarketItem(
        seller_id=seller_id,
        title=title,
        description=description,
        image_urls_json=image_urls_json,
        price_points=price_points,
    )
    db.session.add(item)
    db.session.commit()
    return item


def get_item_by_id(item_id: int) -> MarketItem | None:
    return db.session.get(MarketItem, item_id)


def list_active_items_page(page: int, per_page: int) -> tuple[list[MarketItem], int]:
    """Return paginated active (on-sale) items, newest first."""
    base = select(MarketItem).where(MarketItem.status == "active")
    total = db.session.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.session.scalars(
        base.order_by(MarketItem.created_at.desc()).limit(per_page).offset((page - 1) * per_page)
    ).all()
    return list(items), total


def list_all_active_items() -> list[MarketItem]:
    return list(
        db.session.scalars(
            select(MarketItem)
            .where(MarketItem.status == "active")
            .order_by(MarketItem.created_at.desc(), MarketItem.id.desc())
        ).all()
    )


def list_all_active_items_excluding_seller(*, seller_id: int) -> list[MarketItem]:
    return list(
        db.session.scalars(
            select(MarketItem)
            .where(
                MarketItem.status == "active",
                MarketItem.seller_id != seller_id,
            )
            .order_by(MarketItem.created_at.desc(), MarketItem.id.desc())
        ).all()
    )


def list_items_by_seller(seller_id: int, page: int, per_page: int) -> tuple[list[MarketItem], int]:
    """Return all items (any status) listed by a seller, newest first."""
    base = select(MarketItem).where(MarketItem.seller_id == seller_id)
    total = db.session.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.session.scalars(
        base.order_by(MarketItem.created_at.desc()).limit(per_page).offset((page - 1) * per_page)
    ).all()
    return list(items), total


def update_item_status(item: MarketItem, status: str) -> MarketItem:
    """Update item status in-place.
    Does NOT commit — caller handles the transaction boundary.
    """
    item.status = status
    return item


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


def create_order(
    *,
    item_id: int,
    buyer_id: int,
    seller_id: int,
    price_points: int,
) -> Order:
    order = Order(
        item_id=item_id,
        buyer_id=buyer_id,
        seller_id=seller_id,
        price_points=price_points,
    )
    db.session.add(order)
    return order


def get_order_by_id(order_id: int) -> Order | None:
    return db.session.get(Order, order_id)


def update_order_status(order: Order, status: str) -> Order:
    """Update order status in-place.
    Does NOT commit — caller handles the transaction boundary.
    """
    order.status = status
    return order


def list_orders_by_user(user_id: int, page: int, per_page: int) -> tuple[list[Order], int]:
    """Return orders where the user is the buyer OR seller, newest first."""
    base = select(Order).where(or_(Order.buyer_id == user_id, Order.seller_id == user_id))
    total = db.session.scalar(select(func.count()).select_from(base.subquery())) or 0
    orders = db.session.scalars(
        base.order_by(Order.created_at.desc()).limit(per_page).offset((page - 1) * per_page)
    ).all()
    return list(orders), total


def list_orders_as_buyer(buyer_id: int, page: int, per_page: int) -> tuple[list[Order], int]:
    base = select(Order).where(Order.buyer_id == buyer_id)
    total = db.session.scalar(select(func.count()).select_from(base.subquery())) or 0
    orders = db.session.scalars(
        base.order_by(Order.created_at.desc()).limit(per_page).offset((page - 1) * per_page)
    ).all()
    return list(orders), total


def list_orders_as_seller(seller_id: int, page: int, per_page: int) -> tuple[list[Order], int]:
    base = select(Order).where(Order.seller_id == seller_id)
    total = db.session.scalar(select(func.count()).select_from(base.subquery())) or 0
    orders = db.session.scalars(
        base.order_by(Order.created_at.desc()).limit(per_page).offset((page - 1) * per_page)
    ).all()
    return list(orders), total


def count_orders_for_item(item_id: int, *, statuses: list[str] | None = None) -> int:
    stmt = select(func.count(Order.id)).where(Order.item_id == item_id)
    if statuses:
        normalized_statuses = [
            str(status).strip().lower() for status in statuses if str(status).strip()
        ]
        if normalized_statuses:
            stmt = stmt.where(Order.status.in_(normalized_statuses))
    return db.session.scalar(stmt) or 0


def list_ordered_item_ids_by_buyer(buyer_id: int) -> set[int]:
    return {
        int(item_id)
        for item_id in db.session.scalars(
            select(Order.item_id)
            .where(Order.buyer_id == buyer_id)
            .order_by(Order.created_at.desc(), Order.id.desc())
        ).all()
        if item_id is not None
    }


def list_order_counts_for_item_ids(
    item_ids: list[int],
    *,
    statuses: list[str] | None = None,
) -> dict[int, int]:
    normalized_item_ids = [int(item_id) for item_id in item_ids if item_id is not None]
    if not normalized_item_ids:
        return {}

    stmt = (
        select(Order.item_id, func.count(Order.id))
        .where(Order.item_id.in_(normalized_item_ids))
        .group_by(Order.item_id)
    )
    if statuses:
        normalized_statuses = [
            str(status).strip().lower() for status in statuses if str(status).strip()
        ]
        if normalized_statuses:
            stmt = stmt.where(Order.status.in_(normalized_statuses))

    rows = db.session.execute(stmt).all()
    return {int(item_id): int(count) for item_id, count in rows if item_id is not None}
