from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select

from app.extensions.db import db
from app.models.recommendation import ContentTopicAssignment, UserPreferenceProfile


def _ensure_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_source_domains(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def _serialize_source_domains(values: list[str] | set[str] | None) -> str:
    if not values:
        return "[]"
    unique_values = sorted({str(item).strip().lower() for item in values if str(item).strip()})
    return json.dumps(unique_values, ensure_ascii=False)


def replace_content_topic_assignments(
    *,
    domain: str,
    content_type: str,
    content_id: int,
    topics: list[dict[str, Any]],
    source: str = "ai_constrained",
) -> list[ContentTopicAssignment]:
    normalized_domain = str(domain).strip().lower()
    normalized_content_type = str(content_type).strip().lower()

    db.session.execute(
        delete(ContentTopicAssignment).where(
            ContentTopicAssignment.domain == normalized_domain,
            ContentTopicAssignment.content_type == normalized_content_type,
            ContentTopicAssignment.content_id == content_id,
        )
    )

    rows: list[ContentTopicAssignment] = []
    for item in topics:
        topic_id = str(item.get("topic_id") or "").strip().lower()
        if not topic_id:
            continue
        row = ContentTopicAssignment(
            domain=normalized_domain,
            content_type=normalized_content_type,
            content_id=content_id,
            topic_id=topic_id,
            confidence_score=float(item.get("confidence_score") or 0.0),
            source=str(item.get("source") or source).strip() or source,
        )
        rows.append(row)

    if rows:
        db.session.add_all(rows)
    db.session.commit()
    return rows


def list_content_topic_assignments(
    *,
    domain: str,
    content_type: str,
    content_id: int,
) -> list[ContentTopicAssignment]:
    rows = db.session.scalars(
        select(ContentTopicAssignment)
        .where(
            ContentTopicAssignment.domain == str(domain).strip().lower(),
            ContentTopicAssignment.content_type == str(content_type).strip().lower(),
            ContentTopicAssignment.content_id == content_id,
        )
        .order_by(ContentTopicAssignment.confidence_score.desc(), ContentTopicAssignment.id.asc())
    ).all()
    return list(rows)


def list_content_topic_assignments_for_content_ids(
    *,
    domain: str,
    content_type: str,
    content_ids: list[int],
) -> dict[int, list[ContentTopicAssignment]]:
    normalized_domain = str(domain).strip().lower()
    normalized_content_type = str(content_type).strip().lower()
    normalized_content_ids = [int(content_id) for content_id in content_ids if content_id is not None]
    if not normalized_content_ids:
        return {}

    rows = db.session.scalars(
        select(ContentTopicAssignment)
        .where(
            ContentTopicAssignment.domain == normalized_domain,
            ContentTopicAssignment.content_type == normalized_content_type,
            ContentTopicAssignment.content_id.in_(normalized_content_ids),
        )
        .order_by(
            ContentTopicAssignment.content_id.asc(),
            ContentTopicAssignment.confidence_score.desc(),
            ContentTopicAssignment.id.asc(),
        )
    ).all()

    grouped: dict[int, list[ContentTopicAssignment]] = {}
    for row in rows:
        grouped.setdefault(int(row.content_id), []).append(row)
    return grouped


def get_primary_content_topic_assignment(
    *,
    domain: str,
    content_type: str,
    content_id: int,
) -> ContentTopicAssignment | None:
    return db.session.scalar(
        select(ContentTopicAssignment)
        .where(
            ContentTopicAssignment.domain == str(domain).strip().lower(),
            ContentTopicAssignment.content_type == str(content_type).strip().lower(),
            ContentTopicAssignment.content_id == content_id,
        )
        .order_by(ContentTopicAssignment.confidence_score.desc(), ContentTopicAssignment.id.asc())
    )


def replace_user_preference_profiles(
    *,
    user_id: int,
    profiles: list[dict[str, Any]],
) -> list[UserPreferenceProfile]:
    db.session.execute(delete(UserPreferenceProfile).where(UserPreferenceProfile.user_id == user_id))

    rows: list[UserPreferenceProfile] = []
    for item in profiles:
        profile_type = str(item.get("profile_type") or "").strip().lower()
        profile_key = str(item.get("profile_key") or "").strip().lower()
        if not profile_type or not profile_key:
            continue
        row = UserPreferenceProfile(
            user_id=user_id,
            profile_type=profile_type,
            profile_key=profile_key,
            raw_score=float(item.get("raw_score") or 0.0),
            normalized_score=float(item.get("normalized_score") or 0.0),
            confidence_score=float(item.get("confidence_score") or 0.0),
            event_count=int(item.get("event_count") or 0),
            source_domains_json=_serialize_source_domains(item.get("source_domains")),
            last_event_at=_ensure_aware_utc(item.get("last_event_at")),
        )
        rows.append(row)

    if rows:
        db.session.add_all(rows)
    db.session.commit()
    return rows


def list_user_preference_profiles(
    user_id: int,
    *,
    profile_type: str | None = None,
) -> list[UserPreferenceProfile]:
    stmt = select(UserPreferenceProfile).where(UserPreferenceProfile.user_id == user_id)
    if profile_type:
        stmt = stmt.where(UserPreferenceProfile.profile_type == str(profile_type).strip().lower())

    rows = db.session.scalars(
        stmt.order_by(
            UserPreferenceProfile.normalized_score.desc(),
            UserPreferenceProfile.event_count.desc(),
            UserPreferenceProfile.profile_key.asc(),
        )
    ).all()
    return list(rows)


def serialize_preference_profile(profile: UserPreferenceProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "profile_type": profile.profile_type,
        "profile_key": profile.profile_key,
        "raw_score": float(profile.raw_score or 0.0),
        "normalized_score": float(profile.normalized_score or 0.0),
        "confidence_score": float(profile.confidence_score or 0.0),
        "event_count": int(profile.event_count or 0),
        "source_domains": _parse_source_domains(profile.source_domains_json),
        "last_event_at": profile.last_event_at.isoformat() if profile.last_event_at else None,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }
