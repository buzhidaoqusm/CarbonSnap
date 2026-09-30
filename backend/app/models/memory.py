from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserMemoryItem(Base):
    __tablename__ = "user_memory_items"
    __table_args__ = (
        Index(
            "ix_user_memory_items_user_status_type_key",
            "user_id",
            "status",
            "memory_type",
            "memory_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    memory_type: Mapped[str] = mapped_column(String(32))
    memory_key: Mapped[str] = mapped_column(String(128))
    value_json: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(32))
    source_message_id: Mapped[int | None] = mapped_column(ForeignKey("ai_messages.id"))
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("ai_conversations.id"))
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
