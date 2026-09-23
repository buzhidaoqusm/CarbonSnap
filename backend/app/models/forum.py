from datetime import UTC, datetime

from app.extensions.db import db


class ForumPost(db.Model):
    __tablename__ = "forum_posts"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.Text, nullable=False)
    # JSON array of image URLs stored as text.
    image_urls_json = db.Column(db.Text)
    # published | deleted  (soft delete)
    status = db.Column(db.String(16), nullable=False, default="published")
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class ForumComment(db.Model):
    __tablename__ = "forum_comments"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("forum_posts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # NULL for top-level comments; set to parent comment id for replies.
    parent_comment_id = db.Column(db.Integer, db.ForeignKey("forum_comments.id"))
    content = db.Column(db.Text, nullable=False)
    # published | deleted  (soft delete)
    status = db.Column(db.String(16), nullable=False, default="published")
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class Like(db.Model):
    __tablename__ = "likes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # post | comment
    target_type = db.Column(db.String(16), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Prevent duplicate likes: one user can only like a target once.
    __table_args__ = (
        db.UniqueConstraint("user_id", "target_type", "target_id", name="uq_likes_user_target"),
    )


class ForumPostChunk(db.Model):
    __tablename__ = "forum_post_chunks"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("forum_posts.id"), nullable=False)
    chunk_text = db.Column(db.Text, nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False, default=0)
    section_title = db.Column(db.String(256))
    chunk_version = db.Column(db.Integer, nullable=False, default=1)
    # Key into the FAISS index. NULL until the chunk has been embedded.
    embedding_id = db.Column(db.String(64))
