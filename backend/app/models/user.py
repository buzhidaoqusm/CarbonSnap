from datetime import UTC, datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    avatar_url: Mapped[str | None] = mapped_column(String(256))
    bio: Mapped[str | None] = mapped_column(Text)
    total_carbon_amount: Mapped[float] = mapped_column(default=0.0)
    current_points: Mapped[int] = mapped_column(default=0)
    # Compact AI-facing preference summary, stored as JSON text.
    preferences_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
