"""Tokens and auth errors.

Tokens keep the claims flask_jwt_extended wrote, so a user who logged in
before the move off Flask stays logged in.
"""

from __future__ import annotations

import datetime as dt

import jwt as pyjwt
import pytest

from app.core.config import get_settings


def test_a_token_with_the_old_claims_is_accepted(client, make_auth_headers):
    # make_auth_headers signs with the claims flask_jwt_extended wrote.
    _, headers = make_auth_headers()

    response = client.get("/api/notifications/unread-count", headers=headers)

    assert response.status_code == 200


def test_a_token_names_its_user(client, make_user):
    from app.core.security import create_access_token

    user_id, _ = make_user()
    headers = {"Authorization": f"Bearer {create_access_token(user_id)}"}

    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["user"]["id"] == user_id


def test_legacy_token_with_username_subject_still_works(client, make_user):
    # Early tokens carried the username as the subject. forum and market
    # resolve it; the notification routes used int(sub) and failed with a 500.
    from app.core.security import create_access_token

    make_user(username="legacy", email="legacy@example.com")
    token = create_access_token("legacy")

    response = client.get(
        "/api/notifications/unread-count", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


def _expired_token() -> str:
    now = dt.datetime.now(dt.UTC)
    claims = {"sub": "1", "type": "access", "iat": now - dt.timedelta(days=8)}
    claims["exp"] = now - dt.timedelta(days=1)
    return pyjwt.encode(claims, get_settings().jwt_secret_key, algorithm="HS256")


@pytest.mark.parametrize(
    "authorization",
    [None, "Bearer not-a-jwt", "Token abc", "expired"],
    ids=["missing", "malformed", "wrong-scheme", "expired"],
)
def test_auth_failures_use_the_envelope(client, authorization):
    headers = {}
    if authorization == "expired":
        headers["Authorization"] = f"Bearer {_expired_token()}"
    elif authorization is not None:
        headers["Authorization"] = authorization

    response = client.get("/api/notifications", headers=headers)

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == 40100
    assert body["message"]
    assert body["data"] == {}


def test_refresh_type_token_is_rejected(client, make_user):
    user_id, _ = make_user()
    now = dt.datetime.now(dt.UTC)
    token = pyjwt.encode(
        {"sub": str(user_id), "type": "refresh", "iat": now, "exp": now + dt.timedelta(hours=1)},
        get_settings().jwt_secret_key,
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
