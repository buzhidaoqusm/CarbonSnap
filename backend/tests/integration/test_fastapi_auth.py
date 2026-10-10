"""Tokens and auth errors while routes move from Flask to FastAPI.

Both stacks verify the same tokens: a user logged in before a route moved
stays logged in after, whichever side issued the token.
"""

from __future__ import annotations

import datetime as dt

import jwt as pyjwt
import pytest


def test_token_from_flask_is_accepted_by_fastapi(client, make_auth_headers):
    # make_auth_headers signs with flask_jwt_extended.
    _, headers = make_auth_headers()

    response = client.get("/api/notifications/unread-count", headers=headers)

    assert response.status_code == 200


def test_token_from_fastapi_is_accepted_by_flask(client, make_user):
    from app.core.security import create_access_token

    user_id, _ = make_user()
    headers = {"Authorization": f"Bearer {create_access_token(user_id)}"}

    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["user"]["id"] == user_id


def test_legacy_token_with_username_subject_still_works(app, client, make_user):
    # Early tokens carried the username as the subject. forum and market
    # resolve it; the notification routes used int(sub) and failed with a 500.
    from flask_jwt_extended import create_access_token

    make_user(username="legacy", email="legacy@example.com")
    with app.app_context():
        token = create_access_token(identity="legacy")

    response = client.get(
        "/api/notifications/unread-count", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


def _expired_token(app) -> str:
    now = dt.datetime.now(dt.UTC)
    claims = {"sub": "1", "type": "access", "iat": now - dt.timedelta(days=8)}
    claims["exp"] = now - dt.timedelta(days=1)
    return pyjwt.encode(claims, app.config["JWT_SECRET_KEY"], algorithm="HS256")


@pytest.mark.parametrize(
    "authorization",
    [None, "Bearer not-a-jwt", "Token abc", "expired"],
    ids=["missing", "malformed", "wrong-scheme", "expired"],
)
def test_auth_failures_use_the_envelope(app, client, authorization):
    headers = {}
    if authorization == "expired":
        headers["Authorization"] = f"Bearer {_expired_token(app)}"
    elif authorization is not None:
        headers["Authorization"] = authorization

    response = client.get("/api/notifications", headers=headers)

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == 40100
    assert body["message"]
    assert body["data"] == {}


def test_refresh_type_token_is_rejected(app, client, make_user):
    user_id, _ = make_user()
    now = dt.datetime.now(dt.UTC)
    token = pyjwt.encode(
        {"sub": str(user_id), "type": "refresh", "iat": now, "exp": now + dt.timedelta(hours=1)},
        app.config["JWT_SECRET_KEY"],
        algorithm="HS256",
    )

    response = client.get("/api/notifications", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_invalid_query_parameter_is_a_400_envelope(client, make_auth_headers):
    # FastAPI's own validation error is a 422 with a "detail" list; the
    # frontend reads "message", so it is mapped onto the envelope.
    _, headers = make_auth_headers()

    response = client.patch("/api/notifications/abc/read", headers=headers)

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 40000
    assert "notification_id" in body["message"]
