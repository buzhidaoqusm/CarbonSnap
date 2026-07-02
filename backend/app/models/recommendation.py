from __future__ import annotations

from datetime import datetime, timezone

from app.extensions.db import db


class UserBehaviorEvent(db.Model):
    __tablename__ = "user_behavior_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # forum | project | market | ai
    domain = db.Column(db.String(32), nullable=False)
    # view | like | comment | buy | contribute | ai_accept
    action_type = db.Column(db.String(32), nullable=False)
    target_type = db.Column(db.String(32))
    target_id = db.Column(db.Integer, nullable=False)
    topic_payload_json = db.Column(db.Text)
    context_json = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class ContentTopicAssignment(db.Model):
    __tablename__ = "content_topic_assignments"

    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(32), nullable=False)
    content_type = db.Column(db.String(32), nullable=False)
    content_id = db.Column(db.Integer, nullable=False)
    topic_id = db.Column(db.String(64), nullable=False)
    confidence_score = db.Column(db.Float, nullable=False, default=0.0)
    source = db.Column(db.String(32), nullable=False)
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

    __table_args__ = (
        db.UniqueConstraint(
            "domain",
            "content_type",
            "content_id",
            "topic_id",
            name="uq_content_topic_assignments_content_topic",
        ),
    )


class UserPreferenceProfile(db.Model):
    __tablename__ = "user_preference_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    profile_type = db.Column(db.String(32), nullable=False)
    profile_key = db.Column(db.String(128), nullable=False)
    raw_score = db.Column(db.Float, nullable=False, default=0.0)
    normalized_score = db.Column(db.Float, nullable=False, default=0.0)
    confidence_score = db.Column(db.Float, nullable=False, default=0.0)
    event_count = db.Column(db.Integer, nullable=False, default=0)
    source_domains_json = db.Column(db.Text, nullable=False, default="[]")
    last_event_at = db.Column(db.DateTime)
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

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "profile_type",
            "profile_key",
            name="uq_user_preference_profiles_user_profile_key",
        ),
    )
