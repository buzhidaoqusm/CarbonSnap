from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ForumPost(Base):
    __tablename__ = "forum_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(256))
    content: Mapped[str] = mapped_column(Text)
    # JSON array of image URLs stored as text.
    image_urls_json: Mapped[str | None] = mapped_column(Text)
    # published | deleted  (soft delete)
    status: Mapped[str] = mapped_column(String(16), default="published")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))


class ForumComment(Base):
    __tablename__ = "forum_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("forum_posts.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # NULL for top-level comments; set to parent comment id for replies.
    parent_comment_id: Mapped[int | None] = mapped_column(ForeignKey("forum_comments.id"))
    content: Mapped[str] = mapped_column(Text)
    # published | deleted  (soft delete)
    status: Mapped[str] = mapped_column(String(16), default="published")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))


class Like(Base):
    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # post | comment
    target_type: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    # Prevent duplicate likes: one user can only like a target once.
    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="uq_likes_user_target"),
    )


class ForumPostChunk(Base):
    __tablename__ = "forum_post_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("forum_posts.id"))
    chunk_text: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(default=0)
    section_title: Mapped[str | None] = mapped_column(String(256))
    chunk_version: Mapped[int] = mapped_column(default=1)
    # Key into the FAISS index. NULL until the chunk has been embedded.
    embedding_id: Mapped[str | None] = mapped_column(String(64))
