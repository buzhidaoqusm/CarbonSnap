"""Access tokens without Flask.

Tokens are interchangeable with the ones flask_jwt_extended issues, so both
stacks accept each other's while routes move: HS256 with JWT_SECRET_KEY, the
user id as a string subject, type "access", and a 7-day expiry.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_LIFETIME = dt.timedelta(days=7)


class InvalidTokenError(Exception):
    """The request carries no usable access token."""


def create_access_token(user_id: int) -> str:
    now = dt.datetime.now(dt.UTC)
    claims = {
        # The same claims flask_jwt_extended writes.
        "fresh": False,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "access",
        "sub": str(user_id),
        "nbf": now,
        "exp": now + ACCESS_TOKEN_LIFETIME,
    }
    return jwt.encode(claims, get_settings().jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Return the claims of a valid access token, or raise InvalidTokenError."""
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            get_settings().jwt_secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("Token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Token is invalid.") from exc
    # flask_jwt_extended treats a token without "type" as an access token.
    if claims.get("type", "access") != "access":
        raise InvalidTokenError("Only access tokens are accepted.")
    return claims
