from __future__ import annotations

import json
from typing import Any

from app.repositories.recommendation import preference_profile_repository
from app.services.ai.openrouter_service import complete_json_diagnostic
from app.services.recommendation.topic_taxonomy import (
    PHASE1_TOPIC_IDS,
    normalize_topic_id,
    recall_topic_candidates,
    topic_label,
)


def _normalize_query_text(*parts: str) -> str:
    return " ".join(str(part or "").strip() for part in parts if str(part or "").strip())


def _clamp_confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(number, 1.0))


def _normalize_selected_topics(
    payload: dict[str, Any] | None,
    *,
    allowed_topic_ids: set[str],
) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []

    raw_selected = payload.get("selected_topics")
    if raw_selected is None and payload.get("topic_id") is not None:
        raw_selected = [payload]

    if not isinstance(raw_selected, list):
        return []

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in raw_selected:
        if not isinstance(item, dict):
            continue

        topic_id = normalize_topic_id(str(item.get("topic_id") or ""))
        if topic_id not in allowed_topic_ids:
            continue

        confidence_score = _clamp_confidence(
            item.get("confidence_score")
            if item.get("confidence_score") is not None
            else item.get("score")
        )
        if confidence_score <= 0.0 or topic_id in seen:
            continue

        normalized.append(
            {
                "topic_id": topic_id,
                "label": topic_label(topic_id),
                "confidence_score": round(confidence_score, 3),
                "source": "ai_constrained",
            }
        )
        seen.add(topic_id)

    normalized.sort(key=lambda item: (-float(item["confidence_score"]), item["topic_id"]))
    return normalized


def select_forum_topics_with_llm(
    *,
    title: str,
    content: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not candidates:
        return []

    allowed_topic_ids = {candidate["topic_id"] for candidate in candidates}
    prompt_payload = {
        "title": title,
        "content": content,
        "candidate_topics": [
            {
                "topic_id": candidate["topic_id"],
                "label": candidate.get("label"),
                "confidence_score": candidate.get("confidence_score"),
            }
            for candidate in candidates
        ],
    }

    diagnostic = complete_json_diagnostic(
        user_message=json.dumps(prompt_payload, ensure_ascii=False),
        system_prompt=_forum_topic_selection_system_prompt(),
    )
    return _normalize_selected_topics(
        diagnostic.get("payload"),
        allowed_topic_ids=allowed_topic_ids,
    )


def select_market_topics_with_llm(
    *,
    title: str,
    description: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not candidates:
        return []

    allowed_topic_ids = {candidate["topic_id"] for candidate in candidates}
    prompt_payload = {
        "title": title,
        "description": description,
        "candidate_topics": [
            {
                "topic_id": candidate["topic_id"],
                "label": candidate.get("label"),
                "confidence_score": candidate.get("confidence_score"),
            }
            for candidate in candidates
        ],
    }

    diagnostic = complete_json_diagnostic(
        user_message=json.dumps(prompt_payload, ensure_ascii=False),
        system_prompt=_market_topic_selection_system_prompt(),
    )
    return _normalize_selected_topics(
        diagnostic.get("payload"),
        allowed_topic_ids=allowed_topic_ids,
    )


def select_project_topics_with_llm(
    *,
    title: str,
    description: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not candidates:
        return []

    allowed_topic_ids = {candidate["topic_id"] for candidate in candidates}
    prompt_payload = {
        "title": title,
        "description": description,
        "candidate_topics": [
            {
                "topic_id": candidate["topic_id"],
                "label": candidate.get("label"),
                "confidence_score": candidate.get("confidence_score"),
            }
            for candidate in candidates
        ],
    }

    diagnostic = complete_json_diagnostic(
        user_message=json.dumps(prompt_payload, ensure_ascii=False),
        system_prompt=_project_topic_selection_system_prompt(),
    )
    return _normalize_selected_topics(
        diagnostic.get("payload"),
        allowed_topic_ids=allowed_topic_ids,
    )


def assign_forum_post_topics(*, title: str, content: str) -> list[dict[str, Any]]:
    query_text = _normalize_query_text(title, content)
    candidates = recall_topic_candidates(query_text)
    if not candidates:
        return [{"topic_id": "uncategorized", "confidence_score": 1.0, "source": "fallback"}]

    selected = select_forum_topics_with_llm(
        title=title,
        content=content,
        candidates=candidates,
    )
    if selected:
        return selected[:3]

    best_candidate = candidates[0]
    return [
        {
            "topic_id": best_candidate["topic_id"],
            "label": best_candidate.get("label"),
            "confidence_score": float(best_candidate.get("confidence_score") or 0.0),
            "source": "rule_recall",
        }
    ]


def assign_market_item_topics(*, title: str, description: str | None = None) -> list[dict[str, Any]]:
    query_text = _normalize_query_text(title, description or "")
    candidates = recall_topic_candidates(query_text)
    if not candidates:
        return [{"topic_id": "uncategorized", "confidence_score": 1.0, "source": "fallback"}]

    selected = select_market_topics_with_llm(
        title=title,
        description=description or "",
        candidates=candidates,
    )
    if selected:
        return selected[:3]

    best_candidate = candidates[0]
    return [
        {
            "topic_id": best_candidate["topic_id"],
            "label": best_candidate.get("label"),
            "confidence_score": float(best_candidate.get("confidence_score") or 0.0),
            "source": "rule_recall",
        }
    ]


def assign_project_topics(*, title: str, description: str | None = None) -> list[dict[str, Any]]:
    query_text = _normalize_query_text(title, description or "")
    candidates = recall_topic_candidates(query_text)
    if not candidates:
        return [{"topic_id": "uncategorized", "confidence_score": 1.0, "source": "fallback"}]

    selected = select_project_topics_with_llm(
        title=title,
        description=description or "",
        candidates=candidates,
    )
    if selected:
        return selected[:3]

    best_candidate = candidates[0]
    return [
        {
            "topic_id": best_candidate["topic_id"],
            "label": best_candidate.get("label"),
            "confidence_score": float(best_candidate.get("confidence_score") or 0.0),
            "source": "rule_recall",
        }
    ]


def refresh_forum_post_topics(*, post_id: int, title: str, content: str) -> list[dict[str, Any]]:
    topics = assign_forum_post_topics(title=title, content=content)
    preference_profile_repository.replace_content_topic_assignments(
        domain="forum",
        content_type="post",
        content_id=post_id,
        topics=topics,
    )
    return topics


def refresh_market_item_topics(*, item_id: int, title: str, description: str | None) -> list[dict[str, Any]]:
    topics = assign_market_item_topics(title=title, description=description)
    preference_profile_repository.replace_content_topic_assignments(
        domain="market",
        content_type="item",
        content_id=item_id,
        topics=topics,
    )
    return topics


def refresh_project_topics(*, project_id: int, title: str, description: str | None) -> list[dict[str, Any]]:
    topics = assign_project_topics(title=title, description=description)
    preference_profile_repository.replace_content_topic_assignments(
        domain="project",
        content_type="project",
        content_id=project_id,
        topics=topics,
    )
    return topics


def _forum_topic_selection_system_prompt() -> str:
    allowed_topics = ", ".join(PHASE1_TOPIC_IDS)
    return f"""
You are assigning fixed sustainability topics to a forum post.
Return exactly one JSON object with a selected_topics array.

Rules:
- Only choose from the allowed topic ids.
- Do not invent new topics.
- Return an empty array if none of the candidate topics fit.

Allowed topic ids:
{allowed_topics}

Expected shape:
{{
  "selected_topics": [
    {{"topic_id": "plastic-recycling", "confidence_score": 0.92}}
  ]
}}
""".strip()


def _market_topic_selection_system_prompt() -> str:
    allowed_topics = ", ".join(PHASE1_TOPIC_IDS)
    return f"""
You are assigning fixed sustainability topics to a market item.
Return exactly one JSON object with a selected_topics array.

Rules:
- Only choose from the allowed topic ids.
- Do not invent new topics.
- Return an empty array if none of the candidate topics fit.

Allowed topic ids:
{allowed_topics}

Expected shape:
{{
  "selected_topics": [
    {{"topic_id": "plastic-recycling", "confidence_score": 0.92}}
  ]
}}
""".strip()


def _project_topic_selection_system_prompt() -> str:
    allowed_topics = ", ".join(PHASE1_TOPIC_IDS)
    return f"""
You are assigning fixed sustainability topics to a community project.
Return exactly one JSON object with a selected_topics array.

Rules:
- Only choose from the allowed topic ids.
- Do not invent new topics.
- Return an empty array if none of the candidate topics fit.

Allowed topic ids:
{allowed_topics}

Expected shape:
{{
  "selected_topics": [
    {{"topic_id": "community-cleanup", "confidence_score": 0.92}}
  ]
}}
""".strip()
