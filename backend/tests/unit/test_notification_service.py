"""Unit tests for services/notification/notification_service.py."""

import pytest
from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.user import User
from app.services.notification import notification_service
from app.services.notification.notification_service import NotificationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username="alice", email="alice@example.com"):
    user = User(username=username, email=email, password_hash=generate_password_hash("pw"))
    db.session.add(user)
    db.session.flush()
    return user


# ---------------------------------------------------------------------------
# dispatch / domain shortcuts
# ---------------------------------------------------------------------------

class TestDispatch:
    def test_dispatch_creates_notification(self):
        user = _make_user()
        notification_service.dispatch(
            recipient_user_id=user.id,
            event_type="post_liked",
            source_type="forum_post",
            source_id=1,
            title="Someone liked your post.",
        )
        result = notification_service.list_notifications(user.id, page=1, per_page=10)
        assert result["total"] == 1
        assert result["items"][0]["event_type"] == "post_liked"

    def test_dispatch_does_not_raise_on_invalid_user(self):
        """dispatch() swallows exceptions — must never propagate."""
        notification_service.dispatch(
            recipient_user_id=99999,
            event_type="post_liked",
            source_type="forum_post",
            source_id=1,
            title="Ghost notification.",
        )  # should not raise


class TestDomainShortcuts:
    def test_on_post_liked(self):
        user = _make_user()
        notification_service.on_post_liked(
            recipient_user_id=user.id, post_id=42, liker_username="bob"
        )
        result = notification_service.list_notifications(user.id, 1, 10)
        assert result["total"] == 1
        n = result["items"][0]
        assert n["event_type"] == "post_liked"
        assert n["source_type"] == "forum_post"
        assert n["source_id"] == 42
        assert "bob" in n["title"]

    def test_on_post_commented(self):
        user = _make_user()
        notification_service.on_post_commented(
            recipient_user_id=user.id, post_id=7, commenter_username="carol"
        )
        result = notification_service.list_notifications(user.id, 1, 10)
        n = result["items"][0]
        assert n["event_type"] == "post_commented"
        assert "carol" in n["title"]

    def test_on_comment_replied(self):
        user = _make_user()
        notification_service.on_comment_replied(
            recipient_user_id=user.id, comment_id=5, replier_username="dave"
        )
        result = notification_service.list_notifications(user.id, 1, 10)
        n = result["items"][0]
        assert n["event_type"] == "comment_replied"
        assert n["source_type"] == "forum_comment"

    def test_on_order_shipped(self):
        user = _make_user()
        notification_service.on_order_shipped(recipient_user_id=user.id, order_id=10)
        result = notification_service.list_notifications(user.id, 1, 10)
        n = result["items"][0]
        assert n["event_type"] == "order_shipped"
        assert n["source_type"] == "order"

    def test_on_order_completed(self):
        user = _make_user()
        notification_service.on_order_completed(recipient_user_id=user.id, order_id=11)
        result = notification_service.list_notifications(user.id, 1, 10)
        n = result["items"][0]
        assert n["event_type"] == "order_completed"

    def test_on_project_completed(self):
        user = _make_user()
        notification_service.on_project_completed(
            recipient_user_id=user.id, project_id=3, project_title="Green Earth"
        )
        result = notification_service.list_notifications(user.id, 1, 10)
        n = result["items"][0]
        assert n["event_type"] == "project_completed"
        assert "Green Earth" in n["title"]


# ---------------------------------------------------------------------------
# Query operations
# ---------------------------------------------------------------------------

class TestListNotifications:
    def test_pagination(self):
        user = _make_user()
        for i in range(5):
            notification_service.dispatch(
                recipient_user_id=user.id,
                event_type="post_liked",
                source_type="forum_post",
                source_id=i,
                title=f"Notification {i}",
            )
        result = notification_service.list_notifications(user.id, page=1, per_page=3)
        assert result["total"] == 5
        assert len(result["items"]) == 3

    def test_unread_only_filter(self):
        user = _make_user()
        for i in range(3):
            notification_service.dispatch(
                recipient_user_id=user.id,
                event_type="post_liked",
                source_type="forum_post",
                source_id=i,
                title=f"N{i}",
            )
        # Mark one as read.
        all_notifs = notification_service.list_notifications(user.id, 1, 10)
        first_id = all_notifs["items"][0]["id"]
        notification_service.mark_as_read(first_id, user_id=user.id)

        unread = notification_service.list_notifications(user.id, 1, 10, unread_only=True)
        assert unread["total"] == 2

    def test_unread_count_in_response(self):
        user = _make_user()
        for i in range(4):
            notification_service.dispatch(
                recipient_user_id=user.id,
                event_type="post_liked",
                source_type="forum_post",
                source_id=i,
                title=f"N{i}",
            )
        result = notification_service.list_notifications(user.id, 1, 10)
        assert result["unread_count"] == 4


class TestGetUnreadCount:
    def test_zero_when_no_notifications(self):
        user = _make_user()
        assert notification_service.get_unread_count(user.id)["unread_count"] == 0

    def test_decrements_after_mark_all_read(self):
        user = _make_user()
        for i in range(3):
            notification_service.dispatch(
                recipient_user_id=user.id,
                event_type="post_liked",
                source_type="forum_post",
                source_id=i,
                title=f"N{i}",
            )
        notification_service.mark_all_as_read(user.id)
        assert notification_service.get_unread_count(user.id)["unread_count"] == 0


class TestMarkAsRead:
    def test_mark_single_notification(self):
        user = _make_user()
        notification_service.dispatch(
            recipient_user_id=user.id,
            event_type="post_liked",
            source_type="forum_post",
            source_id=1,
            title="Hi",
        )
        notifs = notification_service.list_notifications(user.id, 1, 10)
        nid = notifs["items"][0]["id"]
        result = notification_service.mark_as_read(nid, user_id=user.id)
        assert result["is_read"] is True

    def test_cannot_mark_other_users_notification(self):
        u1 = _make_user("u1", "u1@x.com")
        u2 = _make_user("u2", "u2@x.com")
        notification_service.dispatch(
            recipient_user_id=u1.id,
            event_type="post_liked",
            source_type="forum_post",
            source_id=1,
            title="Hi",
        )
        notifs = notification_service.list_notifications(u1.id, 1, 10)
        nid = notifs["items"][0]["id"]
        with pytest.raises(NotificationError) as exc_info:
            notification_service.mark_as_read(nid, user_id=u2.id)
        assert exc_info.value.http_status == 404


class TestMarkAllAsRead:
    def test_returns_updated_count(self):
        user = _make_user()
        for i in range(3):
            notification_service.dispatch(
                recipient_user_id=user.id,
                event_type="post_liked",
                source_type="forum_post",
                source_id=i,
                title=f"N{i}",
            )
        result = notification_service.mark_all_as_read(user.id)
        assert result["updated"] == 3

    def test_idempotent_second_call(self):
        user = _make_user()
        notification_service.dispatch(
            recipient_user_id=user.id,
            event_type="post_liked",
            source_type="forum_post",
            source_id=1,
            title="Hi",
        )
        notification_service.mark_all_as_read(user.id)
        result = notification_service.mark_all_as_read(user.id)
        assert result["updated"] == 0
