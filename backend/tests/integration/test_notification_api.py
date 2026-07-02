"""Integration tests for Notification API endpoints."""

import json
import pytest

from app.services.notification import notification_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_notifications(user_id: int, count: int = 3):
    """Directly call service to create N notifications for a user."""
    for i in range(count):
        notification_service.dispatch(
            recipient_user_id=user_id,
            event_type="post_liked",
            source_type="forum_post",
            source_id=i + 1,
            title=f"Notification {i}",
        )


def _post_json(client, url, data, headers=None):
    return client.post(url, data=json.dumps(data), content_type="application/json", headers=headers)


def _patch_json(client, url, data=None, headers=None):
    return client.patch(
        url,
        data=json.dumps(data or {}),
        content_type="application/json",
        headers=headers,
    )


def _create_forum_post(client, headers, title="Hello", content="World"):
    resp = _post_json(client, "/api/forum/posts", {"title": title, "content": content}, headers)
    assert resp.status_code == 201
    return resp.get_json()["data"]


def _create_forum_comment(client, headers, post_id, content="Nice!", parent_comment_id=None):
    body = {"content": content}
    if parent_comment_id is not None:
        body["parent_comment_id"] = parent_comment_id
    resp = _post_json(client, f"/api/forum/posts/{post_id}/comments", body, headers)
    assert resp.status_code == 201
    return resp.get_json()["data"]


# ---------------------------------------------------------------------------
# GET /api/notifications
# ---------------------------------------------------------------------------

class TestListNotifications:
    def test_returns_own_notifications(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        _seed_notifications(user_id, 3)
        resp = client.get("/api/notifications", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total"] == 3
        assert len(data["items"]) == 3
        first = data["items"][0]
        assert "body" in first
        assert "source_url" in first

    def test_pagination(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        _seed_notifications(user_id, 5)
        resp = client.get("/api/notifications?page=1&per_page=2", headers=headers)
        data = resp.get_json()["data"]
        assert data["total"] == 5
        assert len(data["items"]) == 2

    def test_created_at_is_serialized_with_utc_designator(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        _seed_notifications(user_id, 1)

        resp = client.get("/api/notifications", headers=headers)
        item = resp.get_json()["data"]["items"][0]

        assert item["created_at"].endswith("Z")

    def test_unread_only_filter(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        _seed_notifications(user_id, 4)
        # Mark first one as read via API.
        all_resp = client.get("/api/notifications", headers=headers)
        first_id = all_resp.get_json()["data"]["items"][0]["id"]
        _patch_json(client, f"/api/notifications/{first_id}/read", headers=headers)

        resp = client.get("/api/notifications?unread_only=true", headers=headers)
        assert resp.get_json()["data"]["total"] == 3

    def test_unread_count_in_response(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        _seed_notifications(user_id, 2)
        resp = client.get("/api/notifications", headers=headers)
        assert resp.get_json()["data"]["unread_count"] == 2

    def test_unauthenticated_returns_401(self, client):
        assert client.get("/api/notifications").status_code == 401

    def test_users_cannot_see_each_others_notifications(self, client, make_auth_headers):
        u1_id, h1 = make_auth_headers()
        _u2_id, h2 = make_auth_headers()
        _seed_notifications(u1_id, 3)
        resp = client.get("/api/notifications", headers=h2)
        assert resp.get_json()["data"]["total"] == 0

    def test_comment_notification_routes_to_source_post_anchor(self, client, make_auth_headers):
        _, author_headers = make_auth_headers(username="author")
        _, commenter_headers = make_auth_headers(username="commenter")
        post = _create_forum_post(client, author_headers, title="Forum seed", content="Body")
        comment = _create_forum_comment(client, commenter_headers, post["id"], content="Nice post")

        notification_service.dispatch(
            recipient_user_id=post["author_id"],
            event_type="comment_liked",
            source_type="forum_comment",
            source_id=comment["id"],
            title="commenter liked your comment.",
        )

        resp = client.get("/api/notifications", headers=author_headers)
        item = resp.get_json()["data"]["items"][0]
        assert item["source_url"] == f"/forum/posts/{post['id']}#comment-{comment['id']}"
        assert item["body"] == "A forum comment you published received a like."

    def test_forum_post_notifications_route_to_post_page(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        notification_service.dispatch(
            recipient_user_id=user_id,
            event_type="post_commented",
            source_type="forum_post",
            source_id=77,
            title="Someone commented on your post.",
        )

        resp = client.get("/api/notifications", headers=headers)
        item = resp.get_json()["data"]["items"][0]
        assert item["source_url"] == "/forum/posts/77"
        assert item["body"] == "A forum post you published received a new comment."

    def test_missing_comment_source_falls_back_to_notification(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        notification_service.dispatch(
            recipient_user_id=user_id,
            event_type="comment_replied",
            source_type="forum_comment",
            source_id=99999,
            title="reply",
        )

        resp = client.get("/api/notifications", headers=headers)
        item = resp.get_json()["data"]["items"][0]
        assert item["source_url"] == "/notification"

    def test_project_completed_uses_project_route_and_body(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        notification_service.dispatch(
            recipient_user_id=user_id,
            event_type="project_completed",
            source_type="project",
            source_id=12,
            title="Project completed",
        )

        resp = client.get("/api/notifications", headers=headers)
        item = resp.get_json()["data"]["items"][0]
        assert item["source_url"] == "/project"
        assert item["body"] == "A project you created or supported has reached completion."

    def test_item_and_order_notifications_use_market_route(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        notification_service.dispatch(
            recipient_user_id=user_id,
            event_type="item_purchased",
            source_type="order",
            source_id=21,
            title="Your item has been purchased.",
        )
        notification_service.dispatch(
            recipient_user_id=user_id,
            event_type="order_completed",
            source_type="order",
            source_id=22,
            title="Order completed. Points have been settled.",
        )

        resp = client.get("/api/notifications", headers=headers)
        items = resp.get_json()["data"]["items"]
        assert items[0]["source_url"] == "/market/orders"
        assert items[1]["source_url"] == "/market/orders"
        assert items[0]["body"] == "An order linked to your account has been completed."
        assert items[1]["body"] == "An item you listed in the market was purchased."


# ---------------------------------------------------------------------------
# GET /api/notifications/unread-count
# ---------------------------------------------------------------------------

class TestUnreadCount:
    def test_zero_initially(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        resp = client.get("/api/notifications/unread-count", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["unread_count"] == 0

    def test_increments_with_new_notifications(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        _seed_notifications(user_id, 3)
        resp = client.get("/api/notifications/unread-count", headers=headers)
        assert resp.get_json()["data"]["unread_count"] == 3


# ---------------------------------------------------------------------------
# PATCH /api/notifications/<id>/read
# ---------------------------------------------------------------------------

class TestMarkAsRead:
    def test_mark_single_notification(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        _seed_notifications(user_id, 1)
        notifs = client.get("/api/notifications", headers=headers).get_json()["data"]["items"]
        nid = notifs[0]["id"]
        resp = _patch_json(client, f"/api/notifications/{nid}/read", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["is_read"] is True

    def test_cannot_mark_other_users_notification(self, client, make_auth_headers):
        u1_id, h1 = make_auth_headers()
        _u2_id, h2 = make_auth_headers()
        _seed_notifications(u1_id, 1)
        nid = client.get("/api/notifications", headers=h1).get_json()["data"]["items"][0]["id"]
        resp = _patch_json(client, f"/api/notifications/{nid}/read", headers=h2)
        assert resp.status_code == 404

    def test_nonexistent_notification_returns_404(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        resp = _patch_json(client, "/api/notifications/99999/read", headers=headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/notifications/read-all
# ---------------------------------------------------------------------------

class TestMarkAllAsRead:
    def test_marks_all_as_read(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        _seed_notifications(user_id, 4)
        resp = _patch_json(client, "/api/notifications/read-all", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["updated"] == 4
        # Unread count should now be 0.
        count_resp = client.get("/api/notifications/unread-count", headers=headers)
        assert count_resp.get_json()["data"]["unread_count"] == 0

    def test_idempotent(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        _seed_notifications(user_id, 2)
        _patch_json(client, "/api/notifications/read-all", headers=headers)
        resp = _patch_json(client, "/api/notifications/read-all", headers=headers)
        assert resp.get_json()["data"]["updated"] == 0

    def test_unauthenticated_returns_401(self, client):
        assert client.patch("/api/notifications/read-all").status_code == 401
