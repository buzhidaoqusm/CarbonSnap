"""Register, login and the current user: the behaviour the frontend relies on.

Written against the Flask routes before they moved to FastAPI, and kept
unchanged across the move: status codes, envelope codes and the messages
users see.
"""

from __future__ import annotations

import base64
import re

import pytest

STRONG_PASSWORD = "Str0ng@pass"
# 1x1 transparent PNG.
PNG_DATA_URL = (
    "data:image/png;base64,"
    + base64.b64encode(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082"
        )
    ).decode()
)


def _register(client, **overrides):
    body = {"username": "alice", "email": "alice@example.com", "password": STRONG_PASSWORD}
    body.update(overrides)
    return client.post("/api/auth/register", json=body)


def _assert_error(response, status: int, code: int, message: str) -> None:
    assert response.status_code == status
    assert response.json() == {"code": code, "message": message, "data": {}}


USER_FIELDS = {
    "id",
    "username",
    "email",
    "avatar_url",
    "bio",
    "total_carbon_amount",
    "current_points",
    "created_at",
}


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------


class TestRegister:
    def test_creates_user_and_returns_token(self, client):
        response = _register(client)

        assert response.status_code == 201
        body = response.json()
        assert body["code"] == 0
        user = body["data"]["user"]
        assert set(user) == USER_FIELDS
        assert user["username"] == "alice"
        assert user["email"] == "alice@example.com"
        assert user["avatar_url"] is None
        assert user["bio"] is None
        assert user["total_carbon_amount"] == 0
        assert user["current_points"] == 0
        # Naive ISO 8601, as datetime.isoformat() writes it.
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?", user["created_at"])
        assert body["data"]["access_token"]

    def test_token_works_on_me(self, client):
        token = _register(client).json()["data"]["access_token"]

        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json()["data"]["user"]["username"] == "alice"

    def test_fields_are_trimmed(self, client):
        response = _register(client, username="  alice  ", email=" alice@example.com ")

        assert response.status_code == 201
        assert response.json()["data"]["user"]["username"] == "alice"
        assert response.json()["data"]["user"]["email"] == "alice@example.com"

    @pytest.mark.parametrize("missing", ["username", "email", "password"])
    def test_missing_field(self, client, missing):
        response = _register(client, **{missing: "   "})

        _assert_error(
            response, 400, 40001, "Fields 'username', 'email', and 'password' are required."
        )

    def test_empty_body(self, client):
        response = client.post("/api/auth/register", json={})

        _assert_error(
            response, 400, 40001, "Fields 'username', 'email', and 'password' are required."
        )

    @pytest.mark.parametrize(
        ("password", "message"),
        [
            ("Sh0rt@", "Password must be at least 8 characters."),
            ("lower@case1", "Password must contain at least one uppercase letter."),
            ("NoSpecial1", "Password must contain at least one special character (e.g. @#$!)."),
        ],
    )
    def test_weak_password(self, client, password, message):
        _assert_error(_register(client, password=password), 400, 40001, message)

    def test_duplicate_email(self, client):
        _register(client)

        response = _register(client, username="alice2")

        _assert_error(response, 409, 40900, "Email already registered.")

    def test_duplicate_username(self, client):
        _register(client)

        response = _register(client, email="alice2@example.com")

        _assert_error(response, 409, 40900, "Username already taken.")


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


class TestLogin:
    def test_returns_user_and_token(self, client):
        _register(client)

        response = client.post(
            "/api/auth/login", json={"email": "alice@example.com", "password": STRONG_PASSWORD}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert set(data["user"]) == USER_FIELDS
        assert data["user"]["username"] == "alice"
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
        assert me.status_code == 200

    def test_wrong_password(self, client):
        _register(client)

        response = client.post(
            "/api/auth/login", json={"email": "alice@example.com", "password": "Wr0ng@pass"}
        )

        _assert_error(response, 401, 40100, "Invalid email or password.")

    def test_unknown_email(self, client):
        response = client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": STRONG_PASSWORD}
        )

        _assert_error(response, 401, 40100, "Invalid email or password.")

    def test_missing_field(self, client):
        response = client.post("/api/auth/login", json={"email": "alice@example.com"})

        _assert_error(response, 400, 40001, "Fields 'email' and 'password' are required.")


# ---------------------------------------------------------------------------
# GET / PATCH /api/auth/me, PATCH /api/auth/me/avatar
# ---------------------------------------------------------------------------


class TestMe:
    def test_requires_token(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_legacy_token_with_username_subject(self, app, client, make_user):
        # Early tokens carried the username as the subject.
        from flask_jwt_extended import create_access_token

        user_id, _ = make_user(username="legacy", email="legacy@example.com")
        with app.app_context():
            token = create_access_token(identity="legacy")

        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json()["data"]["user"]["id"] == user_id

    def test_patch_without_bio_keeps_it(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        client.patch("/api/auth/me", json={"bio": "Hello"}, headers=headers)

        response = client.patch("/api/auth/me", json={}, headers=headers)

        assert response.status_code == 200
        assert response.json()["data"]["user"]["bio"] == "Hello"

    def test_patch_with_null_bio_keeps_it(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        client.patch("/api/auth/me", json={"bio": "Hello"}, headers=headers)

        response = client.patch("/api/auth/me", json={"bio": None}, headers=headers)

        assert response.status_code == 200
        assert response.json()["data"]["user"]["bio"] == "Hello"

    def test_patch_with_empty_bio_clears_it(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        client.patch("/api/auth/me", json={"bio": "Hello"}, headers=headers)

        response = client.patch("/api/auth/me", json={"bio": "   "}, headers=headers)

        assert response.status_code == 200
        assert response.json()["data"]["user"]["bio"] == ""

    def test_avatar_upload(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.patch(
            "/api/auth/me/avatar", json={"image": PNG_DATA_URL}, headers=headers
        )

        assert response.status_code == 200
        avatar_url = response.json()["data"]["avatar_url"]
        assert re.fullmatch(r"/api/uploads/avatars/[0-9a-f]{32}\.png", avatar_url)
        me = client.get("/api/auth/me", headers=headers).json()["data"]["user"]
        assert me["avatar_url"] == avatar_url

    def test_avatar_required(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.patch("/api/auth/me/avatar", json={}, headers=headers)

        _assert_error(response, 400, 40001, "Field 'image' (base64 data URL) is required.")

    def test_avatar_must_be_a_data_url(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.patch(
            "/api/auth/me/avatar", json={"image": "not-an-image"}, headers=headers
        )

        _assert_error(response, 400, 40001, "Field 'image' must be a base64 image data URL.")
