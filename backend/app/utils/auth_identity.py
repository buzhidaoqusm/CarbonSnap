from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.profile import user_repository


class UnresolvableJwtIdentityError(ValueError):
    """Raised when a JWT subject cannot be mapped to a local user id."""


def resolve_identity_to_user_id(session: Session, identity) -> int:
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

    user = user_repository.get_by_username(session, identity_str)
    if user is None and "@" in identity_str:
        user = user_repository.get_by_email(session, identity_str)
    if user is None:
        raise UnresolvableJwtIdentityError(f"JWT identity '{identity_str}' could not be resolved.")
    return int(user.id)
