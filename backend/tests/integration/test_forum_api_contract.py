"""Error messages, response shapes and tokens of the forum API.

Pinned against the Flask routes before they moved to FastAPI and kept
unchanged across the move.
"""

from __future__ import annotations

import base64
import datetime as dt
import re

import jwt as pyjwt
import pytest

PNG_DATA_URL = (
    "data:image/png;base64,"
    + base64.b64encode(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082"
        )
    ).decode()
)
NAIVE_ISO = r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?"
POST_FIELDS = {
    "id",
    "author_id",
    "author_username",
    "author_avatar_url",
    "title",
    "content",
    "image_urls_json",
    "status",
    "like_count",
    "comment_count",
    "liked_by_user",
    "created_at",
}
COMMENT_FIELDS = {
    "id",
    "post_id",
    "user_id",
    "author_username",
    "author_avatar_url",
    "parent_comment_id",
    "content",
    "status",
    "like_count",
    "liked_by_user",
    "created_at",
}


def _post(client, headers, **overrides) -> dict:
    body = {"title": "Bottle caps", "content": "Keep the caps on."}
    body.update(overrides)
    response = client.post("/api/forum/posts", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _comment(client, headers, post_id, **overrides) -> dict:
    body = {"content": "Agreed."}
    body.update(overrides)
    response = client.post(f"/api/forum/posts/{post_id}/comments", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _like(client, headers, target_type, target_id):
    return client.post(
        "/api/forum/likes",
        json={"target_type": target_type, "target_id": target_id},
        headers=headers,
    )


def _assert_error(response, status: int, code: int, message: str) -> None:
    assert response.status_code == status, response.text
    assert response.json() == {"code": code, "message": message, "data": {}}


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------


class TestPosts:
    def test_created_post_shape(self, client, make_auth_headers):
        author_id, author = make_auth_headers(username="writer")

        post = _post(client, author, image_urls_json='["/api/uploads/forum/a.png"]')

        assert set(post) == POST_FIELDS
        assert (post["author_id"], post["author_username"], post["author_avatar_url"]) == (
            author_id,
            "writer",
            None,
        )
        assert post["image_urls_json"] == '["/api/uploads/forum/a.png"]'
        assert (post["status"], post["like_count"], post["comment_count"]) == ("published", 0, 0)
        assert post["liked_by_user"] is False
        assert re.fullmatch(NAIVE_ISO, post["created_at"])

    @pytest.mark.parametrize(
        "body", [{"title": " ", "content": "x"}, {"title": "x", "content": ""}, {}]
    )
    def test_title_and_content_are_required(self, client, make_auth_headers, body):
        _, author = make_auth_headers()

        response = client.post("/api/forum/posts", json=body, headers=author)

        _assert_error(response, 400, 40001, "Fields 'title' and 'content' are required.")

    def test_detail_counts_and_liked_flag(self, client, make_auth_headers):
        _, author = make_auth_headers()
        _, reader = make_auth_headers()
        post_id = _post(client, author)["id"]
        _comment(client, reader, post_id)
        _like(client, reader, "post", post_id)

        anonymous = client.get(f"/api/forum/posts/{post_id}").json()["data"]
        as_reader = client.get(f"/api/forum/posts/{post_id}", headers=reader).json()["data"]

        assert set(anonymous) == POST_FIELDS
        assert (anonymous["like_count"], anonymous["comment_count"]) == (1, 1)
        assert anonymous["liked_by_user"] is None
        assert as_reader["liked_by_user"] is True

    def test_list_shape_and_paging(self, client, make_auth_headers):
        _, author = make_auth_headers()
        _post(client, author)

        default = client.get("/api/forum/posts").json()["data"]
        clamped = client.get("/api/forum/posts?page=0&per_page=500").json()["data"]

        assert set(default) == {"items", "total", "page", "per_page"}
        assert (default["page"], default["per_page"], default["total"]) == (1, 20, 1)
        assert (clamped["page"], clamped["per_page"]) == (1, 100)
        assert set(default["items"][0]) == POST_FIELDS

    def test_update_keeps_blank_fields(self, client, make_auth_headers):
        _, author = make_auth_headers()
        post_id = _post(client, author)["id"]

        response = client.put(
            f"/api/forum/posts/{post_id}",
            json={"title": "New title", "content": ""},
            headers=author,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert set(data) == POST_FIELDS
        assert (data["title"], data["content"]) == ("New title", "Keep the caps on.")
        # The update response carries no counts.
        assert (data["like_count"], data["comment_count"], data["liked_by_user"]) == (
            None,
            None,
            None,
        )

    def test_author_only_and_not_found(self, client, make_auth_headers):
        _, author = make_auth_headers()
        _, other = make_auth_headers()
        post_id = _post(client, author)["id"]

        for method in ("put", "delete"):
            _assert_error(
                getattr(client, method)(f"/api/forum/posts/{post_id}", headers=other),
                403,
                40300,
                "You are not the author of this post.",
            )
            _assert_error(
                getattr(client, method)("/api/forum/posts/999999", headers=author),
                404,
                40400,
                "Post not found.",
            )
        _assert_error(client.get("/api/forum/posts/999999"), 404, 40400, "Post not found.")

    def test_delete(self, client, make_auth_headers):
        _, author = make_auth_headers()
        post_id = _post(client, author)["id"]

        response = client.delete(f"/api/forum/posts/{post_id}", headers=author)

        assert response.json() == {"code": 0, "message": "ok", "data": {}}

    def test_long_view(self, client, make_auth_headers):
        _, author = make_auth_headers()
        _, reader = make_auth_headers()
        post_id = _post(client, author)["id"]
        path = f"/api/forum/posts/{post_id}/long-view"

        first = client.post(path, headers=reader)
        again = client.post(path, headers=reader)

        assert (first.status_code, first.json()["data"]) == (201, {"tracked": True})
        assert again.json()["data"] == {"tracked": False, "reason": "deduplicated"}
        _assert_error(
            client.post("/api/forum/posts/999999/long-view", headers=reader),
            404,
            40400,
            "Post not found.",
        )


# ---------------------------------------------------------------------------
# Uploads
# ---------------------------------------------------------------------------


class TestUploads:
    def test_stores_image(self, client, make_auth_headers):
        _, author = make_auth_headers()

        response = client.post("/api/forum/uploads", json={"image": PNG_DATA_URL}, headers=author)

        assert response.status_code == 201
        assert re.fullmatch(r"/api/uploads/forum/[0-9a-f]{32}\.png", response.json()["data"]["url"])

    @pytest.mark.parametrize(
        ("body", "message"),
        [
            ({}, "Field 'image' must be a base64 data URL string."),
            ({"image": 7}, "Field 'image' must be a base64 data URL string."),
            ({"image": "x"}, "Field 'image' must be a base64 image data URL."),
        ],
        ids=["missing", "not-a-string", "not-a-data-url"],
    )
    def test_validation(self, client, make_auth_headers, body, message):
        _, author = make_auth_headers()

        response = client.post("/api/forum/uploads", json=body, headers=author)

        _assert_error(response, 400, 40001, message)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


class TestComments:
    def test_comment_and_reply_shapes(self, client, make_auth_headers):
        _, author = make_auth_headers()
        reader_id, reader = make_auth_headers(username="reader")
        post_id = _post(client, author)["id"]

        comment = _comment(client, reader, post_id, content="  Agreed.  ")
        reply = _comment(client, author, post_id, parent_comment_id=str(comment["id"]))

        assert set(comment) == COMMENT_FIELDS
        assert (comment["post_id"], comment["user_id"], comment["author_username"]) == (
            post_id,
            reader_id,
            "reader",
        )
        assert (comment["content"], comment["parent_comment_id"]) == ("Agreed.", None)
        assert (comment["like_count"], comment["liked_by_user"], comment["status"]) == (
            0,
            False,
            "published",
        )
        assert reply["parent_comment_id"] == comment["id"]

    def test_list(self, client, make_auth_headers):
        _, author = make_auth_headers()
        _, reader = make_auth_headers()
        post_id = _post(client, author)["id"]
        comment_id = _comment(client, reader, post_id)["id"]
        _like(client, author, "comment", comment_id)

        anonymous = client.get(f"/api/forum/posts/{post_id}/comments").json()["data"]
        as_author = client.get(f"/api/forum/posts/{post_id}/comments", headers=author).json()[
            "data"
        ]

        assert set(anonymous) == {"items", "total"}
        assert anonymous["total"] == 1
        assert set(anonymous["items"][0]) == COMMENT_FIELDS
        assert (anonymous["items"][0]["like_count"], anonymous["items"][0]["liked_by_user"]) == (
            1,
            None,
        )
        assert as_author["items"][0]["liked_by_user"] is True

    def test_errors(self, client, make_auth_headers):
        _, author = make_auth_headers()
        _, other = make_auth_headers()
        post_id = _post(client, author)["id"]
        comment_id = _comment(client, author, post_id)["id"]
        path = f"/api/forum/posts/{post_id}/comments"

        _assert_error(
            client.post(path, json={"content": " "}, headers=author),
            400,
            40001,
            "Field 'content' is required.",
        )
        _assert_error(
            client.post(path, json={"content": "x", "parent_comment_id": "x"}, headers=author),
            400,
            40001,
            "'parent_comment_id' must be an integer.",
        )
        _assert_error(
            client.post(path, json={"content": "x", "parent_comment_id": 999999}, headers=author),
            404,
            40400,
            "Parent comment not found.",
        )
        _assert_error(
            client.post("/api/forum/posts/999999/comments", json={"content": "x"}, headers=author),
            404,
            40400,
            "Post not found.",
        )
        _assert_error(client.get("/api/forum/posts/999999/comments"), 404, 40400, "Post not found.")
        _assert_error(
            client.delete(f"/api/forum/comments/{comment_id}", headers=other),
            403,
            40300,
            "You are not the author of this comment.",
        )
        _assert_error(
            client.delete("/api/forum/comments/999999", headers=author),
            404,
            40400,
            "Comment not found.",
        )
        deleted = client.delete(f"/api/forum/comments/{comment_id}", headers=author)
        assert deleted.json() == {"code": 0, "message": "ok", "data": {}}


# ---------------------------------------------------------------------------
# Likes
# ---------------------------------------------------------------------------


class TestLikes:
    def test_toggle(self, client, make_auth_headers):
        _, author = make_auth_headers()
        _, reader = make_auth_headers()
        post_id = _post(client, author)["id"]

        liked = _like(client, reader, "post", post_id)
        unliked = _like(client, reader, "post", str(post_id))

        assert (liked.status_code, liked.json()["data"]) == (200, {"liked": True, "like_count": 1})
        assert unliked.json()["data"] == {"liked": False, "like_count": 0}

    @pytest.mark.parametrize(
        ("body", "status", "code", "message"),
        [
            ({}, 400, 40001, "Fields 'target_type' and 'target_id' are required."),
            (
                {"target_type": "post"},
                400,
                40001,
                "Fields 'target_type' and 'target_id' are required.",
            ),
            (
                {"target_type": "post", "target_id": "x"},
                400,
                40001,
                "'target_id' must be an integer.",
            ),
            (
                {"target_type": "user", "target_id": 1},
                400,
                40001,
                "target_type must be 'post' or 'comment'.",
            ),
            ({"target_type": "post", "target_id": 999999}, 404, 40400, "Post not found."),
            ({"target_type": "comment", "target_id": 999999}, 404, 40400, "Comment not found."),
        ],
        ids=["empty", "no-id", "id-not-int", "bad-type", "no-post", "no-comment"],
    )
    def test_errors(self, client, make_auth_headers, body, status, code, message):
        _, reader = make_auth_headers()

        response = client.post("/api/forum/likes", json=body, headers=reader)

        _assert_error(response, status, code, message)


# ---------------------------------------------------------------------------
# Tokens on routes where login is optional
# ---------------------------------------------------------------------------


OPTIONAL_LOGIN_PATHS = [
    "/api/forum/posts",
    "/api/forum/posts/{id}",
    "/api/forum/posts/{id}/comments",
]


class TestOptionalLogin:
    @pytest.mark.parametrize("path", OPTIONAL_LOGIN_PATHS)
    def test_bad_token_is_a_401(self, client, make_auth_headers, path):
        _, author = make_auth_headers()
        post_id = _post(client, author)["id"]

        response = client.get(path.format(id=post_id), headers={"Authorization": "Bearer garbage"})

        assert response.status_code == 401
        assert response.json()["code"] == 40100

    @pytest.mark.parametrize("path", OPTIONAL_LOGIN_PATHS)
    def test_token_for_an_unknown_user_is_a_401(self, app, client, make_auth_headers, path):
        # Was served as anonymous; now the same rule as every optional route.
        _, author = make_auth_headers()
        post_id = _post(client, author)["id"]
        token = pyjwt.encode(
            {
                "sub": "nobody",
                "type": "access",
                "exp": dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
            },
            app.config["JWT_SECRET_KEY"],
            algorithm="HS256",
        )

        response = client.get(path.format(id=post_id), headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
