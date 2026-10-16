"""Dependencies the FastAPI routes declare with Depends()."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.api.errors import Unauthorized
from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_db
from app.utils.auth_identity import UnresolvableJwtIdentityError, resolve_identity_to_user_id

DbSession = Annotated[Session, Depends(get_db)]


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise Unauthorized("Missing Authorization header.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise Unauthorized("Authorization header must be 'Bearer <token>'.")
    return token.strip()


def get_current_user_id(
    session: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> int:
    try:
        claims = decode_access_token(_bearer_token(authorization))
        # Early tokens carry a username or email as the subject.
        return resolve_identity_to_user_id(session, claims["sub"])
    except (InvalidTokenError, UnresolvableJwtIdentityError) as exc:
        raise Unauthorized(str(exc)) from exc


CurrentUserId = Annotated[int, Depends(get_current_user_id)]


def get_optional_user_id(
    session: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> int | None:
    """For routes anyone may call. No token means anonymous; a token that is
    sent must be valid (401 otherwise), as on routes that require login."""
    if not authorization:
        return None
    return get_current_user_id(session, authorization)


OptionalUserId = Annotated[int | None, Depends(get_optional_user_id)]


class Pagination:
    """?page=&per_page= for list endpoints; out-of-range values are clamped,
    as the Flask routes did, and a non-integer is a 400."""

    def __init__(self, page: int, per_page: int):
        self.page = max(1, page)
        self.per_page = min(100, max(1, per_page))


def pagination(default_per_page: int = 20) -> Any:
    """Depends() for ?page=&per_page= with a per-module default page size."""

    # A closure: FastAPI reads this signature, so /docs shows the default.
    def dependency(page: int = 1, per_page: int = default_per_page) -> Pagination:
        return Pagination(page, per_page)

    return Depends(dependency)


PageParams = Annotated[Pagination, pagination()]
