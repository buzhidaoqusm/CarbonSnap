from __future__ import annotations

from flask_jwt_extended import get_jwt_identity

from app.repositories.profile import user_repository


class UnresolvableJwtIdentityError(ValueError):
    """Raised when a JWT subject cannot be mapped to a local user id."""


def resolve_identity_to_user_id(identity) -> int:
    """Map a JWT identity to the canonical numeric user id.

    Newer tokens store the numeric user id as the JWT subject. Older local
    tokens may still store a username or email. We support both so existing
    sessions do not crash optional-auth endpoints like forum and market lists.
    """

    if identity in (None, ""):
        raise UnresolvableJwtIdentityError("JWT identity is missing.")

    try:
        return int(identity)
    except (TypeError, ValueError):
        pass

    identity_str = str(identity).strip()
    if not identity_str:
        raise UnresolvableJwtIdentityError("JWT identity is empty.")

    user = user_repository.get_by_username(identity_str)
    if user is None and "@" in identity_str:
        user = user_repository.get_by_email(identity_str)
    if user is None:
        raise UnresolvableJwtIdentityError(f"JWT identity '{identity_str}' could not be resolved.")
    return int(user.id)


def get_optional_current_user_id() -> int | None:
    identity = get_jwt_identity()
    if identity in (None, ""):
        return None
    try:
        return resolve_identity_to_user_id(identity)
    except UnresolvableJwtIdentityError:
        return None


def get_required_current_user_id() -> int:
    user_id = get_optional_current_user_id()
    if user_id is None:
        raise UnresolvableJwtIdentityError("Authenticated user could not be resolved from the JWT.")
    return user_id
