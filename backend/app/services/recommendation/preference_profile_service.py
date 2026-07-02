from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp
from typing import Any

from app.repositories.recommendation import behavior_event_repository, preference_profile_repository
from app.services.recommendation.topic_taxonomy import PHASE1_TOPIC_IDS, normalize_topic_id


FORUM_ACTION_WEIGHTS = {
    "view": 1.0,
    "long_view": 2.0,
    "like": 3.0,
    "comment_or_reply": 4.0,
}

AI_ACTION_WEIGHTS = {
    "recycling_case_pending_audit": 1.0,
    "recycling_case_failed_audit": 2.0,
    "recycling_case_passed_audit": 4.0,
    "ai_accept": 4.0,
}

MARKET_ACTION_WEIGHTS = {
    "view": 1.0,
    "long_view": 2.0,
    "market_item_create": 2.0,
    "market_order_completed_as_seller": 4.0,
    "market_order": 5.0,
}

PROJECT_ACTION_WEIGHTS = {
    "view": 1.0,
    "project_create": 2.0,
    "project_contribute": 5.0,
}

DEFAULT_PROFILE_CONFIDENCE_THRESHOLD = 0.6
DEFAULT_PROFILE_EVENT_THRESHOLD = 3
DEFAULT_PROFILE_NORMALIZED_THRESHOLD = 0.35
DEFAULT_PROFILE_LIMIT = 5

ACTION_PREFERENCE_TEMPLATE = {
    "prefer_nearby_options": None,
    "allow_manual_area_input": None,
    "preferred_recycling_methods": [],
    "avoid_recycling_methods": [],
    "max_recycling_distance_km": None,
    "response_style": None,
}


@dataclass(frozen=True)
class TopicContribution:
    topic_id: str
    confidence_score: float


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware_utc(value: datetime | None) -> datetime:
    if value is None:
        return _utc_now()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _load_topic_payload(event: Any) -> list[TopicContribution]:
    try:
        parsed = json.loads(getattr(event, "topic_payload_json", None) or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        parsed = []

    contributions: list[TopicContribution] = []
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict):
            continue
        topic_id = normalize_topic_id(str(item.get("topic_id") or ""))
        try:
            confidence_score = float(item.get("confidence_score") or 0.0)
        except (TypeError, ValueError):
            confidence_score = 0.0
        if not topic_id:
            continue
        contributions.append(
            TopicContribution(
                topic_id=topic_id if topic_id in PHASE1_TOPIC_IDS else "uncategorized",
                confidence_score=max(0.0, min(confidence_score, 1.0)),
            )
        )

    return contributions or [TopicContribution(topic_id="uncategorized", confidence_score=1.0)]


def time_decay_for_event(created_at: datetime, *, now: datetime | None = None) -> float:
    current = _ensure_aware_utc(now)
    event_time = _ensure_aware_utc(created_at)
    age_days = max((current - event_time).total_seconds() / 86400.0, 0.0)
    if age_days <= 7:
        return 1.0
    if age_days <= 30:
        return 0.6
    return 0.3


def normalized_score(raw_score: float) -> float:
    if raw_score <= 0:
        return 0.0
    return min(round(1.0 - exp(-raw_score / 8.0), 6), 0.999999)


def _event_weight(event: Any) -> float | None:
    action_type = str(getattr(event, "action_type", "") or "").strip().lower()
    domain = str(getattr(event, "domain", "") or "").strip().lower()
    if domain == "forum":
        return FORUM_ACTION_WEIGHTS.get(action_type)
    if domain == "ai":
        return AI_ACTION_WEIGHTS.get(action_type)
    if domain == "market":
        return MARKET_ACTION_WEIGHTS.get(action_type)
    if domain == "project":
        return PROJECT_ACTION_WEIGHTS.get(action_type)
    return None


def _topic_bucket() -> dict[str, Any]:
    return {
        "raw_score": 0.0,
        "event_count": 0,
        "confidence_sum": 0.0,
        "confidence_count": 0,
        "last_event_at": None,
        "source_domains": set(),
    }


def _update_bucket(
    bucket: dict[str, Any],
    *,
    delta: float,
    event_created_at: datetime,
    topic_confidence: float,
    source_domain: str,
) -> None:
    bucket["raw_score"] += float(delta)
    bucket["event_count"] += 1
    bucket["confidence_sum"] += float(topic_confidence)
    bucket["confidence_count"] += 1
    bucket["source_domains"].add(str(source_domain).strip().lower())
    event_time = _ensure_aware_utc(event_created_at)
    if bucket["last_event_at"] is None or event_time > bucket["last_event_at"]:
        bucket["last_event_at"] = event_time


def _aggregate_topic_rows(user_id: int) -> list[dict[str, Any]]:
    topic_buckets: dict[str, dict[str, Any]] = defaultdict(_topic_bucket)
    for event in behavior_event_repository.list_behavior_events_for_user(user_id):
        if str(getattr(event, "domain", "") or "").strip().lower() == "forum" and str(
            getattr(event, "action_type", "") or ""
        ).strip().lower() in {"like", "unlike"}:
            continue
        action_weight = _event_weight(event)
        if action_weight is None:
            continue
        decay = time_decay_for_event(event.created_at)
        for contribution in _load_topic_payload(event):
            delta = action_weight * decay * contribution.confidence_score
            _update_bucket(
                topic_buckets[contribution.topic_id],
                delta=delta,
                event_created_at=event.created_at,
                topic_confidence=contribution.confidence_score,
                source_domain=event.domain,
            )

    for event in _list_active_forum_like_events(user_id):
        action_weight = FORUM_ACTION_WEIGHTS["like"]
        decay = time_decay_for_event(event.created_at)
        for contribution in _load_topic_payload(event):
            delta = action_weight * decay * contribution.confidence_score
            _update_bucket(
                topic_buckets[contribution.topic_id],
                delta=delta,
                event_created_at=event.created_at,
                topic_confidence=contribution.confidence_score,
                source_domain=event.domain,
            )

    rows: list[dict[str, Any]] = []
    for topic_id, bucket in topic_buckets.items():
        if bucket["event_count"] <= 0:
            continue
        mean_confidence = (
            bucket["confidence_sum"] / bucket["confidence_count"]
            if bucket["confidence_count"]
            else 0.0
        )
        confidence_score = min(
            1.0,
            round(
                (bucket["event_count"] / 5.0)
                + (mean_confidence * 0.15)
                + (0.05 if len(bucket["source_domains"]) > 1 else 0.0),
                3,
            ),
        )
        rows.append(
            {
                "profile_type": "content_interest",
                "profile_key": topic_id,
                "raw_score": round(bucket["raw_score"], 6),
                "normalized_score": normalized_score(bucket["raw_score"]),
                "confidence_score": confidence_score,
                "event_count": bucket["event_count"],
                "source_domains": sorted(bucket["source_domains"]),
                "last_event_at": bucket["last_event_at"],
            }
        )

    rows.sort(
        key=lambda item: (-float(item["normalized_score"]), -int(item["event_count"]), item["profile_key"])
    )
    return rows


def _list_active_forum_like_events(user_id: int) -> list[Any]:
    latest_by_target: dict[tuple[str, int], Any] = {}
    for event in behavior_event_repository.list_behavior_events_for_user(
        user_id,
        domain="forum",
        action_types=["like", "unlike"],
    ):
        target_type = str(getattr(event, "target_type", "") or "").strip().lower()
        target_id = getattr(event, "target_id", None)
        if not target_type or target_id is None:
            continue
        latest_by_target[(target_type, int(target_id))] = event
    return [
        event
        for event in latest_by_target.values()
        if str(getattr(event, "action_type", "") or "").strip().lower() == "like"
    ]


def recompute_user_preference_profiles(user_id: int):
    rows = _aggregate_topic_rows(user_id)
    return preference_profile_repository.replace_user_preference_profiles(
        user_id=user_id,
        profiles=rows,
    )


def list_content_interest_profiles(user_id: int):
    return preference_profile_repository.list_user_preference_profiles(
        user_id,
        profile_type="content_interest",
    )


def is_promotable_profile(
    profile,
    *,
    min_event_count: int = DEFAULT_PROFILE_EVENT_THRESHOLD,
    min_confidence_score: float = DEFAULT_PROFILE_CONFIDENCE_THRESHOLD,
    min_normalized_score: float = DEFAULT_PROFILE_NORMALIZED_THRESHOLD,
) -> bool:
    return (
        int(profile.event_count or 0) >= min_event_count
        and float(profile.confidence_score or 0.0) >= min_confidence_score
        and float(profile.normalized_score or 0.0) >= min_normalized_score
    )


def has_sufficient_history(user_id: int, *, min_event_count: int = DEFAULT_PROFILE_EVENT_THRESHOLD) -> bool:
    profiles = list_content_interest_profiles(user_id)
    return any(int(profile.event_count or 0) >= min_event_count for profile in profiles)


def list_promotable_topics(
    user_id: int,
    *,
    limit: int = DEFAULT_PROFILE_LIMIT,
    min_event_count: int = DEFAULT_PROFILE_EVENT_THRESHOLD,
    min_confidence_score: float = DEFAULT_PROFILE_CONFIDENCE_THRESHOLD,
    min_normalized_score: float = DEFAULT_PROFILE_NORMALIZED_THRESHOLD,
) -> list[dict[str, Any]]:
    promotable = [
        profile
        for profile in list_content_interest_profiles(user_id)
        if is_promotable_profile(
            profile,
            min_event_count=min_event_count,
            min_confidence_score=min_confidence_score,
            min_normalized_score=min_normalized_score,
        )
    ]
    promotable.sort(
        key=lambda profile: (
            -float(profile.normalized_score or 0.0),
            -int(profile.event_count or 0),
            profile.profile_key,
        )
    )
    return [
        {
            "topic_id": profile.profile_key,
            "score": round(float(profile.normalized_score or 0.0), 3),
            "raw_score": round(float(profile.raw_score or 0.0), 3),
            "confidence_score": round(float(profile.confidence_score or 0.0), 3),
            "event_count": int(profile.event_count or 0),
            "source_domains": json.loads(profile.source_domains_json or "[]")
            if profile.source_domains_json
            else [],
            "last_event_at": profile.last_event_at.isoformat() if profile.last_event_at else None,
        }
        for profile in promotable[:limit]
    ]


def get_profile_snapshot(user_id: int) -> dict[str, float]:
    return {
        item["topic_id"]: float(item["score"])
        for item in list_promotable_topics(
            user_id,
            limit=DEFAULT_PROFILE_LIMIT,
            min_event_count=1,
            min_confidence_score=0.0,
            min_normalized_score=0.0,
        )
    }


def build_user_preference_snapshot(user_id: int) -> dict[str, Any]:
    promotable_topics = list_promotable_topics(
        user_id,
        limit=DEFAULT_PROFILE_LIMIT,
        min_event_count=1,
        min_confidence_score=0.0,
        min_normalized_score=0.0,
    )
    confidence = (
        round(sum(item["score"] for item in promotable_topics) / len(promotable_topics), 3)
        if promotable_topics
        else 0.0
    )
    return {
        "content_interest_preferences": {
            "topics": promotable_topics,
            "confidence_score": confidence,
        },
        "action_preferences": dict(ACTION_PREFERENCE_TEMPLATE),
    }
