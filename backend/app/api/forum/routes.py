"""Forum: posts, comments, likes and image uploads."""

from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUserId, DbSession, OptionalUserId, PageParams
from app.api.errors import ApiError
from app.schemas.common import Envelope, ok
from app.schemas.forum import (
    CommentIn,
    CommentList,
    CommentOut,
    LikeIn,
    LikeResult,
    LongViewResult,
    PostIn,
    PostOut,
    PostPage,
    PostUpdateIn,
    UploadIn,
    UploadResult,
)
from app.services.ai.image_storage_service import ImageStorageError, store_data_url_image
from app.services.forum import forum_service
from app.services.forum.forum_service import ForumError

router = APIRouter(prefix="/api/forum", tags=["forum"])


def _api_error(exc: ForumError) -> ApiError:
    return ApiError(exc.code, exc.message, exc.http_status)


def _optional_int(value: Any, field: str) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(40001, f"'{field}' must be an integer.") from exc


@router.post("/uploads", status_code=201, response_model=Envelope[UploadResult])
def upload_forum_image(_: CurrentUserId, body: UploadIn | None = None):
    image = (body or UploadIn()).image
    if not isinstance(image, str):
        raise ApiError(40001, "Field 'image' must be a base64 data URL string.")
    try:
        url = store_data_url_image(image, namespace="forum")
    except ImageStorageError as exc:
        raise ApiError(40001, str(exc)) from exc
    return ok(UploadResult(url=url))


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------


@router.post("/posts", status_code=201, response_model=Envelope[PostOut])
def create_post(user_id: CurrentUserId, session: DbSession, body: PostIn | None = None):
    body = body or PostIn()
    title, content = body.title.strip(), body.content.strip()
    if not title or not content:
        raise ApiError(40001, "Fields 'title' and 'content' are required.")
    try:
        result = forum_service.create_post(
            session,
            author_id=user_id,
            title=title,
            content=content,
            image_urls_json=body.image_urls_json or None,
        )
    except ForumError as exc:
        raise _api_error(exc) from exc
    return ok(result)


@router.get("/posts", response_model=Envelope[PostPage])
def list_posts(session: DbSession, viewer: OptionalUserId, paging: PageParams):
    return ok(
        forum_service.list_posts(session, paging.page, paging.per_page, viewer_user_id=viewer)
    )


@router.get("/posts/{post_id}", response_model=Envelope[PostOut])
def get_post(post_id: int, session: DbSession, viewer: OptionalUserId):
    try:
        return ok(forum_service.get_post(session, post_id, viewer_user_id=viewer))
    except ForumError as exc:
        raise _api_error(exc) from exc


# reason is only present when nothing was tracked, as before.
@router.post(
    "/posts/{post_id}/long-view",
    status_code=201,
    response_model=Envelope[LongViewResult],
    response_model_exclude_none=True,
)
def record_post_long_view(post_id: int, user_id: CurrentUserId, session: DbSession):
    try:
        result = forum_service.record_post_long_view(session, post_id, viewer_user_id=user_id)
    except ForumError as exc:
        raise _api_error(exc) from exc
    return ok(result)


@router.put("/posts/{post_id}", response_model=Envelope[PostOut])
def update_post(
    post_id: int, user_id: CurrentUserId, session: DbSession, body: PostUpdateIn | None = None
):
    body = body or PostUpdateIn()
    try:
        result = forum_service.update_post(
            session,
            post_id,
            operator_user_id=user_id,
            # Blank means unchanged, as the Flask route had it.
            title=body.title or None,
            content=body.content or None,
            image_urls_json=body.image_urls_json or None,
        )
    except ForumError as exc:
        raise _api_error(exc) from exc
    return ok(result)


@router.delete("/posts/{post_id}", response_model=Envelope[dict[str, Any]])
def delete_post(post_id: int, user_id: CurrentUserId, session: DbSession):
    try:
        forum_service.delete_post(session, post_id, operator_user_id=user_id)
    except ForumError as exc:
        raise _api_error(exc) from exc
    return ok({})


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


@router.post("/posts/{post_id}/comments", status_code=201, response_model=Envelope[CommentOut])
def create_comment(
    post_id: int, user_id: CurrentUserId, session: DbSession, body: CommentIn | None = None
):
    body = body or CommentIn()
    content = body.content.strip()
    if not content:
        raise ApiError(40001, "Field 'content' is required.")
    parent_comment_id = _optional_int(body.parent_comment_id, "parent_comment_id")
    try:
        result = forum_service.create_comment(
            session,
            post_id=post_id,
            user_id=user_id,
            content=content,
            parent_comment_id=parent_comment_id,
        )
    except ForumError as exc:
        raise _api_error(exc) from exc
    return ok(result)


@router.get("/posts/{post_id}/comments", response_model=Envelope[CommentList])
def list_comments(post_id: int, session: DbSession, viewer: OptionalUserId):
    try:
        return ok(forum_service.list_comments(session, post_id, viewer_user_id=viewer))
    except ForumError as exc:
        raise _api_error(exc) from exc


@router.delete("/comments/{comment_id}", response_model=Envelope[dict[str, Any]])
def delete_comment(comment_id: int, user_id: CurrentUserId, session: DbSession):
    try:
        forum_service.delete_comment(session, comment_id, operator_user_id=user_id)
    except ForumError as exc:
        raise _api_error(exc) from exc
    return ok({})


# ---------------------------------------------------------------------------
# Likes
# ---------------------------------------------------------------------------


@router.post("/likes", response_model=Envelope[LikeResult])
def toggle_like(user_id: CurrentUserId, session: DbSession, body: LikeIn | None = None):
    body = body or LikeIn()
    target_type = body.target_type.strip()
    if not target_type or body.target_id is None:
        raise ApiError(40001, "Fields 'target_type' and 'target_id' are required.")
    target_id = _optional_int(body.target_id, "target_id")
    assert target_id is not None
    try:
        result = forum_service.toggle_like(
            session, user_id=user_id, target_type=target_type, target_id=target_id
        )
    except ForumError as exc:
        raise _api_error(exc) from exc
    return ok(result)
