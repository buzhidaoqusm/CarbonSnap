from __future__ import annotations

import json
from collections.abc import Generator
from datetime import datetime
from typing import Any

from flask import current_app
from sqlalchemy import func, select

from app.extensions.db import db
from app.models.ai import AIConversation, AIMessage, RecyclingCase
from app.repositories.ai import conversation_repository, recycling_case_repository
from app.services.ai.agent_trace_service import (
    attach_forum_citations_to_trace,
    attach_graph_context_to_trace,
    build_trace_shell,
    normalize_trace_for_storage,
)
from app.services.ai.ai_decision_engine import persist_message_decision
from app.services.ai.conversation_context_builder import build_runtime_reply_context
from app.services.ai.forum_retrieval_service import (
    build_forum_prompt_block,
    extract_used_forum_references,
    retrieve_forum_references,
)
from app.services.ai.image_storage_service import store_data_url_image
from app.services.ai.memory_service import get_prompt_memory_summary, upsert_memory_item
from app.services.ai.neo4j_graph_retrieval_service import (
    build_graph_prompt_block,
    query_graph_context,
)
from app.services.ai.openrouter_service import (
    build_messages,
    chat_with_openrouter,
    generate_conversation_title,
    history_from_message_records,
    stream_chat_with_openrouter,
)
from app.services.ai.prompt_registry import get_prompt_version

_SHORT_TERM_MEMORY_INSTRUCTION = (
    "You are continuing the user's current chat session. Use only the recent context from this "
    "same conversation. If the user asks what they said earlier, what you said earlier, or what "
    "you previously recommended, answer from this current chat only. If the answer is not present "
    "in this chat context, say that you cannot find it in the current conversation and do not "
    "invent prior context."
)


def _parse_json_value(value: str | None) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return value


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def serialize_conversation(conversation: AIConversation) -> dict[str, Any]:
    return {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "title": conversation.title,
        "status": conversation.status,
        "current_pending_action": conversation.current_pending_action,
        "session_context_json": _parse_json_value(conversation.session_context_json),
        "last_message_at": _serialize_datetime(conversation.last_message_at),
        "created_at": _serialize_datetime(conversation.created_at),
        "updated_at": _serialize_datetime(conversation.updated_at),
    }


def serialize_message(message: AIMessage) -> dict[str, Any]:
    parsed_content = _parse_json_value(message.content_json)
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "message_type": message.message_type,
        "content_text": message.content_text,
        "content_json": parsed_content,
        "image_url": parsed_content.get("image_url") if isinstance(parsed_content, dict) else None,
        "trace": parsed_content.get("trace") if isinstance(parsed_content, dict) else None,
        "related_analysis_id": message.related_analysis_id,
        "sequence_no": message.sequence_no,
        "created_at": _serialize_datetime(message.created_at),
    }


def _serialize_audit_attempt(attempt) -> dict[str, Any]:
    return {
        "id": attempt.id,
        "recycling_case_id": attempt.recycling_case_id,
        "attempt_no": attempt.attempt_no,
        "audit_result": attempt.audit_result,
        "auditor_confidence": attempt.auditor_confidence,
        "audit_reason": attempt.audit_reason,
        "audit_image_url": attempt.audit_image_url,
        "audit_response_json": _parse_json_value(attempt.audit_response_json),
        "created_at": _serialize_datetime(attempt.created_at),
    }


def _serialize_recycling_case(
    case: RecyclingCase | None,
    *,
    audit_attempts: list[Any] | None = None,
) -> dict[str, Any] | None:
    if case is None:
        return None

    return {
        "id": case.id,
        "conversation_id": case.conversation_id,
        "origin_message_id": case.origin_message_id,
        "waste_type_predicted": case.waste_type_predicted,
        "confidence": case.confidence,
        "estimated_weight_kg": case.estimated_weight_kg,
        "expected_co2_saved_kg": case.expected_co2_saved_kg,
        "expected_carbon_points": case.expected_carbon_points,
        "status": case.status,
        "latest_audit_attempt_no": case.latest_audit_attempt_no,
        "approved_analysis_id": case.approved_analysis_id,
        "audit_attempts": [_serialize_audit_attempt(attempt) for attempt in (audit_attempts or [])],
    }


def _count_user_conversations(user_id: int) -> int:
    return (
        db.session.scalar(
            select(func.count(AIConversation.id)).where(AIConversation.user_id == user_id)
        )
        or 0
    )


def _resolve_conversation_for_user(
    *,
    user_id: int,
    conversation_id: int | None,
    title: str | None = None,
) -> AIConversation:
    if conversation_id is None:
        return conversation_repository.create_conversation(user_id=user_id, title=title)

    conversation = conversation_repository.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found.")
    return conversation


def _resolve_history_for_request(
    *,
    conversation: AIConversation | None,
    supplied_history: list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], list[Any] | None]:
    max_turns = int(current_app.config.get("AI_SHORT_TERM_MEMORY_TURNS", 10) or 10)

    if conversation is None:
        return _trim_history_to_recent_turns(supplied_history or [], max_turns=max_turns), None

    persisted_messages = conversation_repository.list_messages(conversation.id)
    if persisted_messages:
        return _trim_history_to_recent_turns(
            history_from_message_records(persisted_messages),
            max_turns=max_turns,
        ), persisted_messages

    return _trim_history_to_recent_turns(supplied_history or [], max_turns=max_turns), None


def _trim_history_to_recent_turns(
    history: list[dict[str, Any]] | None,
    *,
    max_turns: int,
) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    for item in history or []:
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            cleaned.append({"role": role, "content": content})

    if max_turns <= 0:
        return cleaned

    return cleaned[-(max_turns * 2) :]


def _clip_text(text: str, limit: int = 220) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


def _build_structured_short_term_notes(messages: list[Any] | None) -> list[str]:
    if not messages:
        return []

    latest_by_type: dict[str, str] = {}
    labels = {
        "analysis_result": "Recent recycling analysis",
        "tool_result": "Recent nearby recycling guidance",
        "audit_result": "Recent completion audit result",
    }

    for message in messages:
        message_type = str(getattr(message, "message_type", "") or "").strip().lower()
        if message_type not in labels:
            continue

        content = str(getattr(message, "content_text", "") or "").strip()
        if content:
            latest_by_type[message_type] = _clip_text(content)

    notes: list[str] = []
    for message_type in ("analysis_result", "tool_result", "audit_result"):
        content = latest_by_type.get(message_type)
        if content:
            notes.append(f"{labels[message_type]}: {content}")
    return notes


def _build_case_context_notes(runtime_context: dict[str, Any] | None) -> list[str]:
    if not runtime_context:
        return []

    notes: list[str] = []
    case_summaries = runtime_context.get("case_summaries") or []
    if case_summaries:
        notes.append("Active recycling cases in this same chat:")
        for case in case_summaries[:4]:
            notes.append(
                "- "
                f"Case {case.get('case_id')}: "
                f"{case.get('predicted_item') or 'Unknown item'} | "
                f"stage={case.get('current_stage') or case.get('status') or 'unknown'}"
            )

    working_memory = runtime_context.get("working_memory") or {}
    if working_memory.get("latest_analysis"):
        notes.append(f"Latest recycling analysis: {working_memory['latest_analysis']}")
    if working_memory.get("latest_nearby_guidance"):
        notes.append(f"Latest nearby guidance: {working_memory['latest_nearby_guidance']}")
    if working_memory.get("latest_verification_feedback"):
        notes.append(
            f"Latest verification feedback: {working_memory['latest_verification_feedback']}"
        )
    location_state = runtime_context.get("location_state") or {}
    if location_state.get("normalized_area"):
        notes.append(f"Current location context: {location_state['normalized_area']}")
    elif location_state.get("permission_state") == "denied":
        notes.append("Current location context: browser location is denied for this chat.")
    return notes


def _build_short_term_system_prompt(
    *,
    history: list[dict[str, Any]],
    persisted_messages: list[Any] | None,
    runtime_context: dict[str, Any] | None = None,
    forum_candidates: list[dict[str, Any]] | None = None,
    graph_context: dict[str, Any] | None = None,
) -> str:
    max_turns = int(current_app.config.get("AI_SHORT_TERM_MEMORY_TURNS", 10) or 10)
    lines = [
        _SHORT_TERM_MEMORY_INSTRUCTION,
        f"Active short-term memory window: recent {max_turns} turns from this chat only.",
    ]

    latest_user = next(
        (item["content"] for item in reversed(history) if item.get("role") == "user"),
        "",
    )
    latest_assistant = next(
        (item["content"] for item in reversed(history) if item.get("role") == "assistant"),
        "",
    )
    if latest_user:
        lines.append(f'Latest user message before this request: "{_clip_text(latest_user, 180)}"')
    if latest_assistant:
        lines.append(
            f'Latest assistant reply before this request: "{_clip_text(latest_assistant, 180)}"'
        )

    structured_notes = _build_structured_short_term_notes(persisted_messages)
    if structured_notes:
        lines.append("Key structured context from this same chat:")
        lines.extend(f"- {note}" for note in structured_notes)

    case_notes = _build_case_context_notes(runtime_context)
    if case_notes:
        lines.append("Conversation working memory:")
        lines.extend(case_notes)

    forum_block = build_forum_prompt_block(forum_candidates or [])
    if forum_block:
        lines.append(forum_block)

    graph_block = build_graph_prompt_block(graph_context)
    if graph_block:
        lines.append(graph_block)
    elif not forum_candidates:
        lines.append(
            "External evidence note: no Neo4j graph evidence or forum citations are available for this turn. "
            "Avoid overclaiming and suggest checking local recycling guidance when rules may vary."
        )

    return "\n".join(lines)


def _persist_user_message(
    *,
    conversation_id: int,
    message: str,
    image_data_url: str | None,
) -> AIMessage:
    content_payload: dict[str, Any] = {
        "has_image": bool(image_data_url),
    }
    if image_data_url:
        content_payload["image_url"] = store_data_url_image(image_data_url, namespace="chat")

    return conversation_repository.append_message(
        conversation_id=conversation_id,
        role="user",
        message_type="image" if image_data_url else "text",
        content_text=message,
        content_json=json.dumps(content_payload, ensure_ascii=False),
    )


def _persist_assistant_message(
    *,
    conversation_id: int,
    reply: str,
    model: str | None,
    forum_references: list[dict[str, Any]] | None = None,
    memory_updates: list[dict[str, Any]] | None = None,
    trace: dict[str, Any] | None = None,
) -> AIMessage:
    payload: dict[str, Any] = {}
    if model:
        payload["model"] = model
    if forum_references:
        payload["forum_references"] = forum_references
    if memory_updates:
        payload["memory_updates"] = memory_updates
    normalized_trace = normalize_trace_for_storage(
        trace,
        conversation_id=conversation_id,
    )
    if normalized_trace:
        payload["trace"] = normalized_trace

    content_json = json.dumps(payload, ensure_ascii=False) if payload else None

    return conversation_repository.append_message(
        conversation_id=conversation_id,
        role="assistant",
        message_type="text",
        content_text=reply,
        content_json=content_json,
    )


def _persist_clarification_assistant_message(
    *,
    conversation_id: int,
    clarification_question: str,
    clarification_options: list[dict[str, Any]] | None,
    trace: dict[str, Any] | None = None,
) -> AIMessage:
    payload = {
        "stream_stage": "clarification",
        "clarification_options": clarification_options or [],
    }
    normalized_trace = normalize_trace_for_storage(
        trace,
        conversation_id=conversation_id,
    )
    if normalized_trace:
        payload["trace"] = normalized_trace
    return conversation_repository.append_message(
        conversation_id=conversation_id,
        role="assistant",
        message_type="tool_result",
        content_text=clarification_question,
        content_json=json.dumps(payload, ensure_ascii=False),
    )


def _persist_explicit_memory_candidates(
    *,
    user_id: int,
    conversation_id: int,
    source_message_id: int,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    persisted_updates: list[dict[str, Any]] = []

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
            persisted_updates.append(
                {
                    "id": item.id,
                    "memory_type": item.memory_type,
                    "memory_key": item.memory_key,
                }
            )
        except Exception:
            continue

    return persisted_updates


def _attach_prompt_version(
    trace: dict[str, Any] | None,
    *,
    prompt_name: str,
) -> dict[str, Any] | None:
    if not trace:
        return None
    trace_with_prompt = dict(trace)
    prompt_versions = dict(trace_with_prompt.get("prompt_versions") or {})
    prompt_versions[prompt_name] = get_prompt_version(prompt_name)
    trace_with_prompt["prompt_versions"] = prompt_versions
    return trace_with_prompt


def _build_response_trace(
    *,
    decision: dict[str, Any] | None,
    conversation_id: int,
    forum_references: list[dict[str, Any]] | None,
    graph_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    trace = _attach_prompt_version(
        decision.get("trace") if isinstance(decision, dict) else None,
        prompt_name="general_chat_answer",
    )
    trace = attach_forum_citations_to_trace(trace, forum_references)
    trace = attach_graph_context_to_trace(trace, graph_context)
    return normalize_trace_for_storage(trace, conversation_id=conversation_id)


def _build_initial_chat_title(
    *,
    message: str,
    image_data_url: str | None,
) -> str:
    fallback_title = "Image discussion" if image_data_url and not message.strip() else "New chat"
    return generate_conversation_title(
        user_message=message,
        image_data_url=image_data_url,
        fallback_title=fallback_title,
    )


def _persist_clarification_request(
    *,
    user_id: int | None,
    message: str,
    image_data_url: str | None,
    conversation_id: int | None,
    decision: dict[str, Any],
) -> dict[str, Any]:
    if user_id is None:
        return {
            "conversation": None,
            "user_message": None,
        }

    resolved_title = None
    if conversation_id is None:
        resolved_title = _build_initial_chat_title(message=message, image_data_url=image_data_url)

    conversation = _resolve_conversation_for_user(
        user_id=user_id,
        conversation_id=conversation_id,
        title=resolved_title,
    )
    user_message = _persist_user_message(
        conversation_id=conversation.id,
        message=message,
        image_data_url=image_data_url,
    )
    persist_message_decision(
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        decision=decision,
    )
    return {
        "conversation": conversation,
        "user_message": user_message,
        "assistant_message": _persist_clarification_assistant_message(
            conversation_id=conversation.id,
            clarification_question=decision.get("clarification_question")
            or "Could you clarify which recycling task you mean?",
            clarification_options=decision.get("clarification_options", []),
            trace=decision.get("trace"),
        ),
    }


def _apply_memory_candidates_to_prompt_memory(
    prompt_memory: dict[str, Any] | None,
    candidates: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    merged = dict(prompt_memory or {})
    if not candidates:
        return merged

    action_preferences = dict(merged.get("action_preferences") or {})
    content_interest = dict(merged.get("content_interest_preferences") or {})
    topics = list(content_interest.get("topics") or [])

    for candidate in candidates:
        memory_type = candidate.get("memory_type")
        memory_key = candidate.get("memory_key")
        value = candidate.get("value") or {}

        if memory_type == "response_style":
            action_preferences["response_style"] = value.get("value")
        elif memory_type == "recycling_preference" and "value" in value:
            action_preferences[memory_key] = value["value"]
        elif memory_type == "topic_interest":
            topic = value.get("topic") or memory_key
            topic_id = f"{str(topic).strip().lower().replace(' ', '-')}"
            if not topic_id.endswith("-recycling"):
                topic_id = f"{topic_id}-recycling"
            topics = [item for item in topics if item.get("topic_id") != topic_id]
            topics.append({"topic_id": topic_id, "score": 1.0, "source": "explicit_memory"})
        elif memory_type == "item_method_preference":
            item_type = value.get("item_type") or memory_key
            methods = list(action_preferences.get("preferred_recycling_methods") or [])
            methods = [item for item in methods if item.get("item_type") != item_type]
            methods.append(
                {
                    "item_type": item_type,
                    "preferred_method": value.get("preferred_method"),
                }
            )
            action_preferences["preferred_recycling_methods"] = methods

    content_interest["topics"] = topics
    merged["content_interest_preferences"] = content_interest
    merged["action_preferences"] = action_preferences
    return merged


def _build_forum_query(message: str, decision: dict[str, Any] | None) -> str:
    parts = [str(message or "").strip()]
    if not isinstance(decision, dict):
        return "\n".join(part for part in parts if part)

    context = decision.get("context") or {}
    target_case_id = decision.get("target_case_id")
    for case in context.get("case_summaries") or []:
        if target_case_id is not None and case.get("case_id") != target_case_id:
            continue
        predicted_item = case.get("predicted_item")
        current_stage = case.get("current_stage") or case.get("status")
        if predicted_item:
            parts.append(f"Related recycling item: {predicted_item}")
        if current_stage:
            parts.append(f"Case stage: {current_stage}")
        break

    working_memory = context.get("working_memory") or {}
    for key in ("latest_analysis", "latest_nearby_guidance", "latest_verification_feedback"):
        value = str(working_memory.get(key) or "").strip()
        if value:
            parts.append(value)
    return "\n".join(part for part in parts if part)


def _retrieve_forum_candidates(
    message: str, decision: dict[str, Any] | None
) -> list[dict[str, Any]]:
    if not isinstance(decision, dict) or not decision.get("should_retrieve_forum"):
        return []

    result = retrieve_forum_references(query=_build_forum_query(message, decision))
    return result.get("candidates") or []


def _retrieve_graph_context(message: str, decision: dict[str, Any] | None) -> dict[str, Any]:
    query = _build_forum_query(message, decision)
    return query_graph_context(query or message)


def _resolve_response_forum_references(
    reply: str,
    forum_candidates: list[dict[str, Any]],
    graph_context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    references = extract_used_forum_references(reply, forum_candidates)
    seen_urls = {str(item.get("url") or "") for item in references}

    graph_citations = []
    if isinstance(graph_context, dict) and graph_context.get("relation_facts"):
        graph_citations = list(graph_context.get("forum_citations") or [])

    for item in graph_citations:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        if not url or url in seen_urls:
            continue
        references.append(
            {
                "reference_id": item.get("reference_id") or f"forum-post-{item.get('post_id')}",
                "post_id": item.get("post_id"),
                "title": title or url,
                "url": url,
            }
        )
        seen_urls.add(url)
    return references


def complete_chat_message(
    *,
    user_id: int | None,
    message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    conversation_id: int | None = None,
    title: str | None = None,
    prompt_memory: dict[str, Any] | None = None,
    memory_candidates: list[dict[str, Any]] | None = None,
    decision: dict[str, Any] | None = None,
    client_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    forum_candidates = _retrieve_forum_candidates(message, decision)
    graph_context = _retrieve_graph_context(message, decision)

    if user_id is None:
        request_history = _trim_history_to_recent_turns(
            history or [],
            max_turns=int(current_app.config.get("AI_SHORT_TERM_MEMORY_TURNS", 10) or 10),
        )
        short_term_system_prompt = _build_short_term_system_prompt(
            history=request_history,
            persisted_messages=None,
            forum_candidates=forum_candidates,
            graph_context=graph_context,
        )
        if image_data_url:
            store_data_url_image(image_data_url, namespace="chat")
        result = chat_with_openrouter(
            user_message=message,
            history=request_history,
            image_data_url=image_data_url,
            system_prompt=short_term_system_prompt,
            prompt_memory=prompt_memory or {},
        )
        result["forum_references"] = _resolve_response_forum_references(
            result.get("reply", ""),
            forum_candidates,
            graph_context,
        )
        return result

    resolved_title = title
    if conversation_id is None and resolved_title is None:
        resolved_title = _build_initial_chat_title(message=message, image_data_url=image_data_url)

    conversation = _resolve_conversation_for_user(
        user_id=user_id,
        conversation_id=conversation_id,
        title=resolved_title,
    )
    request_history, persisted_messages = _resolve_history_for_request(
        conversation=conversation,
        supplied_history=history,
    )
    runtime_context = build_runtime_reply_context(
        conversation_id=conversation.id,
        user_id=user_id,
        supplied_history=history,
        max_turns=int(current_app.config.get("AI_SHORT_TERM_MEMORY_TURNS", 10) or 10),
        prompt_memory=prompt_memory,
        client_context=client_context,
    )
    short_term_system_prompt = _build_short_term_system_prompt(
        history=request_history,
        persisted_messages=persisted_messages,
        runtime_context=runtime_context,
        forum_candidates=forum_candidates,
        graph_context=graph_context,
    )

    user_message = _persist_user_message(
        conversation_id=conversation.id,
        message=message,
        image_data_url=image_data_url,
    )
    memory_updates = _persist_explicit_memory_candidates(
        user_id=user_id,
        conversation_id=conversation.id,
        source_message_id=user_message.id,
        candidates=memory_candidates or [],
    )
    if decision is not None:
        persist_message_decision(
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            decision=decision,
        )
    effective_prompt_memory = (
        get_prompt_memory_summary(user_id)
        if memory_updates
        else (prompt_memory if prompt_memory is not None else get_prompt_memory_summary(user_id))
    )
    effective_prompt_memory = _apply_memory_candidates_to_prompt_memory(
        effective_prompt_memory,
        memory_candidates,
    )
    result = chat_with_openrouter(
        user_message=message,
        history=request_history,
        image_data_url=image_data_url,
        system_prompt=short_term_system_prompt,
        prompt_memory=effective_prompt_memory,
    )
    forum_references = _resolve_response_forum_references(
        result.get("reply", ""),
        forum_candidates,
        graph_context,
    )
    response_trace = _build_response_trace(
        decision=decision,
        conversation_id=conversation.id,
        forum_references=forum_references,
        graph_context=graph_context,
    )
    assistant_message = _persist_assistant_message(
        conversation_id=conversation.id,
        reply=result["reply"],
        model=result.get("model"),
        forum_references=forum_references,
        memory_updates=memory_updates,
        trace=response_trace,
    )

    return {
        **result,
        "forum_references": forum_references,
        "trace": response_trace,
        "graph_context": graph_context,
        "conversation_id": conversation.id,
        "conversation_title": conversation.title,
        "user_message_id": user_message.id,
        "assistant_message_id": assistant_message.id,
        "memory_updates": memory_updates,
    }


def _tool_calling_agent_system_prompt() -> str:
    return (
        "You are CarbonSnap's recycling assistant. You can call tools to ground your answers:\n"
        "- search_forum: retrieve community forum posts for real user experiences and tips.\n"
        "- query_recycling_graph: look up recycling rules, risks, and material relationships.\n"
        "- estimate_carbon_saving: estimate CO2 savings and points for an item.\n"
        "- find_nearby_recycling_places: find nearby recycling points (needs the user's location).\n"
        "- read_user_memory / recommend_project: personalize the reply.\n"
        "Call a tool only when it genuinely helps answer the user, and prefer grounding factual "
        "recycling claims in tool results rather than guessing.\n"
        "When you use a forum post, cite it inline with its exact [Title](URL) and end with a short "
        "'Sources' section listing only the links you actually used. Never invent titles or URLs.\n"
        "Answer in the user's language. Keep replies concise and practical."
    )


def _build_agent_loop_trace(
    *,
    decision: dict[str, Any] | None,
    conversation_id: int | None,
    user_id: int | None,
    loop_result: dict[str, Any],
) -> dict[str, Any] | None:
    trace = decision.get("trace") if isinstance(decision, dict) else None
    if not trace:
        trace = build_trace_shell(
            user_id=user_id,
            conversation_id=conversation_id,
            intent=(decision or {}).get("intent"),
        )

    tool_trace = loop_result.get("tool_trace") or []
    trace = json.loads(json.dumps(trace, ensure_ascii=False, default=str))
    existing_tool_calls = list(trace.get("tool_calls") or [])
    trace["tool_calls"] = [*existing_tool_calls, *tool_trace]
    trace["agent_loop"] = {
        "enabled": True,
        "framework": "langgraph",
        "engine": "tool_calling_agent",
        "stopped_reason": loop_result.get("stopped_reason"),
        "iterations": loop_result.get("iterations"),
        "nodes": loop_result.get("nodes", []),
        "tool_call_count": len(tool_trace),
        "usage": loop_result.get("usage_total", {}),
    }
    if loop_result.get("model"):
        model_block = dict(trace.get("model") or {})
        model_block["name"] = loop_result.get("model")
        trace["model"] = model_block
    return normalize_trace_for_storage(trace, conversation_id=conversation_id)


def complete_tool_calling_agent_message(
    *,
    user_id: int | None,
    message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    conversation_id: int | None = None,
    title: str | None = None,
    prompt_memory: dict[str, Any] | None = None,
    memory_candidates: list[dict[str, Any]] | None = None,
    decision: dict[str, Any] | None = None,
    client_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Model-driven general-chat reply.

    Mirrors ``complete_chat_message``'s persistence, but the reply is produced by
    the tool-calling agent loop: the model chooses and invokes tools (forum RAG,
    graph, carbon estimate, nearby search) instead of retrieval being pre-injected
    by rules. Gated behind ``AI_TOOL_CALLING_AGENT_ENABLED``.
    """
    from app.services.ai.tool_calling_agent import run_tool_calling_agent

    system_prompt = _tool_calling_agent_system_prompt()
    agent_context = {"user_id": user_id, "client_context": client_context}

    if user_id is None:
        request_history = _trim_history_to_recent_turns(
            history or [],
            max_turns=int(current_app.config.get("AI_SHORT_TERM_MEMORY_TURNS", 10) or 10),
        )
        if image_data_url:
            store_data_url_image(image_data_url, namespace="chat")
        messages = build_messages(
            user_message=message,
            history=request_history,
            image_data_url=image_data_url,
            system_prompt=system_prompt,
            prompt_memory=prompt_memory or {},
        )
        loop_result = run_tool_calling_agent(messages=messages, context=agent_context)
        return {
            "reply": loop_result.get("content", ""),
            "model": loop_result.get("model"),
            "usage": loop_result.get("usage_total", {}),
            "tool_trace": loop_result.get("tool_trace", []),
            "agent_loop": {
                "stopped_reason": loop_result.get("stopped_reason"),
                "iterations": loop_result.get("iterations"),
                "nodes": loop_result.get("nodes", []),
            },
        }

    resolved_title = title
    if conversation_id is None and resolved_title is None:
        resolved_title = _build_initial_chat_title(message=message, image_data_url=image_data_url)

    conversation = _resolve_conversation_for_user(
        user_id=user_id,
        conversation_id=conversation_id,
        title=resolved_title,
    )
    request_history, _persisted_messages = _resolve_history_for_request(
        conversation=conversation,
        supplied_history=history,
    )

    user_message = _persist_user_message(
        conversation_id=conversation.id,
        message=message,
        image_data_url=image_data_url,
    )
    memory_updates = _persist_explicit_memory_candidates(
        user_id=user_id,
        conversation_id=conversation.id,
        source_message_id=user_message.id,
        candidates=memory_candidates or [],
    )
    if decision is not None:
        persist_message_decision(
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            decision=decision,
        )
    effective_prompt_memory = (
        get_prompt_memory_summary(user_id)
        if memory_updates
        else (prompt_memory if prompt_memory is not None else get_prompt_memory_summary(user_id))
    )
    effective_prompt_memory = _apply_memory_candidates_to_prompt_memory(
        effective_prompt_memory,
        memory_candidates,
    )

    messages = build_messages(
        user_message=message,
        history=request_history,
        image_data_url=image_data_url,
        system_prompt=system_prompt,
        prompt_memory=effective_prompt_memory,
    )
    loop_result = run_tool_calling_agent(messages=messages, context=agent_context)

    response_trace = _build_agent_loop_trace(
        decision=decision,
        conversation_id=conversation.id,
        user_id=user_id,
        loop_result=loop_result,
    )
    assistant_message = _persist_assistant_message(
        conversation_id=conversation.id,
        reply=loop_result.get("content", ""),
        model=loop_result.get("model"),
        memory_updates=memory_updates,
        trace=response_trace,
    )

    return {
        "reply": loop_result.get("content", ""),
        "model": loop_result.get("model"),
        "usage": loop_result.get("usage_total", {}),
        "tool_trace": loop_result.get("tool_trace", []),
        "trace": response_trace,
        "conversation_id": conversation.id,
        "conversation_title": conversation.title,
        "user_message_id": user_message.id,
        "assistant_message_id": assistant_message.id,
        "memory_updates": memory_updates,
        "agent_loop": {
            "stopped_reason": loop_result.get("stopped_reason"),
            "iterations": loop_result.get("iterations"),
            "nodes": loop_result.get("nodes", []),
        },
    }


def _build_shadow_selection_messages(
    *,
    message: str,
    history: list[dict[str, Any]] | None,
    image_data_url: str | None,
    prompt_memory: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Reconstruct the prompt the tool-calling model would see, for a
    selection-only shadow call (no tools are executed)."""
    request_history = _trim_history_to_recent_turns(
        history or [],
        max_turns=int(current_app.config.get("AI_SHORT_TERM_MEMORY_TURNS", 10) or 10),
    )
    return build_messages(
        user_message=message,
        history=request_history,
        image_data_url=image_data_url,
        system_prompt=_tool_calling_agent_system_prompt(),
        prompt_memory=prompt_memory or {},
    )


def _attach_and_log_tool_selection_shadow(
    *,
    result: dict[str, Any],
    mode: str,
    decision: dict[str, Any] | None,
    comparison: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> None:
    from app.services.ai.tool_selection_shadow import (
        build_shadow_record,
        record_shadow_comparison,
    )

    record = build_shadow_record(
        mode=mode,
        decision=decision,
        comparison=comparison,
        extra={"conversation_id": result.get("conversation_id"), **(extra or {})},
    )
    record_shadow_comparison(record)

    shadow_block = {
        "mode": mode,
        "served_by": record["served_by"],
        **comparison,
    }
    trace = result.get("trace")
    if isinstance(trace, dict):
        trace["tool_selection_shadow"] = shadow_block
    result["tool_selection_shadow"] = shadow_block


def complete_general_chat_with_mode(
    *,
    user_id: int | None,
    message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    conversation_id: int | None = None,
    title: str | None = None,
    prompt_memory: dict[str, Any] | None = None,
    memory_candidates: list[dict[str, Any]] | None = None,
    decision: dict[str, Any] | None = None,
    client_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """General-chat entrypoint that honours the tool-selection rollout mode.

    * ``model``  — serve the model-driven tool-calling loop (A6). Compares the
      tools the model actually invoked against the rule engine's selection for
      free (no extra LLM call).
    * ``shadow`` — serve the rule-based reply, but run one non-executing model
      call to capture what the model *would* have selected, and log the
      divergence (A7 pre-flip evidence gathering).
    * ``rule``   — serve the rule-based reply unchanged (default).
    """
    from app.services.ai.tool_selection_shadow import (
        compare_tool_selections,
        model_tool_selection,
        resolve_tool_selection_mode,
        rule_tool_selection,
    )

    mode = resolve_tool_selection_mode()

    if mode == "model":
        result = complete_tool_calling_agent_message(
            user_id=user_id,
            message=message,
            history=history,
            image_data_url=image_data_url,
            conversation_id=conversation_id,
            title=title,
            prompt_memory=prompt_memory,
            memory_candidates=memory_candidates,
            decision=decision,
            client_context=client_context,
        )
        try:
            rule_tools = rule_tool_selection(decision, client_context=client_context)
            model_tools = [entry.get("name") for entry in (result.get("tool_trace") or [])]
            comparison = compare_tool_selections(rule_tools, model_tools)
            _attach_and_log_tool_selection_shadow(
                result=result, mode=mode, decision=decision, comparison=comparison
            )
        except Exception:  # pragma: no cover - comparison must never break serving
            pass
        return result

    result = complete_chat_message(
        user_id=user_id,
        message=message,
        history=history,
        image_data_url=image_data_url,
        conversation_id=conversation_id,
        title=title,
        prompt_memory=prompt_memory,
        memory_candidates=memory_candidates,
        decision=decision,
        client_context=client_context,
    )

    if mode == "shadow":
        try:
            shadow_messages = _build_shadow_selection_messages(
                message=message,
                history=history,
                image_data_url=image_data_url,
                prompt_memory=prompt_memory,
            )
            model_selection = model_tool_selection(messages=shadow_messages)
            rule_tools = rule_tool_selection(decision, client_context=client_context)
            comparison = compare_tool_selections(rule_tools, model_selection["tools"])
            _attach_and_log_tool_selection_shadow(
                result=result,
                mode=mode,
                decision=decision,
                comparison=comparison,
                extra={
                    "shadow_model": model_selection.get("model"),
                    "shadow_usage": model_selection.get("usage", {}),
                },
            )
        except Exception:  # pragma: no cover - shadow must never break serving
            pass

    return result


def stream_chat_message(
    *,
    user_id: int | None,
    message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    conversation_id: int | None = None,
    title: str | None = None,
    prompt_memory: dict[str, Any] | None = None,
    memory_candidates: list[dict[str, Any]] | None = None,
    decision: dict[str, Any] | None = None,
    client_context: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    forum_candidates = _retrieve_forum_candidates(message, decision)
    graph_context = _retrieve_graph_context(message, decision)

    if user_id is None:
        request_history = _trim_history_to_recent_turns(
            history or [],
            max_turns=int(current_app.config.get("AI_SHORT_TERM_MEMORY_TURNS", 10) or 10),
        )
        short_term_system_prompt = _build_short_term_system_prompt(
            history=request_history,
            persisted_messages=None,
            forum_candidates=forum_candidates,
            graph_context=graph_context,
        )
        if image_data_url:
            store_data_url_image(image_data_url, namespace="chat")
        assistant_reply_parts: list[str] = []
        for event in stream_chat_with_openrouter(
            user_message=message,
            history=request_history,
            image_data_url=image_data_url,
            system_prompt=short_term_system_prompt,
            prompt_memory=prompt_memory or {},
        ):
            if event.get("type") == "delta":
                assistant_reply_parts.append(str(event.get("content", "")))
                yield event
                continue
            if event.get("type") == "done":
                yield {
                    **event,
                    "forum_references": _resolve_response_forum_references(
                        "".join(assistant_reply_parts),
                        forum_candidates,
                        graph_context,
                    ),
                    "graph_context": graph_context,
                }
                return
            yield event
        return

    resolved_title = title
    if conversation_id is None and resolved_title is None:
        resolved_title = _build_initial_chat_title(message=message, image_data_url=image_data_url)

    conversation = _resolve_conversation_for_user(
        user_id=user_id,
        conversation_id=conversation_id,
        title=resolved_title,
    )
    request_history, persisted_messages = _resolve_history_for_request(
        conversation=conversation,
        supplied_history=history,
    )
    runtime_context = build_runtime_reply_context(
        conversation_id=conversation.id,
        user_id=user_id,
        supplied_history=history,
        max_turns=int(current_app.config.get("AI_SHORT_TERM_MEMORY_TURNS", 10) or 10),
        prompt_memory=prompt_memory,
        client_context=client_context,
    )
    short_term_system_prompt = _build_short_term_system_prompt(
        history=request_history,
        persisted_messages=persisted_messages,
        runtime_context=runtime_context,
        forum_candidates=forum_candidates,
        graph_context=graph_context,
    )

    user_message = _persist_user_message(
        conversation_id=conversation.id,
        message=message,
        image_data_url=image_data_url,
    )
    memory_updates = _persist_explicit_memory_candidates(
        user_id=user_id,
        conversation_id=conversation.id,
        source_message_id=user_message.id,
        candidates=memory_candidates or [],
    )
    if decision is not None:
        persist_message_decision(
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            decision=decision,
        )
    effective_prompt_memory = (
        get_prompt_memory_summary(user_id)
        if memory_updates
        else (prompt_memory if prompt_memory is not None else get_prompt_memory_summary(user_id))
    )
    effective_prompt_memory = _apply_memory_candidates_to_prompt_memory(
        effective_prompt_memory,
        memory_candidates,
    )

    assistant_reply_parts: list[str] = []
    assistant_model: str | None = None
    assistant_message: AIMessage | None = None

    for event in stream_chat_with_openrouter(
        user_message=message,
        history=request_history,
        image_data_url=image_data_url,
        system_prompt=short_term_system_prompt,
        prompt_memory=effective_prompt_memory,
    ):
        event_type = event.get("type")
        if event_type == "meta":
            assistant_model = event.get("model")
            yield {
                **event,
                "conversation_id": conversation.id,
                "conversation_title": conversation.title,
                "user_message_id": user_message.id,
                "memory_updates": memory_updates,
            }
            continue

        if event_type == "delta":
            assistant_reply_parts.append(str(event.get("content", "")))
            yield event
            continue

        if event_type == "done":
            forum_references = _resolve_response_forum_references(
                "".join(assistant_reply_parts),
                forum_candidates,
                graph_context,
            )
            response_trace = _build_response_trace(
                decision=decision,
                conversation_id=conversation.id,
                forum_references=forum_references,
                graph_context=graph_context,
            )
            assistant_message = _persist_assistant_message(
                conversation_id=conversation.id,
                reply="".join(assistant_reply_parts),
                model=assistant_model,
                forum_references=forum_references,
                memory_updates=memory_updates,
                trace=response_trace,
            )
            yield {
                **event,
                "conversation_id": conversation.id,
                "conversation_title": conversation.title,
                "user_message_id": user_message.id,
                "assistant_message_id": assistant_message.id,
                "forum_references": forum_references,
                "graph_context": graph_context,
                "trace": response_trace,
            }
            return

        yield event


def complete_routed_chat_message(
    *,
    user_id: int | None,
    message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    conversation_id: int | None = None,
    client_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from app.services.ai.ai_decision_engine import decide_message
    from app.services.ai.demo_seed_replay_service import complete_seed_demo_replay
    from app.services.ai.langgraph_agent import complete_graph_agent_message, is_langgraph_available
    from app.services.ai.recycling_analysis_service import complete_recycling_analysis

    demo_replay = complete_seed_demo_replay(
        user_id=user_id,
        message=message,
        image_data_url=image_data_url,
        conversation_id=conversation_id,
    )
    if demo_replay is not None:
        return demo_replay

    if current_app.config.get("AI_GRAPH_AGENT_ENABLED", False) and is_langgraph_available():
        return complete_graph_agent_message(
            user_id=user_id,
            message=message,
            history=history,
            image_data_url=image_data_url,
            conversation_id=conversation_id,
            client_context=client_context,
        )

    decision = decide_message(
        user_id=user_id,
        conversation_id=conversation_id,
        message=message,
        image_data_url=image_data_url,
        supplied_history=history,
    )

    if decision["needs_clarification"]:
        persisted = _persist_clarification_request(
            user_id=user_id,
            message=message,
            image_data_url=image_data_url,
            conversation_id=conversation_id,
            decision=decision,
        )
        conversation = persisted["conversation"]
        user_message = persisted["user_message"]
        assistant_message = persisted.get("assistant_message")
        return {
            "reply": decision.get("clarification_question")
            or "Could you clarify which recycling task you mean?",
            "model": None,
            "usage": {},
            "conversation_id": conversation.id if conversation is not None else conversation_id,
            "conversation_title": conversation.title if conversation is not None else None,
            "user_message_id": user_message.id if user_message is not None else None,
            "assistant_message_id": assistant_message.id if assistant_message is not None else None,
            "memory_updates": [],
            "decision": {
                key: value
                for key, value in decision.items()
                if key not in {"context", "prompt_memory"}
            },
            "clarification_options": decision.get("clarification_options", []),
        }

    if decision["intent"] in {"recycling_analysis", "recycling_follow_up"}:
        return complete_recycling_analysis(
            user_id=user_id,
            message=message,
            image_data_url=image_data_url,
            conversation_id=conversation_id,
            decision=decision,
            client_context=client_context,
        )

    result = complete_chat_message(
        user_id=user_id,
        message=message,
        history=history,
        image_data_url=image_data_url,
        conversation_id=conversation_id,
        prompt_memory=decision["prompt_memory"],
        memory_candidates=decision["memory_candidates"],
        decision=decision,
        client_context=client_context,
    )
    result["decision"] = {
        key: value for key, value in decision.items() if key not in {"context", "prompt_memory"}
    }
    return result


def stream_routed_chat_message(
    *,
    user_id: int | None,
    message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    conversation_id: int | None = None,
    client_context: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    from app.services.ai.ai_decision_engine import decide_message
    from app.services.ai.demo_seed_replay_service import get_seed_demo_replay_stream
    from app.services.ai.langgraph_agent import is_langgraph_available, stream_graph_agent_message
    from app.services.ai.recycling_analysis_service import stream_recycling_analysis

    demo_replay_stream = get_seed_demo_replay_stream(
        user_id=user_id,
        message=message,
        image_data_url=image_data_url,
        conversation_id=conversation_id,
    )
    if demo_replay_stream is not None:
        yield from demo_replay_stream
        return

    if current_app.config.get("AI_GRAPH_AGENT_ENABLED", False) and is_langgraph_available():
        yield from stream_graph_agent_message(
            user_id=user_id,
            message=message,
            history=history,
            image_data_url=image_data_url,
            conversation_id=conversation_id,
            client_context=client_context,
        )
        return

    decision = decide_message(
        user_id=user_id,
        conversation_id=conversation_id,
        message=message,
        image_data_url=image_data_url,
        supplied_history=history,
    )
    serialized_decision = {
        key: value for key, value in decision.items() if key not in {"context", "prompt_memory"}
    }

    if decision["needs_clarification"]:
        persisted = _persist_clarification_request(
            user_id=user_id,
            message=message,
            image_data_url=image_data_url,
            conversation_id=conversation_id,
            decision=decision,
        )
        conversation = persisted["conversation"]
        user_message = persisted["user_message"]
        assistant_message = persisted.get("assistant_message")
        yield {
            "type": "meta",
            "conversation_id": conversation.id if conversation is not None else conversation_id,
            "conversation_title": conversation.title if conversation is not None else None,
            "user_message_id": user_message.id if user_message is not None else None,
            "assistant_message_id": assistant_message.id if assistant_message is not None else None,
            "decision": serialized_decision,
        }
        yield {
            "type": "clarification",
            "data": {
                "question": decision.get("clarification_question")
                or "Could you clarify which recycling task you mean?",
                "options": decision.get("clarification_options", []),
            },
        }
        yield {"type": "done", "stream_stage": "clarification"}
        return

    if decision["intent"] in {"recycling_analysis", "recycling_follow_up"}:
        yield from stream_recycling_analysis(
            message=message,
            image_data_url=image_data_url,
            session_id=None,
            conversation_id=conversation_id,
            user_id=user_id,
            decision=decision,
            client_context=client_context,
        )
        return

    for event in stream_chat_message(
        user_id=user_id,
        message=message,
        history=history,
        image_data_url=image_data_url,
        conversation_id=conversation_id,
        prompt_memory=decision["prompt_memory"],
        memory_candidates=decision["memory_candidates"],
        decision=decision,
        client_context=client_context,
    ):
        if event.get("type") == "meta":
            yield {
                **event,
                "decision": serialized_decision,
            }
            continue
        yield event


def list_user_conversations(
    *,
    user_id: int,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    offset = (page - 1) * per_page
    conversations = conversation_repository.list_conversations(
        user_id=user_id,
        limit=per_page,
        offset=offset,
    )
    total = _count_user_conversations(user_id)
    return {
        "items": [serialize_conversation(conversation) for conversation in conversations],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def get_conversation_messages(
    *,
    user_id: int,
    conversation_id: int,
) -> dict[str, Any]:
    conversation = conversation_repository.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found.")

    messages = conversation_repository.list_messages(conversation_id)
    recycling_cases = list(
        db.session.scalars(
            select(RecyclingCase)
            .where(RecyclingCase.conversation_id == conversation_id)
            .order_by(RecyclingCase.created_at.asc(), RecyclingCase.id.asc())
        )
    )
    audit_attempts_by_case_id = {
        case.id: recycling_case_repository.list_audit_attempts(case.id) for case in recycling_cases
    }
    case_by_id = {case.id: case for case in recycling_cases}
    case_by_origin_message_id = {case.origin_message_id: case for case in recycling_cases}
    latest_case = recycling_cases[-1] if recycling_cases else None

    serialized_items = []
    for message in messages:
        serialized_message = serialize_message(message)
        associated_case = case_by_origin_message_id.get(message.id)
        if associated_case is None and isinstance(serialized_message["content_json"], dict):
            case_id = serialized_message["content_json"].get("recycling_case_id")
            if case_id is not None:
                associated_case = case_by_id.get(case_id)
        serialized_message["recycling_case"] = _serialize_recycling_case(
            associated_case,
            audit_attempts=audit_attempts_by_case_id.get(getattr(associated_case, "id", None), []),
        )
        serialized_items.append(serialized_message)

    return {
        "conversation": serialize_conversation(conversation),
        "items": serialized_items,
        "total": len(messages),
        "pending_recycling_case": _serialize_recycling_case(
            latest_case
            if latest_case and latest_case.status in {"pending_audit", "audit_failed"}
            else None,
            audit_attempts=(
                audit_attempts_by_case_id.get(latest_case.id, [])
                if latest_case and latest_case.status in {"pending_audit", "audit_failed"}
                else []
            ),
        ),
    }


def delete_user_conversation(
    *,
    user_id: int,
    conversation_id: int,
) -> dict[str, Any]:
    deleted = conversation_repository.delete_conversation(conversation_id, user_id)
    if not deleted:
        raise ValueError(f"Conversation {conversation_id} not found.")

    return {
        "deleted_conversation_id": conversation_id,
    }
