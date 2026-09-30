from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserBehaviorEvent(Base):
    __tablename__ = "user_behavior_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # forum | project | market | ai
    domain: Mapped[str] = mapped_column(String(32))
    # view | like | comment | buy | contribute | ai_accept
    action_type: Mapped[str] = mapped_column(String(32))
    target_type: Mapped[str | None] = mapped_column(String(32))
    target_id: Mapped[int] = mapped_column()
    topic_payload_json: Mapped[str | None] = mapped_column(Text)
    context_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))


class ContentTopicAssignment(Base):
    __tablename__ = "content_topic_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    domain: Mapped[str] = mapped_column(String(32))
    content_type: Mapped[str] = mapped_column(String(32))
    content_id: Mapped[int] = mapped_column()
    topic_id: Mapped[str] = mapped_column(String(64))
    confidence_score: Mapped[float] = mapped_column(default=0.0)
    source: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint(
            "domain",
            "content_type",
            "content_id",
            "topic_id",
            name="uq_content_topic_assignments_content_topic",
        ),
    )


class UserPreferenceProfile(Base):
    __tablename__ = "user_preference_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    profile_type: Mapped[str] = mapped_column(String(32))
    profile_key: Mapped[str] = mapped_column(String(128))
    raw_score: Mapped[float] = mapped_column(default=0.0)
    normalized_score: Mapped[float] = mapped_column(default=0.0)
    confidence_score: Mapped[float] = mapped_column(default=0.0)
    event_count: Mapped[int] = mapped_column(default=0)
    source_domains_json: Mapped[str] = mapped_column(Text, default="[]")
    last_event_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "profile_type",
            "profile_key",
            name="uq_user_preference_profiles_user_profile_key",
        ),
    )
