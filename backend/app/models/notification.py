from datetime import datetime, timezone

from app.extensions.db import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    recipient_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # e.g. post_liked | post_commented | comment_replied | order_shipped | project_completed
    event_type = db.Column(db.String(32), nullable=False)
    # e.g. forum_post | forum_comment | order | project
    # Used by the frontend to construct the correct navigation link.
    source_type = db.Column(db.String(32), nullable=False)
    source_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(256), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
