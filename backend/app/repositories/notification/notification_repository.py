from sqlalchemy import func, select

from app.extensions.db import db
from app.models.notification import Notification


def create_notification(
    *,
    recipient_user_id: int,
    event_type: str,
    source_type: str,
    source_id: int,
    title: str,
) -> Notification:
    notification = Notification(
        recipient_user_id=recipient_user_id,
        event_type=event_type,
        source_type=source_type,
        source_id=source_id,
        title=title,
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def get_notification_by_id(notification_id: int, *, user_id: int) -> Notification | None:
    """Return a notification only if it belongs to the given user."""
    return db.session.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_user_id == user_id,
        )
    )


def list_notifications_page(
    user_id: int,
    page: int,
    per_page: int,
    *,
    unread_only: bool = False,
) -> tuple[list[Notification], int]:
    base = select(Notification).where(Notification.recipient_user_id == user_id)
    if unread_only:
        base = base.where(Notification.is_read.is_(False))

    total = db.session.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.session.scalars(
        base.order_by(Notification.created_at.desc()).limit(per_page).offset((page - 1) * per_page)
    ).all()
    return list(items), total


def count_unread(user_id: int) -> int:
    return (
        db.session.scalar(
            select(func.count(Notification.id)).where(
                Notification.recipient_user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )


def mark_as_read(notification: Notification) -> Notification:
    """Mark a single notification as read. Caller must own it."""
    notification.is_read = True
    db.session.commit()
    return notification


def mark_all_as_read(user_id: int) -> int:
    """Mark every unread notification for a user as read.
    Returns the number of rows updated.
    """
    rows = db.session.scalars(
        select(Notification).where(
            Notification.recipient_user_id == user_id,
            Notification.is_read.is_(False),
        )
    ).all()
    for n in rows:
        n.is_read = True
    db.session.commit()
    return len(rows)
