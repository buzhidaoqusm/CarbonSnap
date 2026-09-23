from __future__ import annotations

import json
import re
from collections.abc import Generator
from datetime import date, datetime
from typing import Any

from flask import current_app
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.ai.tools.map.osm_public_provider import MapProviderError, OSMPublicMapProvider
from app.repositories.ai import conversation_repository, recycling_case_repository
from app.services.ai.ai_decision_engine import persist_message_decision
from app.services.ai.conversation_context_builder import build_runtime_reply_context
from app.services.ai.forum_retrieval_service import (
    build_forum_prompt_block,
    extract_used_forum_references,
    resolve_explicit_forum_references,
    retrieve_forum_references,
)
from app.services.ai.image_storage_service import store_data_url_image
from app.services.ai.memory_service import (
    get_prompt_memory_summary,
    rebuild_user_preferences_summary,
    upsert_memory_item,
)
from app.services.ai.neo4j_graph_retrieval_service import (
    build_graph_prompt_block,
    query_graph_context,
)
from app.services.ai.openrouter_service import (
    complete_json,
    generate_conversation_title,
    stream_text,
)
from app.services.ai.recycling_audit_service import stream_recycling_audit
from app.services.ai.recycling_session_service import (
    clear_paused_context,
    create_or_get_session,
    get_paused_context,
    get_valid_location_state,
    serialize_session,
    set_paused_context,
    set_workflow_reference,
    update_location_state,
)
from app.services.recommendation import behavior_event_service, preference_profile_service

LOCATION_OPTIONS = [
    {"key": "allow_browser_location", "label": "Allow browser location"},
    {"key": "enter_manual_area", "label": "Enter area manually"},
    {"key": "skip_nearby_search", "label": "Skip nearby search"},
]


def _build_forum_query(
    *,
    message: str,
    runtime_context: dict[str, Any] | None = None,
    analysis_payload: dict[str, Any] | None = None,
    case: Any | None = None,
) -> str:
    parts = [str(message or "").strip()]
    if case is not None:
        if getattr(case, "waste_type_predicted", None):
            parts.append(f"Related recycling item: {case.waste_type_predicted}")
        if getattr(case, "status", None):
            parts.append(f"Case status: {case.status}")
    if analysis_payload:
        waste_type = str(analysis_payload.get("waste_type") or "").strip()
        if waste_type:
            parts.append(f"Waste type: {waste_type}")
        for suggestion in analysis_payload.get("recycle_suggestions") or []:
            if suggestion:
                parts.append(str(suggestion))
    working_memory = (runtime_context or {}).get("working_memory") or {}
    for key in ("latest_analysis", "latest_nearby_guidance", "latest_verification_feedback"):
        value = str(working_memory.get(key) or "").strip()
        if value:
            parts.append(value)
    return "\n".join(part for part in parts if part)


def _retrieve_forum_candidates(
    *,
    message: str,
    runtime_context: dict[str, Any] | None = None,
    analysis_payload: dict[str, Any] | None = None,
    case: Any | None = None,
    decision: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if isinstance(decision, dict) and not decision.get("should_retrieve_forum", False):
        return []
    result = retrieve_forum_references(
        query=_build_forum_query(
            message=message,
            runtime_context=runtime_context,
            analysis_payload=analysis_payload,
            case=case,
        )
    )
    return result.get("candidates") or []


def _retrieve_graph_context(
    *,
    message: str,
    runtime_context: dict[str, Any] | None = None,
    analysis_payload: dict[str, Any] | None = None,
    case: Any | None = None,
) -> dict[str, Any]:
    return query_graph_context(
        _build_forum_query(
            message=message,
            runtime_context=runtime_context,
            analysis_payload=analysis_payload,
            case=case,
        )
    )


def _runtime_context_note(runtime_context: dict[str, Any] | None) -> str:
    if not runtime_context:
        return ""

    parts: list[str] = []
    working_memory = runtime_context.get("working_memory") or {}
    if working_memory.get("latest_analysis"):
        parts.append(f"Latest analysis: {working_memory['latest_analysis']}")
    if working_memory.get("latest_nearby_guidance"):
        parts.append(f"Latest nearby guidance: {working_memory['latest_nearby_guidance']}")
    if working_memory.get("latest_verification_feedback"):
        parts.append(
            f"Latest verification feedback: {working_memory['latest_verification_feedback']}"
        )
    selected_audit_attempt = runtime_context.get("selected_audit_attempt") or {}
    if selected_audit_attempt.get("case_id") and selected_audit_attempt.get("attempt_no"):
        parts.append(
            "Selected audit attempt in view: "
            f"case {selected_audit_attempt['case_id']} attempt {selected_audit_attempt['attempt_no']} "
            f"({selected_audit_attempt.get('audit_result') or 'unknown'})"
        )

    for case in (runtime_context.get("case_summaries") or [])[:4]:
        parts.append(
            f"Case {case.get('case_id')}: "
            f"{case.get('predicted_item') or 'Unknown item'} "
            f"({case.get('current_stage') or case.get('status') or 'unknown'})"
        )

    if not parts:
        return ""
    return "Conversation working memory: " + " | ".join(parts)


def _extract_attempt_no_from_message(message: str) -> int | None:
    lowered = str(message or "").strip().lower()
    if not lowered:
        return None

    ordinal_map = {
        "first": 1,
        "second": 2,
        "third": 3,
        "fourth": 4,
        "fifth": 5,
    }
    for word, value in ordinal_map.items():
        if f"{word} attempt" in lowered:
            return value

    match = re.search(r"\b(?:attempt\s*#?\s*|#)(\d+)\b", lowered)
    if match:
        try:
            parsed = int(match.group(1))
            return parsed if parsed > 0 else None
        except (TypeError, ValueError):
            return None

    ordinal_digit_match = re.search(r"\b(\d+)(?:st|nd|rd|th)\s+attempt\b", lowered)
    if ordinal_digit_match:
        try:
            parsed = int(ordinal_digit_match.group(1))
            return parsed if parsed > 0 else None
        except (TypeError, ValueError):
            return None

    return None


def _resolve_selected_audit_attempt(
    *,
    case: Any,
    message: str,
    runtime_context: dict[str, Any] | None = None,
):
    attempts = recycling_case_repository.list_audit_attempts(case.id)
    if not attempts:
        return None

    selected_from_context = (runtime_context or {}).get("selected_audit_attempt") or {}
    if int(selected_from_context.get("case_id") or 0) == int(case.id):
        selected_attempt_no = int(selected_from_context.get("attempt_no") or 0)
        for attempt in attempts:
            if int(getattr(attempt, "attempt_no", 0) or 0) == selected_attempt_no:
                return attempt

    requested_attempt_no = _extract_attempt_no_from_message(message)
    if requested_attempt_no is not None:
        for attempt in attempts:
            if int(getattr(attempt, "attempt_no", 0) or 0) == requested_attempt_no:
                return attempt

    return None


def _selected_audit_attempt_note(
    *,
    case: Any,
    message: str,
    runtime_context: dict[str, Any] | None = None,
) -> str:
    selected_attempt = _resolve_selected_audit_attempt(
        case=case,
        message=message,
        runtime_context=runtime_context,
    )
    if selected_attempt is None:
        return ""

    selected_payload = {
        "attempt_no": getattr(selected_attempt, "attempt_no", None),
        "audit_result": getattr(selected_attempt, "audit_result", None),
        "audit_reason": getattr(selected_attempt, "audit_reason", None),
        "audit_image_url": getattr(selected_attempt, "audit_image_url", None),
    }
    note = (
        "Selected audit attempt context: "
        f"{json.dumps(_make_json_safe(selected_payload), ensure_ascii=False)}. "
        "If the user asks why this attempt failed, unclear, or passed, answer about this attempt first."
    )

    lowered = str(message or "").strip().lower()
    if "fail" in lowered and str(selected_payload.get("audit_result") or "").lower() == "unclear":
        note += " The user called it failed, but the recorded result was unclear, so gently correct that wording."

    return note


def _get_authenticated_user_id() -> int | None:
    try:
        verify_jwt_in_request(optional=True)
    except Exception:
        return None

    identity = get_jwt_identity()
    if identity is None:
        return None

    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


def _sync_conversation_session_context(
    conversation_id: int | None, session: dict[str, Any]
) -> None:
    if conversation_id is None:
        return

    conversation_repository.update_conversation_state(
        conversation_id,
        session_context_json=json.dumps(serialize_session(session), ensure_ascii=False),
    )


def _parse_session_context(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _parse_optional_int(value: Any) -> int | None:
    if value in (None, "", "None", "null"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _location_state_ttl_seconds(location_state: dict[str, Any]) -> int:
    if str(location_state.get("location_source") or "").lower() == "manual":
        return current_app.config["AI_MANUAL_LOCATION_TTL_HOURS"] * 3600
    return current_app.config["AI_BROWSER_LOCATION_TTL_MINUTES"] * 60


def _restore_session_from_persisted_context(
    *,
    session_id: str,
    user_id: int | None,
    conversation_id: int | None = None,
) -> dict[str, Any] | None:
    if not session_id or user_id is None:
        return None

    if conversation_id is not None:
        conversation_candidates = [
            conversation_repository.get_conversation(conversation_id, user_id)
        ]
    else:
        conversation_candidates = conversation_repository.list_conversations(
            user_id=user_id, limit=100
        )

    for conversation in conversation_candidates:
        if conversation is None:
            continue

        session_context = _parse_session_context(conversation.session_context_json)
        if not session_context or str(session_context.get("session_id") or "") != session_id:
            continue

        paused_context = session_context.get("paused_context")
        if isinstance(paused_context, dict) and paused_context:
            session = set_paused_context(session_id, paused_context)
        else:
            session = create_or_get_session(session_id)

        session = set_workflow_reference(
            session_id,
            conversation_id=conversation.id,
            recycling_case_id=_parse_optional_int(session_context.get("recycling_case_id")),
        )

        location_state = session_context.get("location_state")
        if isinstance(location_state, dict):
            coordinates = location_state.get("coordinates")
            if not isinstance(coordinates, dict):
                coordinates = None
            session = update_location_state(
                session_id,
                permission_state=location_state.get("permission_state"),
                location_source=location_state.get("location_source"),
                coordinates=coordinates,
                manual_area=location_state.get("manual_area"),
                normalized_area=location_state.get("normalized_area"),
                skip_nearby_search=bool(location_state.get("skip_nearby_search")),
                ttl_seconds=_location_state_ttl_seconds(location_state),
            )

        _sync_conversation_session_context(conversation.id, session)
        return session

    return None


def _resolve_authenticated_conversation(
    *,
    session: dict[str, Any],
    user_id: int,
    title: str,
    conversation_id: int | None = None,
) -> tuple[Any, dict[str, Any]]:
    if conversation_id is not None:
        conversation = conversation_repository.get_conversation(conversation_id, user_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found.")
        session = set_workflow_reference(session["session_id"], conversation_id=conversation.id)
        _sync_conversation_session_context(conversation.id, session)
        return conversation, session

    conversation_id = session.get("conversation_id")
    if conversation_id is not None:
        conversation = conversation_repository.get_conversation(conversation_id, user_id)
        if conversation is not None:
            return conversation, session

    conversation = conversation_repository.create_conversation(user_id=user_id, title=title)
    session = set_workflow_reference(session["session_id"], conversation_id=conversation.id)
    _sync_conversation_session_context(conversation.id, session)
    return conversation, session


def _build_recycling_title(message: str, image_data_url: str | None = None) -> str:
    return generate_conversation_title(
        user_message=message,
        image_data_url=image_data_url,
        fallback_title="Recycling analysis",
    )


def _create_recycling_case(
    *,
    session: dict[str, Any],
    user_id: int,
    conversation_id: int,
    origin_message_id: int,
    analysis_payload: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    case = recycling_case_repository.create_recycling_case(
        user_id=user_id,
        conversation_id=conversation_id,
        origin_message_id=origin_message_id,
        waste_type_predicted=analysis_payload["waste_type"],
        confidence=analysis_payload["confidence"],
        estimated_weight_kg=analysis_payload["estimated_weight_kg"],
        expected_co2_saved_kg=analysis_payload["co2_saved_kg"],
        expected_carbon_points=analysis_payload["carbon_points"],
    )
    try:
        behavior_event_service.record_ai_recycling_case_pending_audit(
            user_id=user_id,
            recycling_case_id=case.id,
        )
        preference_profile_service.recompute_user_preference_profiles(user_id)
    except Exception:
        pass
    rebuild_user_preferences_summary(user_id)
    session = set_workflow_reference(session["session_id"], recycling_case_id=case.id)
    return case, session


def _persist_memory_candidates(
    *,
    user_id: int | None,
    conversation_id: int | None,
    source_message_id: int | None,
    candidates: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if user_id is None or conversation_id is None or source_message_id is None or not candidates:
        return []

    updates: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            item = upsert_memory_item(
                user_id=user_id,
                memory_type=candidate["memory_type"],
                memory_key=candidate["memory_key"],
                value=candidate["value"],
                source_type="explicit_chat",
                source_message_id=source_message_id,
                conversation_id=conversation_id,
            )
            updates.append(
                {
                    "id": item.id,
                    "memory_type": item.memory_type,
                    "memory_key": item.memory_key,
                }
            )
        except Exception:
            continue
    return updates


def _analysis_payload_from_case(case: Any) -> dict[str, Any]:
    return {
        "waste_type": case.waste_type_predicted,
        "confidence": case.confidence,
        "estimated_weight_kg": case.estimated_weight_kg,
        "co2_saved_kg": round(float(case.expected_co2_saved_kg or 0.0), 2),
        "carbon_points": round(float(case.expected_carbon_points or 0.0), 2),
        "recycle_suggestions": [],
        "forum_references": [],
        "requires_location_decision": True,
    }


def _persist_recycling_assistant_message(
    *,
    conversation_id: int,
    message_type: str,
    content_text: str,
    stream_stage: str,
    analysis_payload: dict[str, Any],
    recycling_case_id: int | None = None,
    nearby_locations: list[dict[str, Any]] | None = None,
    location_state: dict[str, Any] | None = None,
) -> Any:
    content_json = {
        "stream_stage": stream_stage,
        "analysis_payload": analysis_payload,
    }
    if recycling_case_id is not None:
        content_json["recycling_case_id"] = recycling_case_id
    if nearby_locations is not None:
        content_json["nearby_locations"] = nearby_locations
    if location_state is not None:
        content_json["location_state"] = _make_json_safe(location_state)

    return conversation_repository.append_message(
        conversation_id=conversation_id,
        role="assistant",
        message_type=message_type,
        content_text=content_text,
        content_json=json.dumps(content_json, ensure_ascii=False),
    )


def stream_recycling_analysis(
    *,
    message: str,
    image_data_url: str | None,
    session_id: str | None,
    conversation_id: int | None = None,
    user_id: int | None = None,
    decision: dict[str, Any] | None = None,
    client_context: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    session = create_or_get_session(session_id)
    active_session_id = session["session_id"]
    effective_user_id = user_id if user_id is not None else _get_authenticated_user_id()
    prompt_memory = (
        decision.get("prompt_memory")
        if isinstance(decision, dict) and decision.get("prompt_memory") is not None
        else get_prompt_memory_summary(effective_user_id)
    )
    conversation = None
    user_message = None
    stored_image_url = (
        store_data_url_image(image_data_url, namespace="recycling-analysis")
        if image_data_url
        else None
    )

    if effective_user_id is not None:
        conversation, session = _resolve_authenticated_conversation(
            session=session,
            user_id=effective_user_id,
            title=_build_recycling_title(message, image_data_url),
            conversation_id=conversation_id,
        )
        user_message = conversation_repository.append_message(
            conversation_id=conversation.id,
            role="user",
            message_type="image" if image_data_url else "text",
            content_text=message,
            content_json=json.dumps(
                {
                    "has_image": bool(image_data_url),
                    "image_url": stored_image_url,
                },
                ensure_ascii=False,
            ),
        )
        session = set_workflow_reference(
            active_session_id,
            conversation_id=conversation.id,
        )
        _sync_conversation_session_context(conversation.id, session)
        _persist_memory_candidates(
            user_id=effective_user_id,
            conversation_id=conversation.id,
            source_message_id=user_message.id,
            candidates=(decision or {}).get("memory_candidates") or [],
        )
        if decision is not None:
            persist_message_decision(
                conversation_id=conversation.id,
                user_message_id=user_message.id,
                decision=decision,
            )
    runtime_context = build_runtime_reply_context(
        conversation_id=conversation.id if conversation is not None else conversation_id,
        user_id=effective_user_id,
        max_turns=int(current_app.config.get("AI_SHORT_TERM_MEMORY_TURNS", 10) or 10),
        prompt_memory=prompt_memory,
        client_context=client_context,
    )

    yield {
        "type": "meta",
        "session_id": active_session_id,
        "conversation_id": conversation.id if conversation is not None else None,
        "conversation_title": conversation.title if conversation is not None else None,
        "user_message_id": user_message.id if user_message is not None else None,
        "decision": {
            key: value
            for key, value in (decision or {}).items()
            if key not in {"context", "prompt_memory"}
        },
    }

    if decision and decision.get("intent") == "recycling_follow_up":
        target_case_id = decision.get("target_case_id")
        case = None
        if target_case_id and effective_user_id is not None:
            case = recycling_case_repository.get_case(int(target_case_id), effective_user_id)

        if case is None and conversation is not None:
            pending_case = recycling_case_repository.get_pending_case_for_conversation(
                conversation.id
            )
            case = pending_case

        if case is None:
            yield {"type": "stage_start", "stage": "follow_up"}
            for event in stream_text(
                user_message=(
                    "The user asked a recycling follow-up, but no matching recycling case was found in "
                    f"this conversation. User message: {message}"
                ),
                system_prompt=(
                    "You are CarbonSnap's recycling assistant. Explain briefly that there is no matching "
                    "recycling task in the current chat and invite the user to start a new recycling analysis."
                ),
                prompt_memory=prompt_memory,
            ):
                if event["type"] == "meta":
                    continue
                if event["type"] == "delta":
                    yield {"type": "delta", "stage": "follow_up", "content": event["content"]}
            yield {"type": "done", "stream_stage": "completed"}
            return

        analysis_payload = _analysis_payload_from_case(case)
        follow_up_type = decision.get("follow_up_type")
        forum_candidates = _retrieve_forum_candidates(
            message=message,
            runtime_context=runtime_context,
            analysis_payload=analysis_payload,
            case=case,
            decision=decision,
        )
        graph_context = _retrieve_graph_context(
            message=message,
            runtime_context=runtime_context,
            analysis_payload=analysis_payload,
            case=case,
        )

        if follow_up_type == "nearby_search":
            yield {"type": "stage_start", "stage": "nearby_search"}
            valid_location_state = get_valid_location_state(active_session_id)
            if valid_location_state and _can_execute_nearby_search(valid_location_state):
                session = set_workflow_reference(
                    active_session_id,
                    conversation_id=conversation.id
                    if conversation is not None
                    else conversation_id,
                    recycling_case_id=case.id,
                )
                _sync_conversation_session_context(
                    conversation.id if conversation is not None else None, session
                )
                yield from _stream_nearby_stage(
                    session_id=active_session_id,
                    user_id=effective_user_id,
                    conversation_id=conversation.id
                    if conversation is not None
                    else conversation_id,
                    analysis_payload=analysis_payload,
                    location_state=valid_location_state,
                    prompt_memory=prompt_memory,
                )
                return

            session = set_paused_context(
                active_session_id,
                {
                    "analysis_payload": analysis_payload,
                    "original_prompt": message,
                    "conversation_id": conversation.id
                    if conversation is not None
                    else conversation_id,
                    "recycling_case_id": case.id,
                    "user_message_id": user_message.id if user_message is not None else None,
                },
            )
            if conversation is not None:
                _sync_conversation_session_context(conversation.id, session)
                conversation_repository.update_conversation_state(
                    conversation.id,
                    status="awaiting_location",
                    current_pending_action="location_permission",
                    session_context_json=json.dumps(serialize_session(session), ensure_ascii=False),
                )

            yield {
                "type": "awaiting_location",
                "data": {
                    "requires_location_decision": True,
                    "stream_stage": "awaiting_location",
                    "location_options": LOCATION_OPTIONS,
                    "session_id": active_session_id,
                    "permission_state": "unknown",
                    "recycling_case_id": case.id,
                },
            }
            yield {"type": "done", "stream_stage": "awaiting_location"}
            return

        if follow_up_type == "task_verification" and image_data_url and conversation is not None:
            yield from stream_recycling_audit(
                conversation_id=conversation.id,
                recycling_case_id=case.id,
                message=message,
                image_data_url=image_data_url,
            )
            return

        yield {"type": "stage_start", "stage": "follow_up"}
        follow_up_chunks: list[str] = []
        for event in stream_text(
            user_message=(
                "Continue the existing recycling case with a helpful Markdown answer.\n"
                f"User follow-up: {message}\n"
                f"Case summary: {json.dumps(_make_json_safe(analysis_payload), ensure_ascii=False)}\n"
                f"{_selected_audit_attempt_note(case=case, message=message, runtime_context=runtime_context)}\n"
                f"{_runtime_context_note(runtime_context)}\n"
                f"{build_forum_prompt_block(forum_candidates)}\n"
                f"{build_graph_prompt_block(graph_context)}"
            ),
            system_prompt=(
                "You are CarbonSnap's recycling assistant. Answer the user's recycling follow-up using "
                "the current case only. If a selected audit attempt context is present, answer that attempt "
                "specifically before giving broader case guidance. Use concise Markdown. Do not wrap the whole "
                "answer in backticks."
            ),
            prompt_memory=prompt_memory,
        ):
            if event["type"] == "meta":
                continue
            if event["type"] == "delta":
                follow_up_chunks.append(event["content"])
                yield {"type": "delta", "stage": "follow_up", "content": event["content"]}

        forum_references = _resolve_response_forum_references(
            "".join(follow_up_chunks),
            forum_candidates,
            graph_context,
        )
        analysis_payload["forum_references"] = forum_references
        analysis_payload["graph_context"] = graph_context

        if conversation is not None:
            _persist_recycling_assistant_message(
                conversation_id=conversation.id,
                message_type="tool_result",
                content_text="".join(follow_up_chunks).strip() or "Recycling follow-up completed.",
                stream_stage="completed",
                analysis_payload=analysis_payload,
                recycling_case_id=case.id,
            )
            conversation_repository.update_conversation_state(
                conversation.id,
                status="completed",
                current_pending_action="none",
            )
        yield {
            "type": "done",
            "stream_stage": "completed",
            "forum_references": forum_references,
            "graph_context": graph_context,
        }
        return

    yield {"type": "stage_start", "stage": "analysis"}

    stage1_graph_context = _retrieve_graph_context(
        message=message,
        runtime_context=runtime_context,
    )
    analysis = _analyze_stage1(
        message=message,
        image_data_url=image_data_url,
        prompt_memory=prompt_memory,
        forum_candidates=_retrieve_forum_candidates(
            message=message,
            runtime_context=runtime_context,
            decision=decision,
        ),
        graph_context=stage1_graph_context,
    )
    analysis["graph_context"] = stage1_graph_context
    payload = _build_stage_payload(analysis=analysis, nearby_locations=[], stream_stage="analysis")
    yield {"type": "stage_payload", "stage": "analysis", "data": payload}

    stage1_chunks: list[str] = []
    yield from _stream_stage1_markdown(
        analysis=payload,
        original_prompt=message,
        prompt_memory=prompt_memory,
        runtime_context=runtime_context,
        collector=stage1_chunks,
    )

    if effective_user_id is not None and conversation is not None and user_message is not None:
        case, session = _create_recycling_case(
            session=session,
            user_id=effective_user_id,
            conversation_id=conversation.id,
            origin_message_id=user_message.id,
            analysis_payload=payload,
        )
        session = set_workflow_reference(
            active_session_id,
            conversation_id=conversation.id,
            recycling_case_id=case.id,
        )
        _sync_conversation_session_context(conversation.id, session)

        stage1_reply = "".join(stage1_chunks).strip() or "Recycling analysis completed."
        stage1_message = _persist_recycling_assistant_message(
            conversation_id=conversation.id,
            message_type="analysis_result",
            content_text=stage1_reply,
            stream_stage="analysis",
            analysis_payload=payload,
            recycling_case_id=case.id,
        )
        yield {
            "type": "stage_payload",
            "stage": "analysis",
            "data": {
                **payload,
                "conversation_id": conversation.id,
                "user_message_id": user_message.id,
                "recycling_case_id": case.id,
                "assistant_message_id": stage1_message.id,
            },
        }

    valid_location_state = get_valid_location_state(active_session_id)
    needs_nearby_search = bool(payload["requires_location_decision"])

    if not needs_nearby_search:
        clear_paused_context(active_session_id)
        if effective_user_id is not None and conversation is not None:
            session = create_or_get_session(active_session_id)
            _sync_conversation_session_context(conversation.id, session)
            conversation_repository.update_conversation_state(
                conversation.id,
                status="completed",
                current_pending_action="none",
                session_context_json=json.dumps(serialize_session(session), ensure_ascii=False),
            )
        yield {"type": "done", "stream_stage": "completed"}
        return

    if valid_location_state and _can_execute_nearby_search(valid_location_state):
        yield from _stream_nearby_stage(
            session_id=active_session_id,
            user_id=effective_user_id,
            conversation_id=conversation.id if conversation is not None else None,
            analysis_payload=payload,
            location_state=valid_location_state,
            prompt_memory=prompt_memory,
            runtime_context=runtime_context,
        )
        return

    session = set_paused_context(
        active_session_id,
        {
            "analysis_payload": payload,
            "original_prompt": message,
            "conversation_id": conversation.id
            if conversation is not None
            else session.get("conversation_id"),
            "recycling_case_id": session.get("recycling_case_id"),
            "user_message_id": user_message.id if user_message is not None else None,
        },
    )
    if effective_user_id is not None and conversation is not None:
        _sync_conversation_session_context(conversation.id, session)
        conversation_repository.update_conversation_state(
            conversation.id,
            status="awaiting_location",
            current_pending_action="location_permission",
            session_context_json=json.dumps(serialize_session(session), ensure_ascii=False),
        )

    yield {
        "type": "awaiting_location",
        "data": {
            "requires_location_decision": True,
            "stream_stage": "awaiting_location",
            "location_options": LOCATION_OPTIONS,
            "session_id": active_session_id,
            "permission_state": (valid_location_state or {}).get("permission_state", "unknown"),
        },
    }
    yield {"type": "done", "stream_stage": "awaiting_location"}


def complete_recycling_analysis(
    *,
    user_id: int | None,
    message: str,
    image_data_url: str | None,
    conversation_id: int | None = None,
    decision: dict[str, Any] | None = None,
    client_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reply_parts: list[str] = []
    meta: dict[str, Any] = {}
    final_stage = "completed"
    clarification: dict[str, Any] | None = None

    for event in stream_recycling_analysis(
        message=message,
        image_data_url=image_data_url,
        session_id=None,
        conversation_id=conversation_id,
        user_id=user_id,
        decision=decision,
        client_context=client_context,
    ):
        event_type = event.get("type")
        if event_type == "meta":
            meta = event
        elif event_type == "delta":
            reply_parts.append(str(event.get("content", "")))
        elif event_type == "awaiting_location":
            clarification = event.get("data") or {}
        elif event_type == "done":
            final_stage = str(event.get("stream_stage") or "completed")

    return {
        "reply": "".join(reply_parts).strip(),
        "model": None,
        "usage": {},
        "conversation_id": meta.get("conversation_id"),
        "conversation_title": meta.get("conversation_title"),
        "user_message_id": meta.get("user_message_id"),
        "stream_stage": final_stage,
        "clarification": clarification,
        "decision": {
            key: value
            for key, value in (decision or {}).items()
            if key not in {"context", "prompt_memory"}
        },
    }


def store_location_context(payload: dict[str, Any]) -> dict[str, Any]:
    session_id = str(payload.get("session_id", "")).strip()
    if not session_id:
        raise ValueError("Field 'session_id' is required.")

    conversation_id = _parse_optional_int(payload.get("conversation_id"))
    _restore_session_from_persisted_context(
        session_id=session_id,
        user_id=_get_authenticated_user_id(),
        conversation_id=conversation_id,
    )

    permission_state = payload.get("permission_state")
    browser_location = payload.get("browser_location")
    manual_area = str(payload.get("manual_area", "")).strip()
    skip_nearby_search = bool(payload.get("skip_nearby_search"))

    if skip_nearby_search:
        session = update_location_state(
            session_id,
            permission_state=permission_state or "denied",
            location_source="none",
            coordinates=None,
            manual_area=None,
            normalized_area=None,
            skip_nearby_search=True,
            ttl_seconds=current_app.config["AI_BROWSER_LOCATION_TTL_MINUTES"] * 60,
        )
        _sync_conversation_session_context(session.get("conversation_id"), session)
        return serialize_session(session)

    if browser_location is not None:
        try:
            lat = float(browser_location.get("lat"))
            lng = float(browser_location.get("lng"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(
                "Field 'browser_location' must include numeric 'lat' and 'lng' values."
            ) from exc
        session = update_location_state(
            session_id,
            permission_state=permission_state or "granted",
            location_source="browser",
            coordinates={"lat": lat, "lng": lng},
            manual_area=None,
            normalized_area=None,
            skip_nearby_search=False,
            ttl_seconds=current_app.config["AI_BROWSER_LOCATION_TTL_MINUTES"] * 60,
        )
        _sync_conversation_session_context(session.get("conversation_id"), session)
        return serialize_session(session)

    if manual_area:
        provider = OSMPublicMapProvider()
        try:
            area_result = provider.geocode_area(manual_area)
        except MapProviderError as exc:
            raise ValueError(str(exc)) from exc
        session = update_location_state(
            session_id,
            permission_state=permission_state or "granted",
            location_source="manual",
            coordinates={"lat": area_result["lat"], "lng": area_result["lng"]},
            manual_area=manual_area,
            normalized_area=area_result["normalized_area"],
            skip_nearby_search=False,
            ttl_seconds=current_app.config["AI_MANUAL_LOCATION_TTL_HOURS"] * 3600,
        )
        _sync_conversation_session_context(session.get("conversation_id"), session)
        return serialize_session(session)

    if permission_state == "denied":
        session = update_location_state(
            session_id,
            permission_state="denied",
            location_source="none",
            coordinates=None,
            manual_area=None,
            normalized_area=None,
            skip_nearby_search=False,
            ttl_seconds=current_app.config["AI_BROWSER_LOCATION_TTL_MINUTES"] * 60,
        )
        _sync_conversation_session_context(session.get("conversation_id"), session)
        return serialize_session(session)

    raise ValueError(
        "Provide one of browser_location, manual_area, skip_nearby_search, or permission_state=denied."
    )


def stream_recycling_resume(session_id: str) -> Generator[dict[str, Any], None, None]:
    from app.services.ai.demo_seed_replay_service import get_seed_demo_resume_stream

    demo_replay_stream = get_seed_demo_resume_stream(session_id)
    if demo_replay_stream is not None:
        yield from demo_replay_stream
        return

    user_id = _get_authenticated_user_id()
    paused_context = get_paused_context(session_id)
    if not paused_context:
        restored_session = _restore_session_from_persisted_context(
            session_id=session_id,
            user_id=user_id,
        )
        paused_context = get_paused_context(session_id) if restored_session else None

    if not paused_context:
        raise ValueError("No paused AI recycling session was found for this session_id.")

    analysis_payload = paused_context["analysis_payload"]
    location_state = get_valid_location_state(session_id) or {}
    conversation_id = paused_context.get("conversation_id")

    yield {
        "type": "meta",
        "session_id": session_id,
        "conversation_id": conversation_id,
    }

    if _can_execute_nearby_search(location_state):
        runtime_context = build_runtime_reply_context(
            conversation_id=conversation_id,
            user_id=user_id,
            prompt_memory=get_prompt_memory_summary(user_id),
        )
        yield from _stream_nearby_stage(
            session_id=session_id,
            user_id=user_id,
            conversation_id=conversation_id,
            analysis_payload=analysis_payload,
            location_state=location_state,
            prompt_memory=get_prompt_memory_summary(user_id),
            runtime_context=runtime_context,
        )
        return

    cleared_session = clear_paused_context(session_id)
    yield {"type": "stage_start", "stage": "completed"}
    completion_chunks: list[str] = []
    yield from _stream_skip_summary(
        analysis_payload=analysis_payload,
        location_state=location_state,
        prompt_memory=get_prompt_memory_summary(user_id),
        runtime_context=build_runtime_reply_context(
            conversation_id=conversation_id,
            user_id=user_id,
            prompt_memory=get_prompt_memory_summary(user_id),
        ),
        collector=completion_chunks,
    )
    if user_id is not None and conversation_id is not None:
        completion_reply = (
            "".join(completion_chunks).strip() or "Nearby recycling search was skipped."
        )
        _persist_recycling_assistant_message(
            conversation_id=conversation_id,
            message_type="tool_result",
            content_text=completion_reply,
            stream_stage="completed",
            analysis_payload=analysis_payload,
            recycling_case_id=paused_context.get("recycling_case_id"),
            location_state=location_state,
        )
        conversation_repository.update_conversation_state(
            conversation_id,
            status="completed",
            current_pending_action="none",
            session_context_json=json.dumps(serialize_session(cleared_session), ensure_ascii=False),
        )
    yield {"type": "done", "stream_stage": "completed"}


def _analyze_stage1(
    *,
    message: str,
    image_data_url: str | None,
    prompt_memory: dict[str, Any] | None = None,
    forum_candidates: list[dict[str, Any]] | None = None,
    graph_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        response = complete_json(
            user_message=message or "Please analyze this waste item.",
            image_data_url=image_data_url,
            system_prompt=_stage1_analysis_system_prompt(
                forum_candidates=forum_candidates or [],
                graph_context=graph_context,
            ),
            prompt_memory=prompt_memory,
        )
    except Exception:
        response = {
            "waste_type": "Mixed recyclable waste",
            "confidence": 0.55,
            "estimated_weight_kg": 0.2,
            "recycle_suggestions": [
                "Check your local recycling guide before disposal.",
                "Clean the item and separate mixed materials if possible.",
                "Use a verified recycling point for better sorting accuracy.",
            ],
            "needs_nearby_search": True,
            "forum_references": [],
        }
    payload = _normalize_analysis_payload(response, original_prompt=message)
    payload["forum_references"] = resolve_explicit_forum_references(
        response.get("forum_references") if isinstance(response, dict) else [],
        forum_candidates or [],
    )
    payload["forum_references"] = _merge_graph_forum_references(
        payload["forum_references"],
        graph_context,
    )
    return payload


def _resolve_response_forum_references(
    reply: str,
    forum_candidates: list[dict[str, Any]] | None,
    graph_context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    references = extract_used_forum_references(reply, forum_candidates or [])
    return _merge_graph_forum_references(references, graph_context)


def _merge_graph_forum_references(
    references: list[dict[str, Any]],
    graph_context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    merged = list(references or [])
    seen_urls = {str(item.get("url") or "") for item in merged}
    if not isinstance(graph_context, dict) or not graph_context.get("relation_facts"):
        return merged
    for item in graph_context.get("forum_citations") or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        if not url or url in seen_urls:
            continue
        merged.append(
            {
                "reference_id": item.get("reference_id") or f"forum-post-{item.get('post_id')}",
                "post_id": item.get("post_id"),
                "title": title or url,
                "url": url,
            }
        )
        seen_urls.add(url)
    return merged


def _normalize_analysis_payload(
    raw: dict[str, Any],
    *,
    original_prompt: str = "",
) -> dict[str, Any]:
    waste_type = str(raw.get("waste_type") or "Mixed recyclable waste").strip()
    confidence = _clamp_float(raw.get("confidence", 0.65), minimum=0.0, maximum=1.0)
    estimated_weight_kg = max(float(raw.get("estimated_weight_kg", 0.25)), 0.01)

    inferred_waste_type = _infer_waste_type_from_prompt(original_prompt)
    if inferred_waste_type and (
        not waste_type or waste_type.lower() in {"unknown", "mixed recyclable waste"}
    ):
        waste_type = inferred_waste_type
        confidence = max(confidence, 0.72)
        estimated_weight_kg = max(estimated_weight_kg, 0.03)

    emission_factor = _resolve_emission_factor(waste_type)
    co2_saved_kg = round(estimated_weight_kg * emission_factor, 2)
    carbon_points = round(co2_saved_kg * 100, 2)

    recycle_suggestions = raw.get("recycle_suggestions") or [
        "Empty and rinse the item before recycling.",
        "Separate the bottle cap and label if your local recycling guide requires it.",
        "Use a verified recycling station for clean sorting.",
    ]
    recycle_suggestions = [str(item).strip() for item in recycle_suggestions if str(item).strip()][
        :4
    ]

    forum_references = raw.get("forum_references") or []
    normalized_references = []
    for item in forum_references[:3]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        if title and url:
            normalized_references.append(
                {
                    "post_id": item.get("post_id"),
                    "title": title,
                    "url": url,
                }
            )

    needs_nearby_search = bool(raw.get("needs_nearby_search", True))
    if _prompt_implies_nearby_search(original_prompt):
        needs_nearby_search = True

    return {
        "waste_type": waste_type,
        "confidence": confidence,
        "estimated_weight_kg": round(estimated_weight_kg, 3),
        "co2_saved_kg": co2_saved_kg,
        "carbon_points": carbon_points,
        "recycle_suggestions": recycle_suggestions,
        "forum_references": normalized_references,
        "requires_location_decision": needs_nearby_search,
    }


def _prompt_implies_nearby_search(prompt: str) -> bool:
    normalized = str(prompt or "").strip().lower()
    if not normalized:
        return False

    keywords = (
        "recycle",
        "recycling",
        "recyclable",
        "where can i recycle",
        "how do i recycle",
        "how can i recycle",
        "recycling point",
        "nearby recycling",
        "\u56de\u6536",
        "\u600e\u4e48\u56de\u6536",
        "\u5982\u4f55\u56de\u6536",
        "\u56de\u6536\u70b9",
        "\u9644\u8fd1\u56de\u6536",
    )
    return any(keyword in normalized for keyword in keywords)


def _infer_waste_type_from_prompt(prompt: str) -> str | None:
    normalized = str(prompt or "").strip().lower()
    if not normalized:
        return None

    keyword_map = (
        (
            ("plastic bottle", "pet bottle", "\u5851\u6599\u74f6", "\u996e\u6599\u74f6"),
            "Plastic bottle",
        ),
        (("glass bottle", "glass jar", "\u73bb\u7483\u74f6", "\u73bb\u7483\u7f50"), "Glass bottle"),
        (("paper", "cardboard", "\u7eb8", "\u7eb8\u677f"), "Paper waste"),
        (("battery", "\u7535\u6c60"), "Battery"),
        (
            ("electronics", "electronic waste", "e-waste", "\u7535\u5b50\u5783\u573e"),
            "Electronic waste",
        ),
        (("can", "metal can", "aluminum can", "tin can", "\u6613\u62c9\u7f50"), "Metal can"),
    )

    for keywords, label in keyword_map:
        if any(keyword in normalized for keyword in keywords):
            return label

    if "\u74f6" in normalized:
        return "Plastic bottle"

    return None


def _build_stage_payload(
    *,
    analysis: dict[str, Any],
    nearby_locations: list[dict[str, Any]],
    stream_stage: str,
    map_error: str | None = None,
    recycling_case_id: int | None = None,
) -> dict[str, Any]:
    payload = {
        **analysis,
        "nearby_locations": nearby_locations,
        "map_error": map_error,
        "location_options": LOCATION_OPTIONS if analysis["requires_location_decision"] else [],
        "stream_stage": stream_stage,
    }
    if recycling_case_id is not None:
        payload["recycling_case_id"] = recycling_case_id
    return payload


def _stream_stage1_markdown(
    *,
    analysis: dict[str, Any],
    original_prompt: str,
    prompt_memory: dict[str, Any] | None = None,
    runtime_context: dict[str, Any] | None = None,
    collector: list[str] | None = None,
) -> Generator[dict[str, Any], None, None]:
    prompt = (
        "Write a helpful Markdown answer for a recycling assistant.\n"
        "Summarize the waste identification, confidence, estimated weight, carbon reduction, "
        "points, and practical recycling suggestions. Do not mention nearby map results yet.\n"
        f"User prompt: {original_prompt or 'No extra prompt provided.'}\n"
        f"Structured analysis: {json.dumps(analysis, ensure_ascii=False)}\n"
        f"{_runtime_context_note(runtime_context)}"
    )

    for event in stream_text(
        user_message=prompt,
        system_prompt=(
            "You are CarbonSnap's recycling assistant. "
            "Return concise Markdown with headings and bullet points. "
            "Do not invent map locations. Keep the tone practical and supportive. "
            "Do not wrap the whole answer in triple backticks or markdown code fences."
        ),
        prompt_memory=prompt_memory,
    ):
        if event["type"] == "meta":
            continue
        if event["type"] == "delta":
            if collector is not None:
                collector.append(event["content"])
            yield {"type": "delta", "stage": "analysis", "content": event["content"]}


def _stream_nearby_stage(
    *,
    session_id: str,
    user_id: int | None,
    conversation_id: int | None,
    analysis_payload: dict[str, Any],
    location_state: dict[str, Any],
    prompt_memory: dict[str, Any] | None = None,
    runtime_context: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    yield {"type": "stage_start", "stage": "nearby_search"}
    recycling_case_id = create_or_get_session(session_id).get("recycling_case_id")

    coordinates = location_state.get("coordinates") or {}
    lat = float(coordinates["lat"])
    lng = float(coordinates["lng"])
    area_label = location_state.get("normalized_area") or location_state.get("manual_area")

    nearby_locations: list[dict[str, Any]] = []
    map_error = None
    try:
        provider = OSMPublicMapProvider()
        nearby_locations = provider.search_nearby_recycling_points(
            lat=lat, lng=lng, area_label=area_label
        )
    except (MapProviderError, Exception) as exc:
        map_error = str(exc)

    payload = _build_stage_payload(
        analysis=analysis_payload,
        nearby_locations=nearby_locations,
        stream_stage="completed",
        map_error=map_error,
        recycling_case_id=recycling_case_id,
    )
    yield {"type": "nearby_results", "data": payload}

    summary_chunks: list[str] = []
    yield from _stream_nearby_summary(
        analysis_payload=analysis_payload,
        nearby_locations=nearby_locations,
        location_state=location_state,
        map_error=map_error,
        prompt_memory=prompt_memory,
        runtime_context=runtime_context,
        collector=summary_chunks,
    )

    if user_id is not None and conversation_id is not None:
        summary = "".join(summary_chunks).strip() or "Nearby recycling search completed."
        _persist_recycling_assistant_message(
            conversation_id=conversation_id,
            message_type="tool_result",
            content_text=summary,
            stream_stage="nearby_search",
            analysis_payload=analysis_payload,
            recycling_case_id=(create_or_get_session(session_id).get("recycling_case_id")),
            nearby_locations=nearby_locations,
            location_state=location_state,
        )

    cleared_session = clear_paused_context(session_id)
    if user_id is not None and conversation_id is not None:
        conversation_repository.update_conversation_state(
            conversation_id,
            status="completed",
            current_pending_action="none",
            session_context_json=json.dumps(serialize_session(cleared_session), ensure_ascii=False),
        )

    yield {"type": "done", "stream_stage": "completed"}


def _stream_skip_summary(
    *,
    analysis_payload: dict[str, Any],
    location_state: dict[str, Any],
    prompt_memory: dict[str, Any] | None = None,
    runtime_context: dict[str, Any] | None = None,
    collector: list[str] | None = None,
) -> Generator[dict[str, Any], None, None]:
    permission_state = location_state.get("permission_state", "unknown")
    if permission_state == "denied":
        guidance = "Location permission was denied, so nearby recycling search was skipped."
    elif location_state.get("skip_nearby_search"):
        guidance = "Nearby recycling search was skipped at your request."
    else:
        guidance = "Nearby recycling search was not available for this session."

    prompt = (
        "Write a short Markdown follow-up that explains why nearby recycling search is not included "
        "and give one or two next-step suggestions.\n"
        f"Guidance note: {guidance}\n"
        f"Analysis payload: {json.dumps(analysis_payload, ensure_ascii=False)}\n"
        f"{_runtime_context_note(runtime_context)}"
    )

    for event in stream_text(
        user_message=prompt,
        system_prompt=(
            "You are CarbonSnap's recycling assistant. "
            "Write a brief follow-up in Markdown and keep the answer reassuring. "
            "Do not wrap the whole answer in triple backticks or markdown code fences."
        ),
        prompt_memory=prompt_memory,
    ):
        if event["type"] == "meta":
            continue
        if event["type"] == "delta":
            if collector is not None:
                collector.append(event["content"])
            yield {"type": "delta", "stage": "completed", "content": event["content"]}


def _stream_nearby_summary(
    *,
    analysis_payload: dict[str, Any],
    nearby_locations: list[dict[str, Any]],
    location_state: dict[str, Any],
    map_error: str | None,
    prompt_memory: dict[str, Any] | None = None,
    runtime_context: dict[str, Any] | None = None,
    collector: list[str] | None = None,
) -> Generator[dict[str, Any], None, None]:
    context = {
        "analysis_payload": analysis_payload,
        "location_state": _make_json_safe(location_state),
        "nearby_locations": nearby_locations,
        "map_error": map_error,
    }
    prompt = (
        "Write a short Markdown follow-up for the nearby recycling search stage. "
        "If locations exist, summarize the most useful options and what the user should do next. "
        "If no locations exist or the map request failed, explain the fallback clearly without sounding broken.\n"
        f"Context: {json.dumps(context, ensure_ascii=False)}\n"
        f"{_runtime_context_note(runtime_context)}"
    )

    for event in stream_text(
        user_message=prompt,
        system_prompt=(
            "You are CarbonSnap's recycling assistant. "
            "Do not fabricate locations. Use Markdown with a short heading and bullets when helpful. "
            "Do not wrap the whole answer in triple backticks or markdown code fences."
        ),
        prompt_memory=prompt_memory,
    ):
        if event["type"] == "meta":
            continue
        if event["type"] == "delta":
            if collector is not None:
                collector.append(event["content"])
            yield {"type": "delta", "stage": "nearby_search", "content": event["content"]}


def _can_execute_nearby_search(location_state: dict[str, Any] | None) -> bool:
    if not location_state:
        return False
    if location_state.get("skip_nearby_search"):
        return False
    if location_state.get("permission_state") == "denied":
        return False
    return bool(location_state.get("coordinates"))


def _resolve_emission_factor(waste_type: str) -> float:
    emission_factors = current_app.config["AI_EMISSION_FACTORS"]
    normalized = waste_type.strip().lower()
    for key, value in emission_factors.items():
        if key != "default" and key in normalized:
            return float(value)
    return float(emission_factors["default"])


def _clamp_float(value: Any, *, minimum: float, maximum: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = minimum
    return max(minimum, min(maximum, numeric))


def _make_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _stage1_analysis_system_prompt(
    *,
    forum_candidates: list[dict[str, Any]] | None = None,
    graph_context: dict[str, Any] | None = None,
) -> str:
    base_prompt = """
You are CarbonSnap's multimodal recycling analyst.
Inspect the user's image and optional text prompt, then return exactly one JSON object.
Do not wrap the JSON in markdown.

Required JSON fields:
- waste_type: short string
- confidence: number between 0 and 1
- estimated_weight_kg: positive number
- recycle_suggestions: array of 2 to 4 short strings
- needs_nearby_search: boolean
- forum_references: array of objects with title and url when available, otherwise []

Rules:
- If the item appears recyclable, set needs_nearby_search to true.
- Keep forum_references empty unless you truly have explicit references in context.
- Never include commentary outside the JSON object.
""".strip()

    forum_block = build_forum_prompt_block(forum_candidates or [])
    graph_block = build_graph_prompt_block(graph_context)
    if not forum_block and not graph_block:
        return base_prompt

    additions = [base_prompt]
    if forum_block:
        additions.append(
            "If any forum source below materially influenced your recycling suggestions, include it in "
            "`forum_references` using the exact title and url."
        )
        additions.append(forum_block)
    if graph_block:
        additions.append(graph_block)
    return "\n\n".join(additions)
