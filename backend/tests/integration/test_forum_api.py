"""Integration tests for Forum API endpoints.

Tests go through the full HTTP stack: Flask test client -> Blueprint -> Service -> Repository -> DB.
"""

import json
import pytest
from flask_jwt_extended import create_access_token

from app.extensions.db import db
from app.models.user import User
from app.services.forum import forum_service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _post_json(client, url, data, headers=None):
    return client.post(url, data=json.dumps(data), content_type="application/json", headers=headers)


def _put_json(client, url, data, headers=None):
    return client.put(url, data=json.dumps(data), content_type="application/json", headers=headers)


def _create_post(client, headers, title="Hello", content="World"):
    resp = _post_json(client, "/api/forum/posts", {"title": title, "content": content}, headers)
    assert resp.status_code == 201
    return resp.get_json()["data"]


def _create_comment(client, headers, post_id, content="Nice!", parent_comment_id=None):
    body = {"content": content}
    if parent_comment_id is not None:
        body["parent_comment_id"] = parent_comment_id
    resp = _post_json(client, f"/api/forum/posts/{post_id}/comments", body, headers)
    assert resp.status_code == 201
    return resp.get_json()["data"]


def _get_notifications(client, headers):
    resp = client.get("/api/notifications", headers=headers)
    assert resp.status_code == 200
    return resp.get_json()["data"]["items"]


_ONE_PIXEL_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9v7uoAAAAASUVORK5CYII="
)


# ---------------------------------------------------------------------------
# POST /api/forum/uploads
# ---------------------------------------------------------------------------

class TestUploadForumImage:
    def test_authenticated_user_can_upload_image(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        resp = _post_json(client, "/api/forum/uploads", {"image": _ONE_PIXEL_PNG}, headers)
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["url"].startswith("/api/uploads/forum/")

    def test_invalid_image_returns_400(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        resp = _post_json(client, "/api/forum/uploads", {"image": "not-a-data-url"}, headers)
        assert resp.status_code == 400

    def test_upload_requires_auth(self, client):
        resp = _post_json(client, "/api/forum/uploads", {"image": _ONE_PIXEL_PNG})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/forum/posts
# ---------------------------------------------------------------------------

class TestCreatePost:
    def test_authenticated_user_can_create_post(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        resp = _post_json(client, "/api/forum/posts", {"title": "T", "content": "C"}, headers)
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["title"] == "T"
        assert data["author_id"] == user_id

    def test_missing_title_returns_400(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        resp = _post_json(client, "/api/forum/posts", {"content": "C"}, headers)
        assert resp.status_code == 400

    def test_missing_content_returns_400(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        resp = _post_json(client, "/api/forum/posts", {"title": "T"}, headers)
        assert resp.status_code == 400

    def test_unauthenticated_returns_401(self, client):
        resp = _post_json(client, "/api/forum/posts", {"title": "T", "content": "C"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/forum/posts
# ---------------------------------------------------------------------------

class TestListPosts:
    def test_returns_paginated_list(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        for i in range(3):
            _create_post(client, headers, title=f"T{i}", content="C")
        resp = client.get("/api/forum/posts?page=1&per_page=2")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total"] == 3
        assert len(data["items"]) == 2

    def test_anonymous_access_allowed(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        _create_post(client, headers)
        resp = client.get("/api/forum/posts")
        assert resp.status_code == 200

    def test_liked_by_user_present_when_authenticated(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        _create_post(client, headers)
        resp = client.get("/api/forum/posts", headers=headers)
        item = resp.get_json()["data"]["items"][0]
        assert "liked_by_user" in item

    def test_list_posts_includes_author_profile_fields(self, client, make_auth_headers):
        _, headers = make_auth_headers(username="eco_writer")
        _create_post(client, headers, title="Seed", content="Real forum content")

        resp = client.get("/api/forum/posts")

        assert resp.status_code == 200
        item = resp.get_json()["data"]["items"][0]
        assert item["author_username"] == "eco_writer"
        assert "author_avatar_url" in item

    def test_authenticated_list_uses_personalized_backend_order(self, client, make_auth_headers, monkeypatch):
        _, headers = make_auth_headers()
        first = _create_post(client, headers, title="First", content="C")
        second = _create_post(client, headers, title="Second", content="C")

        monkeypatch.setattr(
            forum_service,
            "rank_posts_for_user",
            lambda posts, user_id: list(reversed(posts)),
        )

        resp = client.get("/api/forum/posts", headers=headers)
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.get_json()["data"]["items"]]
        assert ids[:2] == [first["id"], second["id"]]

    def test_authenticated_list_slices_after_global_ranking_for_later_pages(self, client, make_auth_headers, monkeypatch):
        _, headers = make_auth_headers()
        created_posts = [
            _create_post(client, headers, title=f"Post {index}", content="C")
            for index in range(1, 11)
        ]

        monkeypatch.setattr(
            forum_service,
            "rank_posts_for_user",
            lambda *, posts, user_id: list(reversed(posts)),
        )

        resp = client.get("/api/forum/posts?page=2&per_page=3", headers=headers)

        assert resp.status_code == 200
        ids = [item["id"] for item in resp.get_json()["data"]["items"]]
        assert ids == [created_posts[3]["id"], created_posts[4]["id"], created_posts[5]["id"]]

    def test_authenticated_list_preserves_total_when_personalized_ranking_uses_bounded_candidate_window(
        self,
        client,
        make_auth_headers,
        monkeypatch,
    ):
        _, headers = make_auth_headers()
        for index in range(1, 8):
            _create_post(client, headers, title=f"Post {index}", content="C")

        bounded_candidates = forum_service.forum_repository.list_published_posts_for_ranking(candidate_limit=5)

        monkeypatch.setattr(
            forum_service.forum_repository,
            "list_published_posts_for_ranking",
            lambda *, candidate_limit: bounded_candidates,
        )
        monkeypatch.setattr(
            forum_service.forum_repository,
            "count_all_published_posts",
            lambda: 7,
        )
        monkeypatch.setattr(
            forum_service,
            "rank_posts_for_user",
            lambda *, posts, user_id: posts,
        )

        resp = client.get("/api/forum/posts?page=1&per_page=5", headers=headers)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total"] == 7
        assert len(data["items"]) == 5

    def test_legacy_username_token_still_lists_posts(self, client, app, make_auth_headers):
        user_id, headers = make_auth_headers(username="test1")
        created = _create_post(client, headers, title="Legacy token post", content="C")

        with app.app_context():
            legacy_token = create_access_token(identity="test1")

        resp = client.get(
            "/api/forum/posts",
            headers={"Authorization": f"Bearer {legacy_token}"},
        )

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["id"] == created["id"]
        assert data["items"][0]["author_id"] == user_id

# ---------------------------------------------------------------------------
# GET /api/forum/posts/<id>
# ---------------------------------------------------------------------------

class TestGetPost:
    def test_get_existing_post(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        post = _create_post(client, headers)
        resp = client.get(f"/api/forum/posts/{post['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["id"] == post["id"]

    def test_get_nonexistent_post_returns_404(self, client):
        resp = client.get("/api/forum/posts/99999")
        assert resp.status_code == 404


class TestRecordPostLongView:
    def test_authenticated_user_can_record_long_view(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        post = _create_post(client, headers)

        resp = _post_json(client, f"/api/forum/posts/{post['id']}/long-view", {}, headers)

        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["tracked"] is True

    def test_long_view_requires_auth(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        post = _create_post(client, headers)

        resp = _post_json(client, f"/api/forum/posts/{post['id']}/long-view", {})

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /api/forum/posts/<id>
# ---------------------------------------------------------------------------

class TestUpdatePost:
    def test_author_can_update(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        post = _create_post(client, headers, title="Old")
        resp = _put_json(client, f"/api/forum/posts/{post['id']}", {"title": "New"}, headers)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["title"] == "New"

    def test_non_author_gets_403(self, client, make_auth_headers):
        _, author_headers = make_auth_headers()
        _, other_headers = make_auth_headers()
        post = _create_post(client, author_headers)
        resp = _put_json(client, f"/api/forum/posts/{post['id']}", {"title": "X"}, other_headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /api/forum/posts/<id>
# ---------------------------------------------------------------------------

class TestDeletePost:
    def test_author_can_delete(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        post = _create_post(client, headers)
        resp = client.delete(f"/api/forum/posts/{post['id']}", headers=headers)
        assert resp.status_code == 200
        # Subsequent GET should return 404.
        assert client.get(f"/api/forum/posts/{post['id']}").status_code == 404

    def test_non_author_gets_403(self, client, make_auth_headers):
        _, author_headers = make_auth_headers()
        _, other_headers = make_auth_headers()
        post = _create_post(client, author_headers)
        resp = client.delete(f"/api/forum/posts/{post['id']}", headers=other_headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/forum/posts/<id>/comments
# ---------------------------------------------------------------------------

class TestCreateComment:
    def test_create_top_level_comment(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        post = _create_post(client, headers)
        resp = _post_json(
            client,
            f"/api/forum/posts/{post['id']}/comments",
            {"content": "Great post!"},
            headers,
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["post_id"] == post["id"]
        assert data["parent_comment_id"] is None

    def test_create_comment_includes_author_profile_fields(self, client, make_auth_headers):
        user_id, headers = make_auth_headers(username="comment_writer")
        user = db.session.get(User, user_id)
        user.avatar_url = "/api/uploads/avatars/comment-writer.svg"
        db.session.commit()
        post = _create_post(client, headers)

        resp = _post_json(
            client,
            f"/api/forum/posts/{post['id']}/comments",
            {"content": "Great post!"},
            headers,
        )

        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["author_username"] == "comment_writer"
        assert data["author_avatar_url"] == "/api/uploads/avatars/comment-writer.svg"

    def test_create_reply(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        post = _create_post(client, headers)
        comment = _create_comment(client, headers, post["id"])
        reply = _create_comment(
            client, headers, post["id"], content="Reply!", parent_comment_id=comment["id"]
        )
        assert reply["parent_comment_id"] == comment["id"]

    def test_missing_content_returns_400(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        post = _create_post(client, headers)
        resp = _post_json(client, f"/api/forum/posts/{post['id']}/comments", {}, headers)
        assert resp.status_code == 400

    def test_comment_on_nonexistent_post_returns_404(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        resp = _post_json(
            client, "/api/forum/posts/99999/comments", {"content": "X"}, headers
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/forum/posts/<id>/comments
# ---------------------------------------------------------------------------

class TestListComments:
    def test_returns_all_comments(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        post = _create_post(client, headers)
        _create_comment(client, headers, post["id"], "C1")
        _create_comment(client, headers, post["id"], "C2")
        resp = client.get(f"/api/forum/posts/{post['id']}/comments")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["total"] == 2

    def test_deleted_comments_excluded(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        post = _create_post(client, headers)
        c1 = _create_comment(client, headers, post["id"], "Keep")
        c2 = _create_comment(client, headers, post["id"], "Delete me")
        client.delete(f"/api/forum/comments/{c2['id']}", headers=headers)
        resp = client.get(f"/api/forum/posts/{post['id']}/comments")
        ids = [c["id"] for c in resp.get_json()["data"]["items"]]
        assert c1["id"] in ids
        assert c2["id"] not in ids

    def test_list_comments_includes_author_profile_fields(self, client, make_auth_headers):
        user_id, headers = make_auth_headers(username="comment_reader")
        user = db.session.get(User, user_id)
        user.avatar_url = "/api/uploads/avatars/comment-reader.svg"
        db.session.commit()
        post = _create_post(client, headers)
        _create_comment(client, headers, post["id"], "Profile please")

        resp = client.get(f"/api/forum/posts/{post['id']}/comments")

        assert resp.status_code == 200
        item = resp.get_json()["data"]["items"][0]
        assert item["author_username"] == "comment_reader"
        assert item["author_avatar_url"] == "/api/uploads/avatars/comment-reader.svg"


# ---------------------------------------------------------------------------
# DELETE /api/forum/comments/<id>
# ---------------------------------------------------------------------------

class TestDeleteComment:
    def test_author_can_delete_comment(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        post = _create_post(client, headers)
        comment = _create_comment(client, headers, post["id"])
        resp = client.delete(f"/api/forum/comments/{comment['id']}", headers=headers)
        assert resp.status_code == 200

    def test_non_author_gets_403(self, client, make_auth_headers):
        _, author_headers = make_auth_headers()
        _, other_headers = make_auth_headers()
        post = _create_post(client, author_headers)
        comment = _create_comment(client, author_headers, post["id"])
        resp = client.delete(f"/api/forum/comments/{comment['id']}", headers=other_headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/forum/likes
# ---------------------------------------------------------------------------

class TestToggleLike:
    def test_like_post(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        post = _create_post(client, headers)
        resp = _post_json(
            client,
            "/api/forum/likes",
            {"target_type": "post", "target_id": post["id"]},
            headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["liked"] is True
        assert data["like_count"] == 1

    def test_unlike_post(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        post = _create_post(client, headers)
        _post_json(client, "/api/forum/likes", {"target_type": "post", "target_id": post["id"]}, headers)
        resp = _post_json(
            client,
            "/api/forum/likes",
            {"target_type": "post", "target_id": post["id"]},
            headers,
        )
        assert resp.get_json()["data"]["liked"] is False
        assert resp.get_json()["data"]["like_count"] == 0

    def test_like_comment(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        post = _create_post(client, headers)
        comment = _create_comment(client, headers, post["id"])
        resp = _post_json(
            client,
            "/api/forum/likes",
            {"target_type": "comment", "target_id": comment["id"]},
            headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["liked"] is True

    def test_invalid_target_type_returns_400(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        resp = _post_json(
            client, "/api/forum/likes", {"target_type": "invalid", "target_id": 1}, headers
        )
        assert resp.status_code == 400

    def test_missing_fields_returns_400(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        resp = _post_json(client, "/api/forum/likes", {}, headers)
        assert resp.status_code == 400

    def test_unauthenticated_returns_401(self, client):
        resp = _post_json(
            client, "/api/forum/likes", {"target_type": "post", "target_id": 1}
        )
        assert resp.status_code == 401


class TestForumNotifications:
    def test_post_like_notifies_post_author(self, client, make_auth_headers):
        _, author_headers = make_auth_headers(username="author")
        _, liker_headers = make_auth_headers(username="liker")
        post = _create_post(client, author_headers, title="Seed", content="Body")

        resp = _post_json(
            client,
            "/api/forum/likes",
            {"target_type": "post", "target_id": post["id"]},
            liker_headers,
        )
        assert resp.status_code == 200

        author_notifications = _get_notifications(client, author_headers)
        liker_notifications = _get_notifications(client, liker_headers)

        assert len(author_notifications) == 1
        assert author_notifications[0]["event_type"] == "post_liked"
        assert author_notifications[0]["title"] == "liker liked your post."
        assert liker_notifications == []

    def test_top_level_comment_notifies_post_author(self, client, make_auth_headers):
        _, author_headers = make_auth_headers(username="author")
        _, commenter_headers = make_auth_headers(username="commenter")
        post = _create_post(client, author_headers, title="Seed", content="Body")

        resp = _post_json(
            client,
            f"/api/forum/posts/{post['id']}/comments",
            {"content": "Great post!"},
            commenter_headers,
        )
        assert resp.status_code == 201

        author_notifications = _get_notifications(client, author_headers)
        commenter_notifications = _get_notifications(client, commenter_headers)

        assert len(author_notifications) == 1
        assert author_notifications[0]["event_type"] == "post_commented"
        assert author_notifications[0]["title"] == "commenter commented on your post."
        assert commenter_notifications == []

    def test_reply_notifies_parent_comment_author(self, client, make_auth_headers):
        _, author_headers = make_auth_headers(username="author")
        _, commenter_headers = make_auth_headers(username="commenter")
        _, replier_headers = make_auth_headers(username="replier")
        post = _create_post(client, author_headers, title="Seed", content="Body")
        comment = _create_comment(client, commenter_headers, post["id"], content="First!")

        resp = _create_comment(
            client,
            replier_headers,
            post["id"],
            content="Reply!",
            parent_comment_id=comment["id"],
        )
        assert resp["parent_comment_id"] == comment["id"]

        commenter_notifications = _get_notifications(client, commenter_headers)
        replier_notifications = _get_notifications(client, replier_headers)

        assert len(commenter_notifications) == 1
        assert commenter_notifications[0]["event_type"] == "comment_replied"
        assert commenter_notifications[0]["title"] == "replier replied to your comment."
        assert replier_notifications == []

    def test_comment_like_notifies_comment_author(self, client, make_auth_headers):
        _, author_headers = make_auth_headers(username="author")
        _, commenter_headers = make_auth_headers(username="commenter")
        _, liker_headers = make_auth_headers(username="liker")
        post = _create_post(client, author_headers, title="Seed", content="Body")
        comment = _create_comment(client, commenter_headers, post["id"], content="First!")

        resp = _post_json(
            client,
            "/api/forum/likes",
            {"target_type": "comment", "target_id": comment["id"]},
            liker_headers,
        )
        assert resp.status_code == 200

        commenter_notifications = _get_notifications(client, commenter_headers)
        liker_notifications = _get_notifications(client, liker_headers)

        assert len(commenter_notifications) == 1
        assert commenter_notifications[0]["event_type"] == "comment_liked"
        assert commenter_notifications[0]["title"] == "liker liked your comment."
        assert liker_notifications == []

    def test_self_notifications_are_suppressed(self, client, make_auth_headers):
        _, headers = make_auth_headers(username="author")
        post = _create_post(client, headers, title="Seed", content="Body")

        resp = _post_json(
            client,
            "/api/forum/likes",
            {"target_type": "post", "target_id": post["id"]},
            headers,
        )
        assert resp.status_code == 200

        comment = _create_comment(client, headers, post["id"], content="Self comment")
        reply = _create_comment(
            client,
            headers,
            post["id"],
            content="Self reply",
            parent_comment_id=comment["id"],
        )
        assert reply["parent_comment_id"] == comment["id"]

        resp = _post_json(
            client,
            "/api/forum/likes",
            {"target_type": "comment", "target_id": comment["id"]},
            headers,
        )
        assert resp.status_code == 200

        notifications = _get_notifications(client, headers)
        assert notifications == []
