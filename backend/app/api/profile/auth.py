"""Register, login and the current user's profile."""

from fastapi import APIRouter

from app.api.deps import CurrentUserId, DbSession
from app.api.errors import ApiError
from app.repositories.profile import user_repository
from app.schemas.auth import (
    AuthResult,
    AvatarIn,
    AvatarResult,
    LoginIn,
    ProfileIn,
    RegisterIn,
    UserOut,
    UserResult,
)
from app.schemas.common import Envelope, ok
from app.services.profile import auth_service
from app.services.profile.auth_service import AuthError

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _api_error(exc: AuthError) -> ApiError:
    return ApiError(exc.code, exc.message, exc.http_status)


@router.post("/register", status_code=201, response_model=Envelope[AuthResult])
def register(session: DbSession, body: RegisterIn | None = None):
    body = body or RegisterIn()
    username, email, password = body.username.strip(), body.email.strip(), body.password.strip()
    if not username or not email or not password:
        raise ApiError(40001, "Fields 'username', 'email', and 'password' are required.")
    try:
        user, token = auth_service.register(session, username, email, password)
    except AuthError as exc:
        raise _api_error(exc) from exc
    return ok(AuthResult(user=UserOut.model_validate(user), access_token=token))


@router.post("/login", response_model=Envelope[AuthResult])
def login(session: DbSession, body: LoginIn | None = None):
    body = body or LoginIn()
    email, password = body.email.strip(), body.password.strip()
    if not email or not password:
        raise ApiError(40001, "Fields 'email' and 'password' are required.")
    try:
        user, token = auth_service.login(session, email, password)
    except AuthError as exc:
        raise _api_error(exc) from exc
    return ok(AuthResult(user=UserOut.model_validate(user), access_token=token))


@router.get("/me", response_model=Envelope[UserResult])
def me(user_id: CurrentUserId, session: DbSession):
    user = user_repository.get_by_id(session, user_id)
    if user is None:
        raise ApiError(40400, "User not found.", 404)
    return ok(UserResult(user=UserOut.model_validate(user)))


@router.patch("/me", response_model=Envelope[UserResult])
def update_profile(user_id: CurrentUserId, session: DbSession, body: ProfileIn | None = None):
    bio = (body or ProfileIn()).bio
    try:
        user = auth_service.update_profile(session, user_id, bio=bio)
    except AuthError as exc:
        raise _api_error(exc) from exc
    return ok(UserResult(user=UserOut.model_validate(user)))


@router.patch("/me/avatar", response_model=Envelope[AvatarResult])
def update_avatar(user_id: CurrentUserId, session: DbSession, body: AvatarIn | None = None):
    image_data = (body or AvatarIn()).image.strip()
    if not image_data:
        raise ApiError(40001, "Field 'image' (base64 data URL) is required.")
    try:
        user = auth_service.update_avatar(session, user_id, image_data)
    except AuthError as exc:
        raise _api_error(exc) from exc
    return ok(AvatarResult(avatar_url=user.avatar_url))
