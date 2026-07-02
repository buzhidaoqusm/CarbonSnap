"""Forum business logic.

Responsibilities:
- CRUD for posts and comments with ownership checks.
- Polymorphic like / unlike with idempotency.
- Trigger RAG chunk persistence after post create / update / delete.
"""

from datetime import datetime, timedelta, timezone

from app.repositories.recommendation import behavior_event_repository
from app.repositories.forum import forum_repository
from app.repositories.profile import user_repository
from app.services.forum import forum_background_job_service
from app.services.notification import notification_service
from app.services.recommendation import behavior_event_service, preference_profile_service
from app.services.recommendation.forum_recommendation_service import rank_posts_for_user


class ForumError(Exception):
    """Known forum errors; carries API error code and HTTP status."""

    def __init__(self, message: str, code: int = 40001, http_status: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


FORUM_LONG_VIEW_DEDUP_WINDOW = timedelta(minutes=30)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _username_for_user(user_id: int) -> str:
    user = user_repository.get_by_id(int(user_id))
    return getattr(user, "username", None) or f"User {user_id}"


def _notify_post_liked(*, post_id: int, recipient_user_id: int | None, liker_user_id: int) -> None:
    if recipient_user_id is None or recipient_user_id == liker_user_id:
        return
    notification_service.on_post_liked(
        recipient_user_id=recipient_user_id,
        post_id=post_id,
        liker_username=_username_for_user(liker_user_id),
    )


def _notify_post_commented(*, post_id: int, recipient_user_id: int | None, commenter_user_id: int) -> None:
    if recipient_user_id is None or recipient_user_id == commenter_user_id:
        return
    notification_service.on_post_commented(
        recipient_user_id=recipient_user_id,
        post_id=post_id,
        commenter_username=_username_for_user(commenter_user_id),
    )


def _notify_comment_replied(*, comment_id: int, recipient_user_id: int | None, replier_user_id: int) -> None:
    if recipient_user_id is None or recipient_user_id == replier_user_id:
        return
    notification_service.on_comment_replied(
        recipient_user_id=recipient_user_id,
        comment_id=comment_id,
        replier_username=_username_for_user(replier_user_id),
    )


def _notify_comment_liked(*, comment_id: int, recipient_user_id: int | None, liker_user_id: int) -> None:
    if recipient_user_id is None or recipient_user_id == liker_user_id:
        return
    notification_service.on_comment_liked(
        recipient_user_id=recipient_user_id,
        comment_id=comment_id,
        liker_username=_username_for_user(liker_user_id),
    )


# ---------------------------------------------------------------------------
# Serializers (keep presentation logic out of the repository layer)
# ---------------------------------------------------------------------------

def _serialize_post(
    post,
    *,
    liked_by_user: bool | None = None,
    like_count: int | None = None,
    comment_count: int | None = None,
) -> dict:
    author = user_repository.get_by_id(int(post.author_id)) if getattr(post, "author_id", None) is not None else None
    return {
        "id": post.id,
        "author_id": post.author_id,
        "author_username": getattr(author, "username", None),
        "author_avatar_url": getattr(author, "avatar_url", None),
        "title": post.title,
        "content": post.content,
        "image_urls_json": post.image_urls_json,
        "status": post.status,
        "like_count": like_count,
        "comment_count": comment_count,
        "liked_by_user": liked_by_user,
        "created_at": post.created_at.isoformat(),
    }


def _serialize_comment(comment, *, liked_by_user: bool | None = None, like_count: int | None = None) -> dict:
    author = user_repository.get_by_id(int(comment.user_id)) if getattr(comment, "user_id", None) is not None else None
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "user_id": comment.user_id,
        "author_username": getattr(author, "username", None),
        "author_avatar_url": getattr(author, "avatar_url", None),
        "parent_comment_id": comment.parent_comment_id,
        "content": comment.content,
        "status": comment.status,
        "like_count": like_count,
        "liked_by_user": liked_by_user,
        "created_at": comment.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Post operations
# ---------------------------------------------------------------------------

def create_post(*, author_id: int, title: str, content: str, image_urls_json: str | None = None) -> dict:
    post = forum_repository.create_post(
        author_id=author_id,
        title=title,
        content=content,
        image_urls_json=image_urls_json,
    )
    forum_background_job_service.enqueue_post_refresh(
        post_id=post.id,
        title=post.title,
        content=post.content,
    )
    return _serialize_post(post, like_count=0, comment_count=0, liked_by_user=False)


def get_post(post_id: int, *, viewer_user_id: int | None = None) -> dict:
    post = forum_repository.get_post_by_id(post_id)
    if post is None:
        raise ForumError("Post not found.", code=40400, http_status=404)
    if viewer_user_id is not None:
        try:
            behavior_event_service.record_forum_view(user_id=viewer_user_id, post_id=post.id)
            preference_profile_service.recompute_user_preference_profiles(viewer_user_id)
        except Exception:
            pass
    like_count = forum_repository.count_likes("post", post_id)
    comment_count = forum_repository.count_comments(post_id)
    liked = (
        forum_repository.is_liked_by(viewer_user_id, "post", post_id)
        if viewer_user_id is not None
        else None
    )
    return _serialize_post(post, like_count=like_count, comment_count=comment_count, liked_by_user=liked)


def record_post_long_view(post_id: int, *, viewer_user_id: int) -> dict:
    post = forum_repository.get_post_by_id(post_id)
    if post is None:
        raise ForumError("Post not found.", code=40400, http_status=404)

    latest_event = behavior_event_repository.get_latest_behavior_event_for_target(
        viewer_user_id,
        domain="forum",
        target_type="post",
        target_id=post.id,
        action_types=["long_view"],
    )
    if latest_event is not None:
        latest_created_at = _ensure_aware_utc(latest_event.created_at)
        if latest_created_at is not None and (_utc_now() - latest_created_at) < FORUM_LONG_VIEW_DEDUP_WINDOW:
            return {"tracked": False, "reason": "deduplicated"}

    try:
        behavior_event_service.record_forum_long_view(user_id=viewer_user_id, post_id=post.id)
        preference_profile_service.recompute_user_preference_profiles(viewer_user_id)
    except Exception:
        return {"tracked": False, "reason": "skipped"}

    return {"tracked": True}


def list_posts(
    page: int,
    per_page: int,
    *,
    viewer_user_id: int | None = None,
) -> dict:
    if viewer_user_id is not None:
        total = forum_repository.count_all_published_posts()
        candidate_limit = max(total, per_page)
        candidate_posts = forum_repository.list_published_posts_for_ranking(candidate_limit=candidate_limit)
        ranked_posts = rank_posts_for_user(posts=candidate_posts, user_id=viewer_user_id)
        start = (page - 1) * per_page
        posts = ranked_posts[start:start + per_page]
    else:
        posts, total = forum_repository.list_posts_page_by_impact(page, per_page)

    items = []
    for post in posts:
        like_count = forum_repository.count_likes("post", post.id)
        comment_count = forum_repository.count_comments(post.id)
        liked = (
            forum_repository.is_liked_by(viewer_user_id, "post", post.id)
            if viewer_user_id is not None
            else None
        )
        items.append(_serialize_post(post, like_count=like_count, comment_count=comment_count, liked_by_user=liked))
    return {"items": items, "total": total, "page": page, "per_page": per_page}


def update_post(
    post_id: int,
    *,
    operator_user_id: int,
    title: str | None = None,
    content: str | None = None,
    image_urls_json: str | None = None,
) -> dict:
    post = forum_repository.get_post_by_id(post_id)
    if post is None:
        raise ForumError("Post not found.", code=40400, http_status=404)
    if post.author_id != operator_user_id:
        raise ForumError("You are not the author of this post.", code=40300, http_status=403)

    post = forum_repository.update_post(
        post,
        title=title,
        content=content,
        image_urls_json=image_urls_json,
    )
    forum_background_job_service.enqueue_post_refresh(
        post_id=post.id,
        title=post.title,
        content=post.content,
    )
    return _serialize_post(post)


def delete_post(post_id: int, *, operator_user_id: int) -> None:
    post = forum_repository.get_post_by_id(post_id)
    if post is None:
        raise ForumError("Post not found.", code=40400, http_status=404)
    if post.author_id != operator_user_id:
        raise ForumError("You are not the author of this post.", code=40300, http_status=403)

    forum_repository.soft_delete_post(post)
    forum_background_job_service.enqueue_post_removal(post_id=post_id)


# ---------------------------------------------------------------------------
# Comment operations
# ---------------------------------------------------------------------------

def create_comment(
    *,
    post_id: int,
    user_id: int,
    content: str,
    parent_comment_id: int | None = None,
) -> dict:
    # Validate parent post exists.
    post = forum_repository.get_post_by_id(post_id)
    if post is None:
        raise ForumError("Post not found.", code=40400, http_status=404)

    # Validate parent comment exists (if replying).
    if parent_comment_id is not None:
        parent = forum_repository.get_comment_by_id(parent_comment_id)
        if parent is None or parent.post_id != post_id:
            raise ForumError("Parent comment not found.", code=40400, http_status=404)

    comment = forum_repository.create_comment(
        post_id=post_id,
        user_id=user_id,
        content=content,
        parent_comment_id=parent_comment_id,
    )
    if parent_comment_id is None:
        _notify_post_commented(
            post_id=post.id,
            recipient_user_id=forum_repository.get_post_author_id(post.id),
            commenter_user_id=user_id,
        )
    else:
        parent_context = forum_repository.get_comment_notification_context(parent_comment_id)
        _notify_comment_replied(
            comment_id=parent_comment_id,
            recipient_user_id=parent_context["author_id"] if parent_context is not None else None,
            replier_user_id=user_id,
        )
    try:
        behavior_event_service.record_forum_comment_or_reply(user_id=user_id, post_id=post_id)
        preference_profile_service.recompute_user_preference_profiles(user_id)
    except Exception:
        pass
    return _serialize_comment(comment, like_count=0, liked_by_user=False)


def list_comments(post_id: int, *, viewer_user_id: int | None = None) -> dict:
    post = forum_repository.get_post_by_id(post_id)
    if post is None:
        raise ForumError("Post not found.", code=40400, http_status=404)

    comments = forum_repository.list_comments_by_post(post_id)
    items = []
    for c in comments:
        like_count = forum_repository.count_likes("comment", c.id)
        liked = (
            forum_repository.is_liked_by(viewer_user_id, "comment", c.id)
            if viewer_user_id is not None
            else None
        )
        items.append(_serialize_comment(c, like_count=like_count, liked_by_user=liked))
    return {"items": items, "total": len(items)}


def delete_comment(comment_id: int, *, operator_user_id: int) -> None:
    comment = forum_repository.get_comment_by_id(comment_id)
    if comment is None:
        raise ForumError("Comment not found.", code=40400, http_status=404)
    if comment.user_id != operator_user_id:
        raise ForumError("You are not the author of this comment.", code=40300, http_status=403)
    forum_repository.soft_delete_comment(comment)


# ---------------------------------------------------------------------------
# Like operations (post & comment, unified)
# ---------------------------------------------------------------------------

def toggle_like(
    *, user_id: int, target_type: str, target_id: int
) -> dict:
    if target_type not in ("post", "comment"):
        raise ForumError("target_type must be 'post' or 'comment'.")

    # Validate target exists.
    if target_type == "post":
        post_author_id = forum_repository.get_post_author_id(target_id)
        if post_author_id is None:
            raise ForumError("Post not found.", code=40400, http_status=404)
    else:
        comment_context = forum_repository.get_comment_notification_context(target_id)
        if comment_context is None:
            raise ForumError("Comment not found.", code=40400, http_status=404)

    liked = forum_repository.toggle_like(
        user_id=user_id, target_type=target_type, target_id=target_id
    )
    try:
        if liked:
            behavior_event_service.record_forum_like(
                user_id=user_id,
                target_type=target_type,
                target_id=target_id,
            )
        else:
            behavior_event_service.record_forum_unlike(
                user_id=user_id,
                target_type=target_type,
                target_id=target_id,
            )
        preference_profile_service.recompute_user_preference_profiles(user_id)
    except Exception:
        pass
    if liked and target_type == "post":
        _notify_post_liked(
            post_id=target_id,
            recipient_user_id=post_author_id,
            liker_user_id=user_id,
        )
    elif liked and target_type == "comment":
        _notify_comment_liked(
            comment_id=target_id,
            recipient_user_id=comment_context["author_id"] if comment_context is not None else None,
            liker_user_id=user_id,
        )
    like_count = forum_repository.count_likes(target_type, target_id)
    return {"liked": liked, "like_count": like_count}


