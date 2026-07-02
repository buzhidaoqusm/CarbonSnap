from __future__ import annotations

import re
from typing import Any

from flask import current_app

from app.repositories.ai import message_decision_repository
from app.services.ai.agent_trace_service import build_trace_shell
from app.services.ai.case_resolver import resolve_target_case_detailed
from app.services.ai.conversation_context_builder import build_context_bundle
from app.services.ai.intent_router import classify_intent_detailed
from app.services.ai.memory_extractor import extract_explicit_memory_candidates_detailed
from app.services.ai.memory_service import get_prompt_memory_summary
from app.services.ai.prompt_registry import get_prompt_version

_FORUM_QUERY_HINTS = (
    "forum",
    "post",
    "community",
    "discussion",
    "discuss",
    "experience",
    "experiences",
    "tip",
    "tips",
    "best practice",
    "people say",
    "how do i recycle",
    "where do i recycle",
    "recycle",
    "recycling",
    "carbon",
    "sustainability",
    "经验",
    "帖子",
    "讨论",
    "社区",
    "回收",
    "怎么回收",
    "如何回收",
)

def decide_message(
    *,
    user_id: int | None,
    conversation_id: int | None,
    message: str,
    image_data_url: str | None,
    supplied_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    mode = _get_engine_mode()

    if mode == "llm_first":
        decision = _run_decision_pipeline(
            user_id=user_id,
            conversation_id=conversation_id,
            message=message,
            image_data_url=image_data_url,
            supplied_history=supplied_history,
            llm_first=True,
            label="llm_first",
        )
        decision["decision_mode"] = "llm_first"
        return decision

    primary = _run_decision_pipeline(
        user_id=user_id,
        conversation_id=conversation_id,
        message=message,
        image_data_url=image_data_url,
        supplied_history=supplied_history,
        llm_first=False,
        label="compat",
    )
    primary["decision_mode"] = mode

    if mode == "shadow":
        shadow = _run_decision_pipeline(
            user_id=user_id,
            conversation_id=conversation_id,
            message=message,
            image_data_url=image_data_url,
            supplied_history=supplied_history,
            llm_first=True,
            label="shadow",
        )
        primary["shadow_decision"] = _serialize_shadow_decision(shadow)

    return primary


def _run_decision_pipeline(
    *,
    user_id: int | None,
    conversation_id: int | None,
    message: str,
    image_data_url: str | None,
    supplied_history: list[dict[str, Any]] | None,
    llm_first: bool,
    label: str,
) -> dict[str, Any]:
    max_turns = int(current_app.config.get("AI_SHORT_TERM_MEMORY_TURNS", 10) or 10)
    prompt_memory = get_prompt_memory_summary(user_id)
    context = build_context_bundle(
        conversation_id=conversation_id,
        supplied_history=supplied_history,
        max_turns=max_turns,
    )
    conversation_state = context["working_memory"].get("conversation_state") or {}

    routing_detail = classify_intent_detailed(
        message=message,
        image_data_url=image_data_url,
        recent_history=context["recent_history"],
        case_summaries=context["case_summaries"],
        conversation_state=conversation_state,
        prompt_memory=prompt_memory,
        allow_business_fallback=not llm_first,
    )
    routing = routing_detail["result"]

    target_case_id = None
    clarification_question = routing.get("clarification_question")
    clarification_options = routing.get("clarification_options", [])
    needs_clarification = bool(routing.get("needs_clarification", False))
    resolution_confidence = None
    resolver_detail: dict[str, Any] | None = None

    if routing["intent"] == "recycling_follow_up":
        resolver_detail = resolve_target_case_detailed(
            message=message,
            recent_history=context["recent_history"],
            case_summaries=context["case_summaries"],
            allow_heuristic_fallback=not llm_first,
        )
        resolution = resolver_detail["result"]
        target_case_id = resolution.get("target_case_id")
        resolution_confidence = resolution.get("confidence")
        if resolution.get("needs_clarification"):
            needs_clarification = True
            clarification_question = resolution.get("clarification_question")
            clarification_options = resolution.get("clarification_options", [])

    extractor_detail = extract_explicit_memory_candidates_detailed(
        message,
        recent_history=context["recent_history"],
        prompt_memory=prompt_memory,
        allow_heuristic_fallback=not llm_first,
    )
    threshold = _get_confidence_threshold()
    if (
        routing["intent"] == "recycling_follow_up"
        and target_case_id is not None
        and len(context["case_summaries"]) > 1
        and resolution_confidence is not None
        and resolution_confidence < threshold
    ):
        target_case_id = None
        needs_clarification = True
        if not clarification_question:
            clarification_question = "I found multiple recycling tasks in this chat. Which one do you mean?"
        if not clarification_options:
            clarification_options = [
                {
                    "label": f"{case.get('predicted_item') or 'Recycling case'} ({case.get('current_stage') or case.get('status') or 'unknown'})",
                    "reply_text": f"I mean the case about {case.get('predicted_item') or 'that item'}.",
                }
                for case in context["case_summaries"][:4]
            ]

    forum_retrieval = _decide_forum_retrieval(
        intent=routing["intent"],
        follow_up_type=routing.get("follow_up_type"),
        message=message,
        image_data_url=image_data_url,
        context=context,
    )

    decision = {
        "engine_version": _get_engine_version(),
        "pipeline_label": label,
        "intent": routing["intent"],
        "follow_up_type": routing.get("follow_up_type"),
        "confidence": routing.get("confidence"),
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_question,
        "clarification_options": clarification_options,
        "target_case_id": target_case_id,
        "resolution_confidence": resolution_confidence,
        "should_create_new_case": routing["intent"] == "recycling_analysis",
        "should_retrieve_forum": forum_retrieval["should_retrieve_forum"],
        "forum_retrieval_reason": forum_retrieval["forum_retrieval_reason"],
        "forum_citation_policy": forum_retrieval["forum_citation_policy"],
        "memory_candidates": extractor_detail["candidates"],
        "context": context,
        "prompt_memory": prompt_memory,
        "router_failure_reason": routing_detail.get("router_failure_reason"),
        "raw_router_payload": routing_detail.get("raw_router_payload"),
        "router_used_fallback": routing_detail.get("used_fallback", False),
        "router_fallback_mode": routing_detail.get("fallback_mode"),
        "resolver_failure_reason": (resolver_detail or {}).get("resolver_failure_reason"),
        "raw_resolver_payload": (resolver_detail or {}).get("raw_resolver_payload"),
        "resolver_used_fallback": (resolver_detail or {}).get("used_fallback", False),
        "resolver_fallback_mode": (resolver_detail or {}).get("fallback_mode"),
        "extractor_failure_reason": extractor_detail.get("extractor_failure_reason"),
        "raw_extractor_payload": extractor_detail.get("raw_extractor_payload"),
        "extractor_used_fallback": extractor_detail.get("used_fallback", False),
        "extractor_fallback_mode": extractor_detail.get("fallback_mode"),
    }
    if _trace_enabled():
        decision["trace"] = _build_decision_trace(
            user_id=user_id,
            conversation_id=conversation_id,
            decision=decision,
            prompt_memory=prompt_memory,
        )
    return decision


def _serialize_shadow_decision(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in decision.items()
        if key not in {"context", "prompt_memory", "shadow_decision"}
    }


def _get_engine_mode() -> str:
    mode = str(current_app.config.get("AI_DECISION_ENGINE_MODE", "llm_first") or "llm_first").strip().lower()
    if mode not in {"compat", "shadow", "llm_first"}:
        return "llm_first"
    return mode


def _get_engine_version() -> str:
    return str(
        current_app.config.get("AI_DECISION_ENGINE_VERSION", "decision-engine-v2")
        or "decision-engine-v2"
    ).strip() or "decision-engine-v2"


def _trace_enabled() -> bool:
    return bool(current_app.config.get("AI_TRACE_ENABLED", True))


def _build_decision_trace(
    *,
    user_id: int | None,
    conversation_id: int | None,
    decision: dict[str, Any],
    prompt_memory: dict[str, Any] | None,
) -> dict[str, Any]:
    trace = build_trace_shell(
        user_id=user_id,
        conversation_id=conversation_id,
        intent=decision.get("intent"),
    )
    trace["router"].update(
        {
            "intent": decision.get("intent"),
            "follow_up_type": decision.get("follow_up_type"),
            "confidence": decision.get("confidence"),
            "used_fallback": decision.get("router_used_fallback", False),
            "fallback_mode": decision.get("router_fallback_mode"),
            "failure_reason": decision.get("router_failure_reason"),
        }
    )
    trace["memory"].update(
        {
            "used": bool(prompt_memory),
            "summary": prompt_memory if prompt_memory else None,
        }
    )
    trace["retrieval"]["forum"].update(
        {
            "enabled": bool(decision.get("should_retrieve_forum")),
            "reason": decision.get("forum_retrieval_reason"),
            "citation_policy": decision.get("forum_citation_policy"),
        }
    )
    trace["guardrails"]["fallback_applied"] = bool(decision.get("router_used_fallback"))
    if decision.get("router_failure_reason"):
        trace["guardrails"]["reasons"].append(decision["router_failure_reason"])
    trace["prompt_versions"]["router"] = get_prompt_version("router")
    trace["prompt_versions"]["decision_engine"] = decision.get("engine_version")
    return trace


def _get_confidence_threshold() -> float:
    try:
        threshold = float(current_app.config.get("AI_DECISION_CONFIDENCE_THRESHOLD", 0.65) or 0.65)
    except (TypeError, ValueError):
        threshold = 0.65
    return max(0.0, min(1.0, threshold))


def _decide_forum_retrieval(
    *,
    intent: str,
    follow_up_type: str | None,
    message: str,
    image_data_url: str | None,
    context: dict[str, Any],
) -> dict[str, Any]:
    normalized_message = str(message or "").strip().lower()
    recent_history = context.get("recent_history") or []
    case_summaries = context.get("case_summaries") or []

    if intent in {"recycling_analysis", "recycling_follow_up"}:
        return {
            "should_retrieve_forum": True,
            "forum_retrieval_reason": f"recycling_priority:{follow_up_type or 'analysis'}",
            "forum_citation_policy": "mixed_strict_for_facts",
        }

    has_query_hint = any(keyword in normalized_message for keyword in _FORUM_QUERY_HINTS)
    asks_about_people = bool(re.search(r"\b(anyone|someone|others|people)\b", normalized_message))
    has_image = bool(str(image_data_url or "").strip())
    has_relevant_history = bool(recent_history or case_summaries)

    should_retrieve = has_query_hint or asks_about_people or (has_image and has_relevant_history)
    return {
        "should_retrieve_forum": should_retrieve,
        "forum_retrieval_reason": "general_chat_hint" if should_retrieve else "not_triggered",
        "forum_citation_policy": "mixed_strict_for_facts",
    }


def persist_message_decision(
    *,
    conversation_id: int,
    user_message_id: int,
    decision: dict[str, Any],
) -> Any:
    payload = {
        key: value
        for key, value in decision.items()
        if key not in {"context", "prompt_memory"}
    }
    return message_decision_repository.create_message_decision(
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        intent=decision["intent"],
        follow_up_type=decision.get("follow_up_type"),
        target_case_id=decision.get("target_case_id"),
        confidence=decision.get("resolution_confidence") or decision.get("confidence"),
        needs_clarification=bool(decision.get("needs_clarification")),
        decision_payload=payload,
        engine_version=decision.get("engine_version", _get_engine_version()),
    )
