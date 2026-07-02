import re

from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash, generate_password_hash

from app.models.user import User
from app.repositories.profile import user_repository
from app.services.ai.image_storage_service import ImageStorageError, store_data_url_image


class AuthError(Exception):
    """Raised for known auth failures; carries API error code and HTTP status."""

    def __init__(self, message: str, code: int = 40001, http_status: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


def _validate_password_strength(password: str) -> str | None:
    """Return an error message if the password does not meet strength requirements, or None if valid."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[^a-zA-Z0-9]", password):
        return "Password must contain at least one special character (e.g. @#$!)."
    return None


def register(username: str, email: str, password: str) -> tuple[User, str]:
    """Create a new user and return (user, access_token).
    Raises AuthError on duplicate or invalid input.
    """
    strength_error = _validate_password_strength(password)
    if strength_error:
        raise AuthError(strength_error)
    if user_repository.get_by_email(email):
        raise AuthError("Email already registered.", code=40900, http_status=409)
    if user_repository.get_by_username(username):
        raise AuthError("Username already taken.", code=40900, http_status=409)

    user = user_repository.create(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
    )
    token = create_access_token(identity=str(user.id))
    return user, token


def login(email: str, password: str) -> tuple[User, str]:
    """Verify credentials and return (user, access_token).
    Raises AuthError on wrong credentials.
    """
    user = user_repository.get_by_email(email)
    if not user or not check_password_hash(user.password_hash, password):
        raise AuthError("Invalid email or password.", code=40100, http_status=401)

    token = create_access_token(identity=str(user.id))
    return user, token


def update_avatar(user_id: int, image_data: str) -> User:
    """Decode a base64 data URL, persist it to disk, and update the user's avatar_url.
    Raises AuthError if the image is invalid or the user is not found.
    """
    try:
        avatar_url = store_data_url_image(image_data, namespace="avatars")
    except ImageStorageError as exc:
        raise AuthError(str(exc), code=40001, http_status=400) from exc

    user = user_repository.update_avatar_url(user_id, avatar_url)
    if not user:
        raise AuthError("User not found.", code=40400, http_status=404)

    return user


def update_profile(user_id: int, *, bio: str | None = None) -> User:
    normalized_bio = None if bio is None else str(bio).strip()
    if normalized_bio is not None and len(normalized_bio) > 500:
        raise AuthError("Bio must be 500 characters or fewer.")

    user = user_repository.update_profile(user_id, bio=normalized_bio)
    if not user:
        raise AuthError("User not found.", code=40400, http_status=404)

    return user
