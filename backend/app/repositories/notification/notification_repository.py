from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    session: Session,
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
    session.add(notification)
    session.commit()
    return notification


def get_notification_by_id(
    session: Session, notification_id: int, *, user_id: int
) -> Notification | None:
    """Return a notification only if it belongs to the given user."""
    return session.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_user_id == user_id,
        )
    )


def list_notifications_page(
    session: Session,
    user_id: int,
    page: int,
    per_page: int,
    *,
    unread_only: bool = False,
) -> tuple[list[Notification], int]:
    base = select(Notification).where(Notification.recipient_user_id == user_id)
    if unread_only:
        base = base.where(Notification.is_read.is_(False))

    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = session.scalars(
        base.order_by(Notification.created_at.desc()).limit(per_page).offset((page - 1) * per_page)
    ).all()
    return list(items), total


def count_unread(session: Session, user_id: int) -> int:
    return (
        session.scalar(
            select(func.count(Notification.id)).where(
                Notification.recipient_user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )


def mark_as_read(session: Session, notification: Notification) -> Notification:
    """Mark a single notification as read. Caller must own it."""
    notification.is_read = True
    session.commit()
    return notification


def mark_all_as_read(session: Session, user_id: int) -> int:
    """Mark every unread notification for a user as read.
    Returns the number of rows updated.
    """
    rows = session.scalars(
        select(Notification).where(
            Notification.recipient_user_id == user_id,
            Notification.is_read.is_(False),
        )
    ).all()
    for n in rows:
        n.is_read = True
    session.commit()
    return len(rows)
