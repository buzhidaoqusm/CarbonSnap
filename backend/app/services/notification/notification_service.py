"""Notification business logic.

Design:
- `dispatch()` is the single low-level entry point; all other functions are
  domain-specific wrappers that build the correct payload and delegate.
- Notifications are fire-and-forget: failures do NOT raise to the caller.
  Any exception is silently logged so that the primary business operation
  (post like, order shipped, …) is never blocked by a notification error.
"""

import logging
from datetime import UTC

from app.repositories.forum import forum_repository
from app.repositories.notification import notification_repository

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    """Raised for user-facing notification errors (read / list)."""

    def __init__(self, message: str, code: int = 40001, http_status: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------


def _serialize_datetime_utc(value) -> str:
    if value is None:
        return ""

    if value.tzinfo is None:
        normalized = value.replace(tzinfo=UTC)
    else:
        normalized = value.astimezone(UTC)

    return normalized.isoformat().replace("+00:00", "Z")


def _build_body(n) -> str:
    event_type = str(getattr(n, "event_type", "") or "").strip().lower()
    title = str(getattr(n, "title", "") or "").strip()

    if event_type == "post_liked":
        return "A forum post you published received a like."
    if event_type == "post_commented":
        return "A forum post you published received a new comment."
    if event_type == "comment_liked":
        return "A forum comment you published received a like."
    if event_type == "comment_replied":
        return "A forum comment you published received a reply."
    if event_type == "item_purchased":
        return "An item you listed in the market was purchased."
    if event_type == "order_shipped":
        return "An order linked to your account has been shipped."
    if event_type == "order_completed":
        return "An order linked to your account has been completed."
    if event_type == "project_completed":
        return "A project you created or supported has reached completion."
    return title or "You have a new notification."


def _build_source_url(n) -> str:
    source_type = str(getattr(n, "source_type", "") or "").strip().lower()
    source_id = getattr(n, "source_id", None)
    event_type = str(getattr(n, "event_type", "") or "").strip().lower()

    if source_type == "forum_post":
        if source_id is None:
            return "/notification"
        return f"/forum/posts/{source_id}"

    if source_type == "forum_comment":
        if source_id is None:
            return "/notification"
        context = forum_repository.get_comment_notification_context(int(source_id))
        if context is None:
            return "/notification"
        post_id = context.get("post_id")
        if post_id is None:
            return "/notification"
        return f"/forum/posts/{post_id}#comment-{source_id}"

    if source_type == "order":
        return "/market/orders"

    if source_type == "project":
        return "/project"

    if event_type in {"item_purchased", "order_shipped", "order_completed"}:
        return "/market/orders"
    if event_type == "project_completed":
        return "/project"

    return "/notification"


def _serialize(n) -> dict:
    return {
        "id": n.id,
        "event_type": n.event_type,
        "source_type": n.source_type,
        "source_id": n.source_id,
        "title": n.title,
        "body": _build_body(n),
        "source_url": _build_source_url(n),
        "is_read": n.is_read,
        "created_at": _serialize_datetime_utc(n.created_at),
    }


# ---------------------------------------------------------------------------
# Core dispatch
# ---------------------------------------------------------------------------


def dispatch(
    *,
    recipient_user_id: int,
    event_type: str,
    source_type: str,
    source_id: int,
    title: str,
) -> None:
    """Persist a notification.  Swallows all exceptions so the calling
    business flow is never interrupted.
    """
    try:
        notification_repository.create_notification(
            recipient_user_id=recipient_user_id,
            event_type=event_type,
            source_type=source_type,
            source_id=source_id,
            title=title,
        )
    except Exception:
        logger.exception(
            "Failed to dispatch notification: event=%s recipient=%s source=%s/%s",
            event_type,
            recipient_user_id,
            source_type,
            source_id,
        )


# ---------------------------------------------------------------------------
# Domain event shortcuts
# (each helper documents its expected caller and what it notifies)
# ---------------------------------------------------------------------------


def on_post_liked(*, recipient_user_id: int, post_id: int, liker_username: str) -> None:
    """Called by forum service after a post is liked."""
    dispatch(
        recipient_user_id=recipient_user_id,
        event_type="post_liked",
        source_type="forum_post",
        source_id=post_id,
        title=f"{liker_username} liked your post.",
    )


def on_post_commented(*, recipient_user_id: int, post_id: int, commenter_username: str) -> None:
    """Called by forum service after a new top-level comment is created."""
    dispatch(
        recipient_user_id=recipient_user_id,
        event_type="post_commented",
        source_type="forum_post",
        source_id=post_id,
        title=f"{commenter_username} commented on your post.",
    )


def on_comment_replied(*, recipient_user_id: int, comment_id: int, replier_username: str) -> None:
    """Called by forum service after a reply-to-comment is created."""
    dispatch(
        recipient_user_id=recipient_user_id,
        event_type="comment_replied",
        source_type="forum_comment",
        source_id=comment_id,
        title=f"{replier_username} replied to your comment.",
    )


def on_comment_liked(*, recipient_user_id: int, comment_id: int, liker_username: str) -> None:
    """Called by forum service after a comment is liked."""
    dispatch(
        recipient_user_id=recipient_user_id,
        event_type="comment_liked",
        source_type="forum_comment",
        source_id=comment_id,
        title=f"{liker_username} liked your comment.",
    )


def on_order_shipped(*, recipient_user_id: int, order_id: int) -> None:
    """Called by market service after the seller marks an order as shipped."""
    dispatch(
        recipient_user_id=recipient_user_id,
        event_type="order_shipped",
        source_type="order",
        source_id=order_id,
        title="Your order has been shipped.",
    )


def on_order_completed(*, recipient_user_id: int, order_id: int) -> None:
    """Called by market service after the buyer confirms receipt."""
    dispatch(
        recipient_user_id=recipient_user_id,
        event_type="order_completed",
        source_type="order",
        source_id=order_id,
        title="Order completed. Points have been settled.",
    )


def on_item_purchased(
    *,
    recipient_user_id: int,
    order_id: int,
    item_title: str | None = None,
) -> None:
    """Called by market service after a buyer places an order."""
    dispatch(
        recipient_user_id=recipient_user_id,
        event_type="item_purchased",
        source_type="order",
        source_id=order_id,
        title=(
            f"Your item '{item_title}' has been purchased."
            if item_title
            else "Your item has been purchased."
        ),
    )


def on_project_completed(*, recipient_user_id: int, project_id: int, project_title: str) -> None:
    """Called by project service when a project reaches its points target."""
    dispatch(
        recipient_user_id=recipient_user_id,
        event_type="project_completed",
        source_type="project",
        source_id=project_id,
        title=f"Project '{project_title}' has been fully funded!",
    )


# ---------------------------------------------------------------------------
# Query operations (used by notification API routes)
# ---------------------------------------------------------------------------


def list_notifications(
    user_id: int, page: int, per_page: int, *, unread_only: bool = False
) -> dict:
    items, total = notification_repository.list_notifications_page(
        user_id, page, per_page, unread_only=unread_only
    )
    return {
        "items": [_serialize(n) for n in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "unread_count": notification_repository.count_unread(user_id),
    }


def get_unread_count(user_id: int) -> dict:
    return {"unread_count": notification_repository.count_unread(user_id)}


def mark_as_read(notification_id: int, *, user_id: int) -> dict:
    n = notification_repository.get_notification_by_id(notification_id, user_id=user_id)
    if n is None:
        raise NotificationError("Notification not found.", code=40400, http_status=404)
    n = notification_repository.mark_as_read(n)
    return _serialize(n)


def mark_all_as_read(user_id: int) -> dict:
    updated = notification_repository.mark_all_as_read(user_id)
    return {"updated": updated}
