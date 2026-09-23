from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.extensions.db import db
from app.models.memory import UserMemoryItem
from app.models.user import User
from app.repositories.ai import memory_repository
from app.services.recommendation import preference_profile_service
from app.services.recommendation.topic_taxonomy import (
    map_recycling_item_to_topics,
    normalize_topic_id,
)

SUPPORTED_MEMORY_TYPES = {
    "response_style",
    "recycling_preference",
    "topic_interest",
    "item_method_preference",
}

SUPPORTED_SOURCE_TYPES = {"explicit_chat", "manual_edit"}

EXPLICIT_ONLY_ACTION_KEYS = {
    "max_recycling_distance_km",
    "preferred_recycling_methods",
    "avoid_recycling_methods",
}

BEHAVIOR_INFERRED_ACTION_KEYS = {
    "prefer_nearby_options",
    "allow_manual_area_input",
    "response_style",
}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_value_json(value_json: str | None) -> dict[str, Any]:
    if not value_json:
        return {}
    try:
        parsed = json.loads(value_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_summary_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def serialize_memory_item(item: UserMemoryItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "user_id": item.user_id,
        "memory_type": item.memory_type,
        "memory_key": item.memory_key,
        "value": _parse_value_json(item.value_json),
        "source_type": item.source_type,
        "source_message_id": item.source_message_id,
        "conversation_id": item.conversation_id,
        "status": item.status,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def validate_memory_payload(
    *,
    memory_type: str,
    memory_key: str,
    value: dict[str, Any],
    source_type: str,
) -> None:
    if memory_type not in SUPPORTED_MEMORY_TYPES:
        raise ValueError(f"Unsupported memory_type: {memory_type}")
    if source_type not in SUPPORTED_SOURCE_TYPES:
        raise ValueError(f"Unsupported source_type: {source_type}")
    if not memory_key.strip():
        raise ValueError("memory_key is required.")
    if not isinstance(value, dict) or not value:
        raise ValueError("value must be a non-empty object.")


def _empty_summary() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": _utc_now_iso(),
        "content_interest_preferences": {
            "topics": [],
            "confidence_score": 0.0,
        },
        "action_preferences": {
            "prefer_nearby_options": None,
            "allow_manual_area_input": None,
            "preferred_recycling_methods": [],
            "avoid_recycling_methods": [],
            "max_recycling_distance_km": None,
            "response_style": None,
        },
    }


def _topic_entry(
    *,
    topic_id: str,
    score: float,
    event_count: int = 0,
    confidence_score: float | None = None,
    source_domains: list[str] | None = None,
    last_event_at: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    entry = {
        "topic_id": normalize_topic_id(topic_id),
        "score": round(float(score or 0.0), 3),
    }
    if event_count:
        entry["event_count"] = int(event_count)
        entry["source_count"] = int(event_count)
    if confidence_score is not None:
        entry["confidence_score"] = round(float(confidence_score or 0.0), 3)
    if source_domains:
        entry["source_domains"] = list(source_domains)
    if last_event_at:
        entry["last_event_at"] = last_event_at
    if source:
        entry["source"] = source
    return entry


def _merge_explicit_topics(
    profile_topics: list[dict[str, Any]],
    explicit_topics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged = {topic["topic_id"]: dict(topic) for topic in profile_topics}
    for topic in explicit_topics:
        existing = merged.get(topic["topic_id"])
        if existing is None or float(topic["score"]) >= float(existing.get("score") or 0.0):
            merged[topic["topic_id"]] = dict(topic)
    return sorted(
        merged.values(),
        key=lambda item: (
            -float(item.get("score") or 0.0),
            -int(item.get("event_count") or 0),
            item["topic_id"],
        ),
    )[:5]


def build_preferences_summary(
    items: list[UserMemoryItem],
    *,
    user_id: int | None = None,
) -> dict[str, Any]:
    summary = _empty_summary()
    explicit_topics: list[dict[str, Any]] = []
    profile_snapshot = (
        preference_profile_service.build_user_preference_snapshot(user_id)
        if user_id
        else _empty_summary()
    )

    for item in items:
        value = _parse_value_json(item.value_json)
        action_preferences = summary["action_preferences"]

        if item.memory_type == "response_style":
            action_preferences["response_style"] = value.get("value")
        elif item.memory_type == "recycling_preference":
            if "value" not in value:
                continue
            if item.memory_key in BEHAVIOR_INFERRED_ACTION_KEYS | EXPLICIT_ONLY_ACTION_KEYS:
                action_preferences[item.memory_key] = value["value"]
        elif item.memory_type == "topic_interest":
            topic_name = str(value.get("topic") or item.memory_key).strip()
            mapped_topics = map_recycling_item_to_topics(topic_name)
            topic_id = normalize_topic_id(
                str(mapped_topics[0]["topic_id"] if mapped_topics else topic_name)
            )
            explicit_topics.append(
                _topic_entry(
                    topic_id=topic_id,
                    score=1.0,
                    source="explicit_memory",
                )
            )
        elif item.memory_type == "item_method_preference":
            preferred_method = value.get("preferred_method")
            item_type = value.get("item_type") or item.memory_key
            if item_type and preferred_method:
                action_preferences["preferred_recycling_methods"].append(
                    {
                        "item_type": item_type,
                        "preferred_method": preferred_method,
                    }
                )

    profile_topics = (profile_snapshot.get("content_interest_preferences") or {}).get(
        "topics"
    ) or []
    summary["content_interest_preferences"] = {
        "topics": _merge_explicit_topics(profile_topics, explicit_topics),
        "confidence_score": round(
            max(
                float(
                    (profile_snapshot.get("content_interest_preferences") or {}).get(
                        "confidence_score"
                    )
                    or 0.0
                ),
                1.0 if explicit_topics else 0.0,
            ),
            3,
        ),
    }

    for key, value in (profile_snapshot.get("action_preferences") or {}).items():
        if key in BEHAVIOR_INFERRED_ACTION_KEYS and summary["action_preferences"].get(key) is None:
            summary["action_preferences"][key] = value

    return summary


def build_current_preferences_summary(
    user_id: int,
    *,
    include_stored_fallback: bool = True,
) -> dict[str, Any]:
    items = memory_repository.list_active_memory_items(user_id)
    summary = build_preferences_summary(items, user_id=user_id)
    if summary["content_interest_preferences"]["topics"] or any(
        value not in (None, [], {}) for value in summary["action_preferences"].values()
    ):
        return summary

    if not include_stored_fallback:
        return summary

    user = db.session.get(User, user_id)
    if user is None:
        return summary
    fallback = _parse_summary_json(user.preferences_json)
    return fallback or summary


def rebuild_user_preferences_summary(user_id: int) -> dict[str, Any]:
    summary = build_current_preferences_summary(user_id, include_stored_fallback=False)
    user = db.session.get(User, user_id)
    if user is None:
        return summary
    user.preferences_json = json.dumps(summary, ensure_ascii=False)
    db.session.commit()
    return summary


def get_prompt_memory_summary(user_id: int | None) -> dict[str, Any]:
    if user_id is None:
        return {}
    user = db.session.get(User, user_id)
    if user is None:
        return {}
    return build_current_preferences_summary(user_id)


def upsert_memory_item(
    *,
    user_id: int,
    memory_type: str,
    memory_key: str,
    value: dict[str, Any],
    source_type: str,
    source_message_id: int | None = None,
    conversation_id: int | None = None,
) -> UserMemoryItem:
    validate_memory_payload(
        memory_type=memory_type,
        memory_key=memory_key,
        value=value,
        source_type=source_type,
    )
    item = memory_repository.replace_memory_item(
        user_id=user_id,
        memory_type=memory_type,
        memory_key=memory_key,
        value_json=json.dumps(value, ensure_ascii=False),
        source_type=source_type,
        source_message_id=source_message_id,
        conversation_id=conversation_id,
    )
    rebuild_user_preferences_summary(user_id)
    return item


def create_manual_memory_item(
    *,
    user_id: int,
    memory_type: str,
    memory_key: str,
    value: dict[str, Any],
) -> UserMemoryItem:
    return upsert_memory_item(
        user_id=user_id,
        memory_type=memory_type,
        memory_key=memory_key,
        value=value,
        source_type="manual_edit",
    )


def update_manual_memory_item(
    *,
    item_id: int,
    user_id: int,
    memory_type: str | None = None,
    memory_key: str | None = None,
    value: dict[str, Any] | None = None,
) -> UserMemoryItem:
    item = memory_repository.get_memory_item(item_id, user_id)
    if item is None:
        raise ValueError("Memory item not found.")
    if item.status != "active":
        raise ValueError("Memory item is deleted.")

    next_type = memory_type or item.memory_type
    next_key = memory_key or item.memory_key
    next_value = value if value is not None else _parse_value_json(item.value_json)
    validate_memory_payload(
        memory_type=next_type,
        memory_key=next_key,
        value=next_value,
        source_type="manual_edit",
    )

    updated = memory_repository.update_memory_item(
        item_id,
        user_id,
        memory_type=next_type,
        memory_key=next_key,
        value_json=json.dumps(next_value, ensure_ascii=False),
    )
    if updated is None:
        raise ValueError("Memory item not found.")

    rebuild_user_preferences_summary(user_id)
    return updated


def delete_memory_item(*, item_id: int, user_id: int) -> UserMemoryItem:
    item = memory_repository.soft_delete_memory_item(item_id, user_id)
    if item is None:
        raise ValueError("Memory item not found.")
    rebuild_user_preferences_summary(user_id)
    return item


def list_memory_payload(user_id: int) -> dict[str, Any]:
    items = memory_repository.list_active_memory_items(user_id)
    summary = rebuild_user_preferences_summary(user_id)
    return {
        "summary": summary,
        "items": [serialize_memory_item(item) for item in items],
    }
