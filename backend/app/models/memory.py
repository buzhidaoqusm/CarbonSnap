from datetime import datetime, timezone

from app.extensions.db import db


class UserMemoryItem(db.Model):
    __tablename__ = "user_memory_items"
    __table_args__ = (
        db.Index(
            "ix_user_memory_items_user_status_type_key",
            "user_id",
            "status",
            "memory_type",
            "memory_key",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    memory_type = db.Column(db.String(32), nullable=False)
    memory_key = db.Column(db.String(128), nullable=False)
    value_json = db.Column(db.Text, nullable=False)
    source_type = db.Column(db.String(32), nullable=False)
    source_message_id = db.Column(db.Integer, db.ForeignKey("ai_messages.id"))
    conversation_id = db.Column(db.Integer, db.ForeignKey("ai_conversations.id"))
    status = db.Column(db.String(16), nullable=False, default="active")
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
