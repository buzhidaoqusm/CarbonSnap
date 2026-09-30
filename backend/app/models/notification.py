from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # e.g. post_liked | post_commented | comment_replied | order_shipped | project_completed
    event_type: Mapped[str] = mapped_column(String(32))
    # e.g. forum_post | forum_comment | order | project
    # Used by the frontend to construct the correct navigation link.
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[int] = mapped_column()
    title: Mapped[str] = mapped_column(String(256))
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
