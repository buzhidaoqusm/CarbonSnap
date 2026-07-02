from __future__ import annotations

import json
from typing import Any

from app.extensions.db import db
from app.models.ai import AIConversation
from app.repositories.ai import conversation_repository, recycling_case_repository
from app.services.ai.memory_service import get_prompt_memory_summary
from app.services.ai.openrouter_service import history_from_message_records


def _clip_text(text: str, limit: int = 200) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


def _parse_json(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def build_recent_history(
    *,
    conversation_id: int | None,
    supplied_history: list[dict[str, Any]] | None = None,
    max_turns: int = 10,
) -> list[dict[str, str]]:
    if conversation_id is None:
        history = supplied_history or []
    else:
        history = history_from_message_records(conversation_repository.list_messages(conversation_id))

    cleaned: list[dict[str, str]] = []
    for item in history:
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            cleaned.append({"role": role, "content": content})

    if max_turns <= 0:
        return cleaned
    return cleaned[-(max_turns * 2) :]


def build_case_summaries(conversation_id: int | None) -> list[dict[str, Any]]:
    if conversation_id is None:
        return []

    cases = recycling_case_repository.list_cases_for_conversation(conversation_id)
    summaries: list[dict[str, Any]] = []
    for case in cases:
        summaries.append(
            {
                "case_id": case.id,
                "predicted_item": case.waste_type_predicted,
                "current_stage": _case_stage(case),
                "status": case.status,
                "created_at": case.created_at.isoformat() if case.created_at else None,
                "updated_at": case.updated_at.isoformat() if case.updated_at else None,
                "has_nearby_results": False,
                "has_verification_attempts": int(case.latest_audit_attempt_no or 0) > 0,
                "expected_carbon_points": case.expected_carbon_points,
                "user_original_request": _resolve_case_origin_request(conversation_id, case.origin_message_id),
            }
        )
    return summaries


def build_conversation_working_memory(conversation_id: int | None) -> dict[str, Any]:
    if conversation_id is None:
        return {}

    messages = conversation_repository.list_messages(conversation_id)
    conversation = db.session.get(AIConversation, conversation_id)
    latest_tool_result = ""
    latest_audit_result = ""
    latest_analysis = ""

    for message in messages:
        content_text = str(getattr(message, "content_text", "") or "").strip()
        if not content_text:
            continue
        message_type = str(getattr(message, "message_type", "") or "").strip().lower()
        if message_type == "analysis_result":
            latest_analysis = _clip_text(content_text)
        elif message_type == "tool_result":
            latest_tool_result = _clip_text(content_text)
        elif message_type == "audit_result":
            latest_audit_result = _clip_text(content_text)

    session_context = None
    if conversation is not None:
        session_context = _parse_json(conversation.session_context_json)

    return {
        "latest_analysis": latest_analysis,
        "latest_nearby_guidance": latest_tool_result,
        "latest_verification_feedback": latest_audit_result,
        "session_context": session_context,
        "conversation_state": {
            "status": getattr(conversation, "status", None),
            "current_pending_action": getattr(conversation, "current_pending_action", None),
        },
    }


def build_context_bundle(
    *,
    conversation_id: int | None,
    supplied_history: list[dict[str, Any]] | None = None,
    max_turns: int = 10,
) -> dict[str, Any]:
    return {
        "recent_history": build_recent_history(
            conversation_id=conversation_id,
            supplied_history=supplied_history,
            max_turns=max_turns,
        ),
        "case_summaries": build_case_summaries(conversation_id),
        "working_memory": build_conversation_working_memory(conversation_id),
    }


def build_runtime_reply_context(
    *,
    conversation_id: int | None,
    user_id: int | None,
    supplied_history: list[dict[str, Any]] | None = None,
    max_turns: int = 10,
    prompt_memory: dict[str, Any] | None = None,
    client_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context_bundle = build_context_bundle(
        conversation_id=conversation_id,
        supplied_history=supplied_history,
        max_turns=max_turns,
    )
    working_memory = dict(context_bundle.get("working_memory") or {})
    session_context = working_memory.get("session_context") or {}
    location_state = dict(session_context.get("location_state") or {})
    paused_context = dict(session_context.get("paused_context") or {})
    selected_audit_attempt = _normalize_selected_audit_attempt(client_context)

    return {
        "conversation_id": conversation_id,
        "recent_history": context_bundle.get("recent_history") or [],
        "case_summaries": context_bundle.get("case_summaries") or [],
        "working_memory": working_memory,
        "location_state": location_state,
        "paused_context": paused_context,
        "selected_audit_attempt": selected_audit_attempt,
        "long_term_memory": (
            dict(prompt_memory)
            if prompt_memory is not None
            else get_prompt_memory_summary(user_id)
        ),
    }


def _normalize_selected_audit_attempt(client_context: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(client_context, dict):
        return None

    raw = client_context.get("selected_audit_attempt")
    if not isinstance(raw, dict):
        return None

    try:
        case_id = int(raw.get("case_id"))
        attempt_no = int(raw.get("attempt_no"))
    except (TypeError, ValueError):
        return None

    if case_id <= 0 or attempt_no <= 0:
        return None

    audit_result = str(raw.get("audit_result") or "").strip().lower()
    if audit_result not in {"passed", "failed", "unclear"}:
        audit_result = ""

    return {
        "case_id": case_id,
        "attempt_no": attempt_no,
        "audit_result": audit_result,
    }


def _case_stage(case: Any) -> str:
    if case.status == "audit_passed":
        return "verified"
    if case.latest_audit_attempt_no:
        return "verification_pending"
    if case.status in {"pending_audit", "audit_failed"}:
        return "analysis_ready"
    return case.status or "analysis_ready"


def _resolve_case_origin_request(conversation_id: int, origin_message_id: int) -> str:
    messages = conversation_repository.list_messages(conversation_id)
    for message in messages:
        if getattr(message, "id", None) == origin_message_id:
            return _clip_text(getattr(message, "content_text", "") or "")
    return ""
