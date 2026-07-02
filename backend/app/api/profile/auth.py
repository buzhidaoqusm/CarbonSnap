from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.repositories.profile import user_repository
from app.services.profile import auth_service
from app.services.profile.auth_service import AuthError
from app.utils.response import fail, ok

auth_bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_user(user) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "total_carbon_amount": user.total_carbon_amount,
        "current_points": user.current_points,
        "created_at": user.created_at.isoformat(),
    }


def _validate_register_body(body: dict) -> tuple[dict | None, tuple | None]:
    username = str(body.get("username", "")).strip()
    email = str(body.get("email", "")).strip()
    password = str(body.get("password", "")).strip()
    if not username or not email or not password:
        return None, fail(40001, "Fields 'username', 'email', and 'password' are required.")
    return {"username": username, "email": email, "password": password}, None


def _validate_login_body(body: dict) -> tuple[dict | None, tuple | None]:
    email = str(body.get("email", "")).strip()
    password = str(body.get("password", "")).strip()
    if not email or not password:
        return None, fail(40001, "Fields 'email' and 'password' are required.")
    return {"email": email, "password": password}, None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@auth_bp.post("/auth/register")
def register():
    fields, err = _validate_register_body(request.get_json(silent=True) or {})
    if err:
        return err

    try:
        user, token = auth_service.register(**fields)
    except AuthError as exc:
        return fail(exc.code, exc.message, exc.http_status)

    return ok({"user": _serialize_user(user), "access_token": token}, status=201)


@auth_bp.post("/auth/login")
def login():
    fields, err = _validate_login_body(request.get_json(silent=True) or {})
    if err:
        return err

    try:
        user, token = auth_service.login(**fields)
    except AuthError as exc:
        return fail(exc.code, exc.message, exc.http_status)

    return ok({"user": _serialize_user(user), "access_token": token})


@auth_bp.get("/auth/me")
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = user_repository.get_by_id(user_id)
    if not user:
        return fail(40400, "User not found.", 404)
    return ok({"user": _serialize_user(user)})


@auth_bp.patch("/auth/me")
@jwt_required()
def update_profile():
    body = request.get_json(silent=True) or {}
    try:
        user = auth_service.update_profile(
            int(get_jwt_identity()),
            bio=body.get("bio") if "bio" in body else None,
        )
    except AuthError as exc:
        return fail(exc.code, exc.message, exc.http_status)

    return ok({"user": _serialize_user(user)})


@auth_bp.patch("/auth/me/avatar")
@jwt_required()
def update_avatar():
    body = request.get_json(silent=True) or {}
    image_data = str(body.get("image", "")).strip()
    if not image_data:
        return fail(40001, "Field 'image' (base64 data URL) is required.")

    try:
        user = auth_service.update_avatar(int(get_jwt_identity()), image_data)
    except AuthError as exc:
        return fail(exc.code, exc.message, exc.http_status)

    return ok({"avatar_url": user.avatar_url})
