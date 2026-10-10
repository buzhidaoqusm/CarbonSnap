"""Notification API.

Endpoints:
  GET   /api/notifications                 List notifications (paginated)
  GET   /api/notifications/unread-count    Unread badge count
  PATCH /api/notifications/<id>/read       Mark one notification as read
  PATCH /api/notifications/read-all        Mark all notifications as read
"""

from fastapi import APIRouter

from app.api.deps import CurrentUserId, DbSession
from app.api.errors import ApiError
from app.schemas.common import Envelope, ok
from app.schemas.notification import (
    MarkAllResult,
    NotificationOut,
    NotificationPage,
    UnreadCount,
)
from app.services.notification import notification_service
from app.services.notification.notification_service import NotificationError

router = APIRouter(prefix="/api/notifications", tags=["notification"])


# Plain def, not async def: the database calls block, so FastAPI runs these
# in its thread pool instead of on the event loop.
@router.get("", response_model=Envelope[NotificationPage])
def list_notifications(
    user_id: CurrentUserId,
    session: DbSession,
    page: int = 1,
    per_page: int = 20,
    unread_only: bool = False,
):
    # Out-of-range values are clamped, as the Flask route did.
    page = max(1, page)
    per_page = min(100, max(1, per_page))
    result = notification_service.list_notifications(
        session, user_id, page, per_page, unread_only=unread_only
    )
    return ok(result)


@router.get("/unread-count", response_model=Envelope[UnreadCount])
def unread_count(user_id: CurrentUserId, session: DbSession):
    return ok(notification_service.get_unread_count(session, user_id))


@router.patch("/{notification_id}/read", response_model=Envelope[NotificationOut])
def mark_as_read(notification_id: int, user_id: CurrentUserId, session: DbSession):
    try:
        result = notification_service.mark_as_read(session, notification_id, user_id=user_id)
    except NotificationError as exc:
        raise ApiError(exc.code, exc.message, exc.http_status) from exc
    return ok(result)


@router.patch("/read-all", response_model=Envelope[MarkAllResult])
def mark_all_as_read(user_id: CurrentUserId, session: DbSession):
    return ok(notification_service.mark_all_as_read(session, user_id))
