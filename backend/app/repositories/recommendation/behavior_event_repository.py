from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.extensions.db import db
from app.models.recommendation import UserBehaviorEvent


def _ensure_aware_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_behavior_event(
    *,
    user_id: int,
    domain: str,
    action_type: str,
    target_type: str | None,
    target_id: int,
    topic_payload: list[dict[str, Any]] | None = None,
    context: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> UserBehaviorEvent:
    event = UserBehaviorEvent(
        user_id=user_id,
        domain=str(domain).strip().lower(),
        action_type=str(action_type).strip().lower(),
        target_type=str(target_type).strip().lower() if target_type else None,
        target_id=target_id,
        topic_payload_json=json.dumps(topic_payload or [], ensure_ascii=False)
        if topic_payload is not None
        else None,
        context_json=json.dumps(context or {}, ensure_ascii=False)
        if context is not None
        else None,
    )
    event.created_at = _ensure_aware_utc(created_at)
    db.session.add(event)
    db.session.commit()
    return event


def list_behavior_events_for_user(
    user_id: int,
    *,
    domain: str | None = None,
    action_types: list[str] | None = None,
) -> list[UserBehaviorEvent]:
    stmt = select(UserBehaviorEvent).where(UserBehaviorEvent.user_id == user_id)

    if domain:
        stmt = stmt.where(UserBehaviorEvent.domain == str(domain).strip().lower())
    if action_types:
        normalized_actions = [str(item).strip().lower() for item in action_types if str(item).strip()]
        if normalized_actions:
            stmt = stmt.where(UserBehaviorEvent.action_type.in_(normalized_actions))

    rows = db.session.scalars(
        stmt.order_by(UserBehaviorEvent.created_at.asc(), UserBehaviorEvent.id.asc())
    ).all()
    return list(rows)


def list_recent_behavior_events_for_user(
    user_id: int,
    *,
    limit: int = 100,
    domain: str | None = None,
) -> list[UserBehaviorEvent]:
    stmt = select(UserBehaviorEvent).where(UserBehaviorEvent.user_id == user_id)
    if domain:
        stmt = stmt.where(UserBehaviorEvent.domain == str(domain).strip().lower())

    rows = db.session.scalars(
        stmt.order_by(UserBehaviorEvent.created_at.desc(), UserBehaviorEvent.id.desc()).limit(limit)
    ).all()
    return list(rows)


def list_recent_topic_exposure_counts_for_user(
    user_id: int,
    *,
    domain: str | None = None,
    limit: int = 100,
    action_types: list[str] | None = None,
) -> dict[str, int]:
    """Count recent topic exposures from topic payload snapshots."""
    events = list_recent_behavior_events_for_user(
        user_id,
        domain=domain,
        limit=limit,
    )

    normalized_actions = None
    if action_types:
        normalized_actions = {str(item).strip().lower() for item in action_types if str(item).strip()}

    counts: dict[str, int] = {}
    for event in events:
        if normalized_actions is not None and str(event.action_type or "").strip().lower() not in normalized_actions:
            continue
        try:
            payload = json.loads(event.topic_payload_json or "[]")
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(payload, list):
            continue
        for item in payload:
            if not isinstance(item, dict):
                continue
            topic_id = str(item.get("topic_id") or "").strip().lower()
            if not topic_id:
                continue
            counts[topic_id] = counts.get(topic_id, 0) + 1
    return counts


def count_behavior_events_for_user(user_id: int, *, domain: str | None = None) -> int:
    stmt = select(UserBehaviorEvent).where(UserBehaviorEvent.user_id == user_id)
    if domain:
        stmt = stmt.where(UserBehaviorEvent.domain == str(domain).strip().lower())
    return len(db.session.scalars(stmt).all())


def get_latest_behavior_event_for_user(
    user_id: int,
    *,
    domain: str | None = None,
) -> UserBehaviorEvent | None:
    stmt = select(UserBehaviorEvent).where(UserBehaviorEvent.user_id == user_id)
    if domain:
        stmt = stmt.where(UserBehaviorEvent.domain == str(domain).strip().lower())
    return db.session.scalar(
        stmt.order_by(UserBehaviorEvent.created_at.desc(), UserBehaviorEvent.id.desc())
    )


def get_latest_behavior_event_for_target(
    user_id: int,
    *,
    target_id: int,
    domain: str | None = None,
    target_type: str | None = None,
    action_types: list[str] | None = None,
) -> UserBehaviorEvent | None:
    stmt = select(UserBehaviorEvent).where(
        UserBehaviorEvent.user_id == user_id,
        UserBehaviorEvent.target_id == target_id,
    )
    if domain:
        stmt = stmt.where(UserBehaviorEvent.domain == str(domain).strip().lower())
    if target_type:
        stmt = stmt.where(UserBehaviorEvent.target_type == str(target_type).strip().lower())
    if action_types:
        normalized_actions = [str(item).strip().lower() for item in action_types if str(item).strip()]
        if normalized_actions:
            stmt = stmt.where(UserBehaviorEvent.action_type.in_(normalized_actions))
    return db.session.scalar(
        stmt.order_by(UserBehaviorEvent.created_at.desc(), UserBehaviorEvent.id.desc())
    )


def list_behavior_target_ids_for_user(
    user_id: int,
    *,
    domain: str | None = None,
    target_type: str | None = None,
    action_types: list[str] | None = None,
) -> set[int]:
    stmt = select(UserBehaviorEvent.target_id).where(UserBehaviorEvent.user_id == user_id)
    if domain:
        stmt = stmt.where(UserBehaviorEvent.domain == str(domain).strip().lower())
    if target_type:
        stmt = stmt.where(UserBehaviorEvent.target_type == str(target_type).strip().lower())
    if action_types:
        normalized_actions = [str(item).strip().lower() for item in action_types if str(item).strip()]
        if normalized_actions:
            stmt = stmt.where(UserBehaviorEvent.action_type.in_(normalized_actions))
    return {int(target_id) for target_id in db.session.scalars(stmt).all() if target_id is not None}


def list_active_forum_like_target_ids_for_user(
    user_id: int,
    *,
    target_type: str = "post",
) -> set[int]:
    normalized_target_type = str(target_type).strip().lower()
    latest_by_target: dict[int, UserBehaviorEvent] = {}
    for event in list_behavior_events_for_user(
        user_id,
        domain="forum",
        action_types=["like", "unlike"],
    ):
        if str(event.target_type or "").strip().lower() != normalized_target_type:
            continue
        latest_by_target[int(event.target_id)] = event
    return {
        int(target_id)
        for target_id, event in latest_by_target.items()
        if str(event.action_type or "").strip().lower() == "like"
    }
