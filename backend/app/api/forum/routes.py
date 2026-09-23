"""Forum API Blueprint.

Endpoints:
  POST   /api/forum/posts                    Create a post
  GET    /api/forum/posts                    List posts (paginated)
  GET    /api/forum/posts/<id>               Get post detail
  PUT    /api/forum/posts/<id>               Edit post (author only)
  DELETE /api/forum/posts/<id>               Soft-delete post (author only)

  POST   /api/forum/posts/<id>/comments      Create comment / reply
  GET    /api/forum/posts/<id>/comments      List comments for a post
  DELETE /api/forum/comments/<id>            Soft-delete comment (author only)

  POST   /api/forum/likes                    Toggle like (post or comment)
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.services.ai.image_storage_service import ImageStorageError, store_data_url_image
from app.services.forum import forum_service
from app.services.forum.forum_service import ForumError
from app.utils.auth_identity import (
    UnresolvableJwtIdentityError,
    get_optional_current_user_id,
    get_required_current_user_id,
)
from app.utils.response import fail, ok

forum_bp = Blueprint("forum", __name__)


def _current_user_id() -> int:
    return get_required_current_user_id()


def _parse_pagination() -> tuple[int, int]:
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except (TypeError, ValueError):
        per_page = 20
    return page, per_page


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------


@forum_bp.post("/forum/uploads")
@jwt_required()
def upload_forum_image():
    body = request.get_json(silent=True) or {}
    image_data_url = body.get("image")

    if image_data_url is None or not isinstance(image_data_url, str):
        return fail(40001, "Field 'image' must be a base64 data URL string.")

    try:
        image_url = store_data_url_image(image_data_url, namespace="forum")
    except ImageStorageError as exc:
        return fail(40001, str(exc))

    return ok({"url": image_url}, status=201)


@forum_bp.post("/forum/posts")
@jwt_required()
def create_post():
    body = request.get_json(silent=True) or {}
    title = str(body.get("title", "")).strip()
    content = str(body.get("content", "")).strip()
    if not title or not content:
        return fail(40001, "Fields 'title' and 'content' are required.")

    try:
        result = forum_service.create_post(
            author_id=_current_user_id(),
            title=title,
            content=content,
            image_urls_json=body.get("image_urls_json") or None,
        )
    except ForumError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result, status=201)


@forum_bp.get("/forum/posts")
@jwt_required(optional=True)
def list_posts():
    page, per_page = _parse_pagination()
    viewer_id = get_optional_current_user_id()
    return ok(forum_service.list_posts(page, per_page, viewer_user_id=viewer_id))


@forum_bp.get("/forum/posts/<int:post_id>")
@jwt_required(optional=True)
def get_post(post_id: int):
    viewer_id = get_optional_current_user_id()
    try:
        result = forum_service.get_post(post_id, viewer_user_id=viewer_id)
    except ForumError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result)


@forum_bp.post("/forum/posts/<int:post_id>/long-view")
@jwt_required()
def record_post_long_view(post_id: int):
    try:
        result = forum_service.record_post_long_view(post_id, viewer_user_id=_current_user_id())
    except ForumError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result, status=201)


@forum_bp.put("/forum/posts/<int:post_id>")
@jwt_required()
def update_post(post_id: int):
    body = request.get_json(silent=True) or {}
    try:
        result = forum_service.update_post(
            post_id,
            operator_user_id=_current_user_id(),
            title=body.get("title") or None,
            content=body.get("content") or None,
            image_urls_json=body.get("image_urls_json") or None,
        )
    except ForumError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result)


@forum_bp.delete("/forum/posts/<int:post_id>")
@jwt_required()
def delete_post(post_id: int):
    try:
        forum_service.delete_post(post_id, operator_user_id=_current_user_id())
    except ForumError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok()


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


@forum_bp.post("/forum/posts/<int:post_id>/comments")
@jwt_required()
def create_comment(post_id: int):
    body = request.get_json(silent=True) or {}
    content = str(body.get("content", "")).strip()
    if not content:
        return fail(40001, "Field 'content' is required.")

    parent_comment_id = body.get("parent_comment_id")
    if parent_comment_id is not None:
        try:
            parent_comment_id = int(parent_comment_id)
        except (TypeError, ValueError):
            return fail(40001, "'parent_comment_id' must be an integer.")

    try:
        result = forum_service.create_comment(
            post_id=post_id,
            user_id=_current_user_id(),
            content=content,
            parent_comment_id=parent_comment_id,
        )
    except ForumError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result, status=201)


@forum_bp.get("/forum/posts/<int:post_id>/comments")
@jwt_required(optional=True)
def list_comments(post_id: int):
    viewer_id = get_optional_current_user_id()
    try:
        result = forum_service.list_comments(post_id, viewer_user_id=viewer_id)
    except ForumError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result)


@forum_bp.errorhandler(UnresolvableJwtIdentityError)
def handle_unresolvable_jwt_identity(exc: UnresolvableJwtIdentityError):
    return fail(40100, str(exc), 401)


@forum_bp.delete("/forum/comments/<int:comment_id>")
@jwt_required()
def delete_comment(comment_id: int):
    try:
        forum_service.delete_comment(comment_id, operator_user_id=_current_user_id())
    except ForumError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok()


# ---------------------------------------------------------------------------
# Likes
# ---------------------------------------------------------------------------


@forum_bp.post("/forum/likes")
@jwt_required()
def toggle_like():
    body = request.get_json(silent=True) or {}
    target_type = str(body.get("target_type", "")).strip()
    target_id = body.get("target_id")

    if not target_type or target_id is None:
        return fail(40001, "Fields 'target_type' and 'target_id' are required.")
    try:
        target_id = int(target_id)
    except (TypeError, ValueError):
        return fail(40001, "'target_id' must be an integer.")

    try:
        result = forum_service.toggle_like(
            user_id=_current_user_id(),
            target_type=target_type,
            target_id=target_id,
        )
    except ForumError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result)
