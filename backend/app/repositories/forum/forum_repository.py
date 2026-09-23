from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError

from app.extensions.db import db
from app.models.forum import ForumComment, ForumPost, ForumPostChunk, Like

# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------


def create_post(
    *,
    author_id: int,
    title: str,
    content: str,
    image_urls_json: str | None = None,
) -> ForumPost:
    post = ForumPost(
        author_id=author_id,
        title=title,
        content=content,
        image_urls_json=image_urls_json,
    )
    db.session.add(post)
    db.session.commit()
    return post


def get_post_by_id(post_id: int) -> ForumPost | None:
    """Return a published post, or None if not found / soft-deleted."""
    return db.session.scalar(
        select(ForumPost).where(
            ForumPost.id == post_id,
            ForumPost.status == "published",
        )
    )


def get_post_author_id(post_id: int) -> int | None:
    post = get_post_by_id(post_id)
    if post is None:
        return None
    return int(post.author_id)


def update_post(
    post: ForumPost,
    *,
    title: str | None = None,
    content: str | None = None,
    image_urls_json: str | None = None,
) -> ForumPost:
    if title is not None:
        post.title = title
    if content is not None:
        post.content = content
    if image_urls_json is not None:
        post.image_urls_json = image_urls_json
    db.session.commit()
    return post


def soft_delete_post(post: ForumPost) -> None:
    post.status = "deleted"
    db.session.commit()


def list_posts_page(page: int, per_page: int) -> tuple[list[ForumPost], int]:
    """Return (posts, total) for all published posts, newest first."""
    base = select(ForumPost).where(ForumPost.status == "published")
    total = db.session.scalar(select(func.count()).select_from(base.subquery())) or 0
    posts = db.session.scalars(
        base.order_by(ForumPost.created_at.desc()).limit(per_page).offset((page - 1) * per_page)
    ).all()
    return list(posts), total


def list_posts_page_by_impact(page: int, per_page: int) -> tuple[list[ForumPost], int]:
    """Return (posts, total) for all published posts, ordered by impact."""
    total = (
        db.session.scalar(select(func.count(ForumPost.id)).where(ForumPost.status == "published"))
        or 0
    )

    like_counts = (
        select(
            Like.target_id.label("post_id"),
            func.count(Like.id).label("like_count"),
        )
        .where(Like.target_type == "post")
        .group_by(Like.target_id)
        .subquery()
    )
    comment_counts = (
        select(
            ForumComment.post_id.label("post_id"),
            func.count(ForumComment.id).label("comment_count"),
        )
        .where(ForumComment.status == "published")
        .group_by(ForumComment.post_id)
        .subquery()
    )

    now = datetime.now(UTC)
    recent_three_day_cutoff = now - timedelta(days=3)
    recent_seven_day_cutoff = now - timedelta(days=7)

    like_score = func.coalesce(like_counts.c.like_count, 0)
    comment_score = func.coalesce(comment_counts.c.comment_count, 0) * 2
    recency_bonus = case(
        (ForumPost.created_at >= recent_three_day_cutoff, 2),
        (ForumPost.created_at >= recent_seven_day_cutoff, 1),
        else_=0,
    )
    impact_score = like_score + comment_score + recency_bonus

    posts = db.session.scalars(
        select(ForumPost)
        .outerjoin(like_counts, like_counts.c.post_id == ForumPost.id)
        .outerjoin(comment_counts, comment_counts.c.post_id == ForumPost.id)
        .where(ForumPost.status == "published")
        .order_by(
            impact_score.desc(),
            ForumPost.created_at.desc(),
            ForumPost.id.desc(),
        )
        .limit(per_page)
        .offset((page - 1) * per_page)
    ).all()
    return list(posts), total


def list_all_published_posts() -> list[ForumPost]:
    return list(
        db.session.scalars(
            select(ForumPost)
            .where(ForumPost.status == "published")
            .order_by(ForumPost.created_at.desc(), ForumPost.id.desc())
        ).all()
    )


def count_all_published_posts() -> int:
    return (
        db.session.scalar(select(func.count(ForumPost.id)).where(ForumPost.status == "published"))
        or 0
    )


def list_published_posts_for_ranking(*, candidate_limit: int) -> list[ForumPost]:
    if candidate_limit <= 0:
        return []
    return list(
        db.session.scalars(
            select(ForumPost)
            .where(ForumPost.status == "published")
            .order_by(ForumPost.created_at.desc(), ForumPost.id.desc())
            .limit(candidate_limit)
        ).all()
    )


def list_posts_by_ids(post_ids: list[int]) -> list[ForumPost]:
    if not post_ids:
        return []

    return list(
        db.session.scalars(
            select(ForumPost)
            .where(
                ForumPost.id.in_(post_ids),
                ForumPost.status == "published",
            )
            .order_by(ForumPost.created_at.desc(), ForumPost.id.desc())
        ).all()
    )


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


def create_comment(
    *,
    post_id: int,
    user_id: int,
    content: str,
    parent_comment_id: int | None = None,
) -> ForumComment:
    comment = ForumComment(
        post_id=post_id,
        user_id=user_id,
        content=content,
        parent_comment_id=parent_comment_id,
    )
    db.session.add(comment)
    db.session.commit()
    return comment


def get_comment_by_id(comment_id: int) -> ForumComment | None:
    return db.session.scalar(
        select(ForumComment).where(
            ForumComment.id == comment_id,
            ForumComment.status == "published",
        )
    )


def get_comment_notification_context(comment_id: int) -> dict | None:
    comment = get_comment_by_id(comment_id)
    if comment is None:
        return None

    return {
        "comment_id": int(comment.id),
        "post_id": int(comment.post_id),
        "author_id": int(comment.user_id),
        "parent_comment_id": int(comment.parent_comment_id)
        if comment.parent_comment_id is not None
        else None,
    }


def soft_delete_comment(comment: ForumComment) -> None:
    comment.status = "deleted"
    db.session.commit()


def list_comments_by_post(post_id: int) -> list[ForumComment]:
    """Return all published comments for a post, ordered oldest first."""
    return list(
        db.session.scalars(
            select(ForumComment)
            .where(
                ForumComment.post_id == post_id,
                ForumComment.status == "published",
            )
            .order_by(ForumComment.created_at.asc())
        ).all()
    )


# ---------------------------------------------------------------------------
# Likes  (polymorphic: target_type = 'post' | 'comment')
# ---------------------------------------------------------------------------


def toggle_like(*, user_id: int, target_type: str, target_id: int) -> bool:
    """Toggle like state. Returns True if liked, False if unliked."""
    existing = db.session.scalar(
        select(Like).where(
            Like.user_id == user_id,
            Like.target_type == target_type,
            Like.target_id == target_id,
        )
    )
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return False
    else:
        like = Like(user_id=user_id, target_type=target_type, target_id=target_id)
        db.session.add(like)
        try:
            db.session.commit()
        except IntegrityError:
            # Race condition: another request inserted simultaneously — treat as liked.
            db.session.rollback()
        return True


def count_likes(target_type: str, target_id: int) -> int:
    return (
        db.session.scalar(
            select(func.count(Like.id)).where(
                Like.target_type == target_type,
                Like.target_id == target_id,
            )
        )
        or 0
    )


def count_comments(post_id: int) -> int:
    return (
        db.session.scalar(
            select(func.count(ForumComment.id)).where(
                ForumComment.post_id == post_id,
                ForumComment.status == "published",
            )
        )
        or 0
    )


def is_liked_by(user_id: int, target_type: str, target_id: int) -> bool:
    return (
        db.session.scalar(
            select(Like).where(
                Like.user_id == user_id,
                Like.target_type == target_type,
                Like.target_id == target_id,
            )
        )
        is not None
    )


# ---------------------------------------------------------------------------
# RAG chunks
# ---------------------------------------------------------------------------


def save_post_chunks(post_id: int, chunks: list[str | dict]) -> list[ForumPostChunk]:
    """Persist a list of chunks for a post (replaces old chunks)."""
    # Remove stale chunks first.
    old = db.session.scalars(select(ForumPostChunk).where(ForumPostChunk.post_id == post_id)).all()
    for c in old:
        db.session.delete(c)

    new_chunks = []
    for index, item in enumerate(chunks):
        if isinstance(item, dict):
            new_chunks.append(
                ForumPostChunk(
                    post_id=post_id,
                    chunk_text=item["chunk_text"],
                    chunk_index=int(item.get("chunk_index", index)),
                    section_title=item.get("section_title"),
                    chunk_version=int(item.get("chunk_version", 1)),
                    embedding_id=item.get("embedding_id"),
                )
            )
        else:
            new_chunks.append(
                ForumPostChunk(
                    post_id=post_id,
                    chunk_text=item,
                    chunk_index=index,
                    section_title="Main",
                    chunk_version=1,
                )
            )
    db.session.add_all(new_chunks)
    db.session.commit()
    return new_chunks


def get_chunks_by_post(post_id: int) -> list[ForumPostChunk]:
    return list(
        db.session.scalars(
            select(ForumPostChunk)
            .where(ForumPostChunk.post_id == post_id)
            .order_by(ForumPostChunk.chunk_version.desc(), ForumPostChunk.chunk_index.asc())
        ).all()
    )


def get_latest_chunk_version(post_id: int) -> int:
    return (
        db.session.scalar(
            select(func.max(ForumPostChunk.chunk_version)).where(ForumPostChunk.post_id == post_id)
        )
        or 0
    )


def list_active_chunks() -> list[tuple[ForumPostChunk, ForumPost]]:
    rows = db.session.execute(
        select(ForumPostChunk, ForumPost)
        .join(ForumPost, ForumPost.id == ForumPostChunk.post_id)
        .where(ForumPost.status == "published")
        .order_by(
            ForumPost.created_at.desc(),
            ForumPost.id.desc(),
            ForumPostChunk.chunk_version.desc(),
            ForumPostChunk.chunk_index.asc(),
        )
    ).all()
    return [(row[0], row[1]) for row in rows]


def list_active_chunks_by_embedding_ids(
    embedding_ids: list[str],
) -> list[tuple[ForumPostChunk, ForumPost]]:
    if not embedding_ids:
        return []

    rows = db.session.execute(
        select(ForumPostChunk, ForumPost)
        .join(ForumPost, ForumPost.id == ForumPostChunk.post_id)
        .where(
            ForumPost.status == "published",
            ForumPostChunk.embedding_id.in_(embedding_ids),
        )
    ).all()
    return [(row[0], row[1]) for row in rows]
