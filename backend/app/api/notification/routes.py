"""Notification API Blueprint.

Endpoints:
  GET   /api/notifications                 List notifications (paginated)
  GET   /api/notifications/unread-count    Unread badge count
  PATCH /api/notifications/<id>/read       Mark one notification as read
  PATCH /api/notifications/read-all        Mark all notifications as read
"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.notification.notification_service import NotificationError
from app.services.notification import notification_service
from app.utils.response import fail, ok

notification_bp = Blueprint("notification", __name__)


def _current_user_id() -> int:
    return int(get_jwt_identity())


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
# Routes
# ---------------------------------------------------------------------------

@notification_bp.get("/notifications")
@jwt_required()
def list_notifications():
    page, per_page = _parse_pagination()
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    result = notification_service.list_notifications(
        _current_user_id(), page, per_page, unread_only=unread_only
    )
    return ok(result)


@notification_bp.get("/notifications/unread-count")
@jwt_required()
def unread_count():
    return ok(notification_service.get_unread_count(_current_user_id()))


@notification_bp.patch("/notifications/<int:notification_id>/read")
@jwt_required()
def mark_as_read(notification_id: int):
    try:
        result = notification_service.mark_as_read(
            notification_id, user_id=_current_user_id()
        )
    except NotificationError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result)


@notification_bp.patch("/notifications/read-all")
@jwt_required()
def mark_all_as_read():
    result = notification_service.mark_all_as_read(_current_user_id())
    return ok(result)
