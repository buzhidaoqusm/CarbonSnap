from __future__ import annotations

import json
from typing import Any

from app.services.ai.openrouter_service import complete_json_diagnostic


INTENTS = {"general_chat", "recycling_analysis", "recycling_follow_up"}
FOLLOW_UP_TYPES = {"guidance_follow_up", "nearby_search", "task_verification"}
ROUTER_FEW_SHOTS: tuple[dict[str, Any], ...] = (
    {
        "message": "How do I recycle this plastic bottle?",
        "has_active_case": False,
        "case_count": 0,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_analysis",
            "follow_up_type": None,
            "needs_clarification": False,
        },
    },
    {
        "message": "Can this battery be recycled?",
        "has_active_case": False,
        "case_count": 0,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_analysis",
            "follow_up_type": None,
            "needs_clarification": False,
        },
    },
    {
        "message": "Which bin should this glass jar go in?",
        "has_active_case": False,
        "case_count": 0,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_analysis",
            "follow_up_type": None,
            "needs_clarification": False,
        },
    },
    {
        "message": "Where should I dispose of this old charger?",
        "has_active_case": False,
        "case_count": 0,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_analysis",
            "follow_up_type": None,
            "needs_clarification": False,
        },
    },
    {
        "message": "What did I just ask you about?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "general_chat",
            "follow_up_type": None,
            "needs_clarification": False,
        },
    },
    {
        "message": "What was my previous recycling item?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "general_chat",
            "follow_up_type": None,
            "needs_clarification": False,
        },
    },
    {
        "message": "Any interesting DIY ideas for this bottle?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "general_chat",
            "follow_up_type": None,
            "needs_clarification": False,
        },
    },
    {
        "message": "What do people usually say about recycling plastic bottles?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "general_chat",
            "follow_up_type": None,
            "needs_clarification": False,
        },
    },
    {
        "message": "Can you give me another recycling method besides putting it in the recycling bin?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_follow_up",
            "follow_up_type": "guidance_follow_up",
            "needs_clarification": False,
        },
    },
    {
        "message": "Any other option for this one?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_follow_up",
            "follow_up_type": "guidance_follow_up",
            "needs_clarification": False,
        },
    },
    {
        "message": "What else can I do with it?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_follow_up",
            "follow_up_type": "guidance_follow_up",
            "needs_clarification": False,
        },
    },
    {
        "message": "Can you suggest a different recycling approach?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_follow_up",
            "follow_up_type": "guidance_follow_up",
            "needs_clarification": False,
        },
    },
    {
        "message": "Where can I recycle it near me?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "recent_history": [
            {"role": "user", "content": "Can you give me another recycling method besides putting it in the recycling bin?"},
            {"role": "assistant", "content": "You could upcycle the bottle into a DIY lantern."},
        ],
        "expected": {
            "intent": "recycling_follow_up",
            "follow_up_type": "nearby_search",
            "needs_clarification": False,
        },
    },
    {
        "message": "Where can I recycle it near me?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_follow_up",
            "follow_up_type": "nearby_search",
            "needs_clarification": False,
        },
    },
    {
        "message": "Show me nearby recycling points.",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_follow_up",
            "follow_up_type": "nearby_search",
            "needs_clarification": False,
        },
    },
    {
        "message": "Can you find a drop-off location near me for this?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_follow_up",
            "follow_up_type": "nearby_search",
            "needs_clarification": False,
        },
    },
    {
        "message": "I allowed location, now where should I take it?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "location_permission"},
        "expected": {
            "intent": "recycling_follow_up",
            "follow_up_type": "nearby_search",
            "needs_clarification": False,
        },
    },
    {
        "message": "Did I finish it correctly?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_follow_up",
            "follow_up_type": "task_verification",
            "needs_clarification": False,
        },
    },
    {
        "message": "Can you verify this completion photo?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_follow_up",
            "follow_up_type": "task_verification",
            "needs_clarification": False,
        },
    },
    {
        "message": "Why did my verification fail?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_follow_up",
            "follow_up_type": "task_verification",
            "needs_clarification": False,
        },
    },
    {
        "message": "Did I finish it correctly?",
        "has_active_case": True,
        "case_count": 1,
        "conversation_state": {"current_pending_action": "none"},
        "recent_history": [
            {"role": "user", "content": "Can you give me another recycling method besides putting it in the recycling bin?"},
            {"role": "assistant", "content": "You could upcycle it into a decorative DIY lantern."},
        ],
        "expected": {
            "intent": "recycling_follow_up",
            "follow_up_type": "task_verification",
            "needs_clarification": False,
        },
    },
    {
        "message": "Can you find a nearby drop-off point for it?",
        "has_active_case": True,
        "case_count": 2,
        "conversation_state": {"current_pending_action": "none"},
        "expected": {
            "intent": "recycling_follow_up",
            "follow_up_type": "nearby_search",
            "needs_clarification": True,
        },
    },
)


def classify_intent(
    *,
    message: str,
    image_data_url: str | None,
    recent_history: list[dict[str, Any]],
    case_summaries: list[dict[str, Any]],
    conversation_state: dict[str, Any] | None,
    prompt_memory: dict[str, Any] | None,
) -> dict[str, Any]:
    return classify_intent_detailed(
        message=message,
        image_data_url=image_data_url,
        recent_history=recent_history,
        case_summaries=case_summaries,
        conversation_state=conversation_state,
        prompt_memory=prompt_memory,
        allow_business_fallback=True,
    )["result"]


def classify_intent_detailed(
    *,
    message: str,
    image_data_url: str | None,
    recent_history: list[dict[str, Any]],
    case_summaries: list[dict[str, Any]],
    conversation_state: dict[str, Any] | None,
    prompt_memory: dict[str, Any] | None,
    allow_business_fallback: bool,
) -> dict[str, Any]:
    diagnostic = complete_json_diagnostic(
        user_message=_build_router_user_prompt(
            message=message,
            recent_history=recent_history,
            case_summaries=case_summaries,
            conversation_state=conversation_state,
            prompt_memory=prompt_memory,
        ),
        image_data_url=image_data_url,
        system_prompt=_router_system_prompt(),
    )

    payload = diagnostic.get("payload")
    normalized = _normalize_router_payload(payload) if isinstance(payload, dict) else {}
    if normalized:
        return {
            "result": normalized,
            "router_failure_reason": None,
            "raw_router_payload": diagnostic.get("raw_reply"),
            "used_fallback": False,
            "fallback_mode": None,
        }

    fallback_mode = "business_fallback" if allow_business_fallback else "safe_default"
    failure_reason = str(diagnostic.get("error") or "invalid_intent")
    if isinstance(payload, dict) and not normalized and not diagnostic.get("error"):
        failure_reason = "invalid_intent"

    result = (
        _business_fallback_route(message=message, case_summaries=case_summaries, conversation_state=conversation_state)
        if allow_business_fallback
        else _safe_default_route()
    )
    return {
        "result": result,
        "router_failure_reason": failure_reason,
        "raw_router_payload": diagnostic.get("raw_reply"),
        "used_fallback": True,
        "fallback_mode": fallback_mode,
    }


def _normalize_router_payload(raw: dict[str, Any]) -> dict[str, Any]:
    intent = str(raw.get("intent") or "").strip().lower()
    if intent not in INTENTS:
        return {}

    follow_up_type = str(raw.get("follow_up_type") or "").strip().lower() or None
    if follow_up_type not in FOLLOW_UP_TYPES:
        follow_up_type = None

    clarification_options = raw.get("clarification_options") or []
    if not isinstance(clarification_options, list):
        clarification_options = []

    try:
        confidence = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    return {
        "intent": intent,
        "follow_up_type": follow_up_type,
        "confidence": confidence,
        "possible_preference_signal": bool(raw.get("possible_preference_signal", False)),
        "needs_clarification": bool(raw.get("needs_clarification", False)),
        "clarification_question": str(raw.get("clarification_question") or "").strip() or None,
        "clarification_options": [
            {
                "label": str(option.get("label") or "").strip(),
                "reply_text": str(option.get("reply_text") or "").strip(),
            }
            for option in clarification_options
            if isinstance(option, dict)
            and str(option.get("label") or "").strip()
            and str(option.get("reply_text") or "").strip()
        ],
    }


def _business_fallback_route(
    *,
    message: str,
    case_summaries: list[dict[str, Any]],
    conversation_state: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = str(message or "").strip().lower()
    possible_preference_signal = any(
        token in normalized
        for token in (
            "prefer",
            "i like",
            "i want",
            "from now on",
            "不要",
            "别用",
        )
    )

    if case_summaries and _looks_like_guidance_follow_up(normalized):
        return {
            "intent": "recycling_follow_up",
            "follow_up_type": "guidance_follow_up",
            "confidence": 0.6,
            "possible_preference_signal": possible_preference_signal,
            "needs_clarification": False,
            "clarification_question": None,
            "clarification_options": [],
        }

    if any(token in normalized for token in ("nearby", "location", "map", "where can i recycle")) and case_summaries:
        return {
            "intent": "recycling_follow_up",
            "follow_up_type": "nearby_search",
            "confidence": 0.55,
            "possible_preference_signal": possible_preference_signal,
            "needs_clarification": False,
            "clarification_question": None,
            "clarification_options": [],
        }

    if any(token in normalized for token in ("verify", "audit", "completed", "did i finish")) and case_summaries:
        return {
            "intent": "recycling_follow_up",
            "follow_up_type": "task_verification",
            "confidence": 0.55,
            "possible_preference_signal": possible_preference_signal,
            "needs_clarification": False,
            "clarification_question": None,
            "clarification_options": [],
        }

    pending_action = str((conversation_state or {}).get("current_pending_action") or "").strip().lower()
    if pending_action == "location_permission" and case_summaries:
        return {
            "intent": "recycling_follow_up",
            "follow_up_type": "nearby_search",
            "confidence": 0.58,
            "possible_preference_signal": possible_preference_signal,
            "needs_clarification": False,
            "clarification_question": None,
            "clarification_options": [],
        }

    if _looks_like_recycling_ideation(normalized):
        return {
            "intent": "general_chat",
            "follow_up_type": None,
            "confidence": 0.54,
            "possible_preference_signal": possible_preference_signal,
            "needs_clarification": False,
            "clarification_question": None,
            "clarification_options": [],
        }

    if _looks_like_recycling_analysis_request(normalized):
        return {
            "intent": "recycling_analysis",
            "follow_up_type": None,
            "confidence": 0.56,
            "possible_preference_signal": possible_preference_signal,
            "needs_clarification": False,
            "clarification_question": None,
            "clarification_options": [],
        }

    return {
        "intent": "general_chat",
        "follow_up_type": None,
        "confidence": 0.51,
        "possible_preference_signal": possible_preference_signal,
        "needs_clarification": False,
        "clarification_question": None,
        "clarification_options": [],
    }


def _safe_default_route() -> dict[str, Any]:
    return {
        "intent": "general_chat",
        "follow_up_type": None,
        "confidence": 0.0,
        "possible_preference_signal": False,
        "needs_clarification": False,
        "clarification_question": None,
        "clarification_options": [],
    }


def _looks_like_guidance_follow_up(normalized: str) -> bool:
    direct_tokens = (
        "other suggestion",
        "other suggestions",
        "more suggestions",
        "more advice",
        "other recycling advice",
        "what else can i do",
        "what else should i do",
        "anything else",
        "another option",
        "还有什么建议",
        "还有别的",
        "还可以怎么",
    )
    if any(token in normalized for token in direct_tokens):
        return True

    english_other = ("other", "more", "another", "else", "alternative")
    english_guidance = ("suggestion", "suggestions", "advice", "option", "options")
    chinese_other = ("其他", "别的", "更多", "另外", "还有")
    chinese_guidance = ("建议", "回收建议", "做法", "办法")

    return (
        any(token in normalized for token in english_other)
        and any(token in normalized for token in english_guidance)
    ) or (
        any(token in normalized for token in chinese_other)
        and any(token in normalized for token in chinese_guidance)
    )


def _looks_like_recycling_ideation(normalized: str) -> bool:
    english_idea_tokens = (
        "interesting",
        "creative",
        "fun",
        "cool",
        "idea",
        "ideas",
        "tips",
        "method",
        "methods",
        "way",
        "ways",
        "repurpose",
        "upcycle",
        "craft",
        "diy",
    )
    chinese_idea_tokens = (
        "有意思",
        "有趣",
        "创意",
        "点子",
        "想法",
        "方法",
        "做法",
        "妙招",
        "改造",
        "手工",
    )
    recycling_subject_tokens = (
        "recycle",
        "recycling",
        "plastic bottle",
        "bottle",
        "battery",
        "电子",
        "塑料瓶",
        "瓶子",
        "电池",
        "回收",
    )

    return any(token in normalized for token in recycling_subject_tokens) and (
        any(token in normalized for token in english_idea_tokens)
        or any(token in normalized for token in chinese_idea_tokens)
    )


def _looks_like_recycling_analysis_request(normalized: str) -> bool:
    direct_tokens = (
        "how do i recycle",
        "how can i recycle",
        "can this be recycled",
        "where can i recycle",
        "what bin",
        "which bin",
        "recycling instructions",
        "recycling steps",
        "how to dispose",
        "怎么回收",
        "如何回收",
        "能回收吗",
        "可回收吗",
        "扔哪个垃圾桶",
        "属于什么垃圾",
    )
    broad_tokens = ("recycle", "recycling", "回收", "垃圾分类")
    task_tokens = (
        "dispose",
        "bin",
        "instructions",
        "steps",
        "where",
        "location",
        "drop off",
        "center",
        "centre",
        "recycling center",
        "recycling centre",
        "怎么",
        "如何",
        "哪里",
        "在哪",
        "垃圾桶",
        "站点",
    )

    return any(token in normalized for token in direct_tokens) or (
        any(token in normalized for token in broad_tokens)
        and any(token in normalized for token in task_tokens)
    )


def _build_router_user_prompt(
    *,
    message: str,
    recent_history: list[dict[str, Any]],
    case_summaries: list[dict[str, Any]],
    conversation_state: dict[str, Any] | None,
    prompt_memory: dict[str, Any] | None,
) -> str:
    payload = {
        "task": (
            "Classify the CURRENT message. Use history only to resolve references such as "
            "'it', 'this', 'that', or to determine whether an existing recycling case is active. "
            "Do not let prior assistant suggestions override explicit intent signals in the current message."
        ),
        "current_message": message,
        "recent_history_for_reference_only": recent_history[-6:],
        "active_case_summaries": case_summaries,
        "conversation_state": conversation_state or {},
        "memory_summary": prompt_memory or {},
    }
    return json.dumps(payload, ensure_ascii=False)


def _format_router_few_shots() -> str:
    lines = ["Examples:"]
    for index, example in enumerate(ROUTER_FEW_SHOTS, start=1):
        lines.append(f"Example {index}:")
        lines.append(
            json.dumps(
                {
                    "message": example["message"],
                    "has_active_case": example["has_active_case"],
                    "case_count": example["case_count"],
                    "conversation_state": example["conversation_state"],
                    "recent_history": example.get("recent_history", []),
                    "expected": example["expected"],
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(lines)


def _router_system_prompt() -> str:
    return f"""
You are CarbonSnap's AI decision router.
Classify the user's CURRENT message only, while using recent conversation context and active recycling cases for disambiguation.

Return exactly one JSON object with these fields:
- intent: one of {sorted(INTENTS)}
- follow_up_type: one of {sorted(FOLLOW_UP_TYPES)} or null
- confidence: number between 0 and 1
- possible_preference_signal: boolean
- needs_clarification: boolean
- clarification_question: string or null
- clarification_options: array of objects with label and reply_text

Rules:
- Images are supporting context only. They do NOT force recycling intent.
- The current message is the primary signal. Recent history is secondary context only.
- Use recent history only for pronoun resolution, case continuity, and ambiguity resolution. Do not let earlier assistant suggestions override clear intent words in the current message.
- General chat includes normal conversation, image description requests, conversation-memory questions, and broad ideation such as interesting, creative, DIY, or forum-style discussion about reuse or recycling ideas.
- recycling_analysis means the user is asking for direct task-oriented recycling or disposal help for a specific item, such as identifying whether it is recyclable, which bin it belongs in, where to take it, or concrete recycling steps.
- recycling_follow_up means the user is continuing an existing recycling task or case.
- If the conversation already contains a recycling case and the user asks for more, other, or alternative recycling suggestions, treat it as recycling_follow_up with follow_up_type=guidance_follow_up.
- Questions like "what did I just recycle" or "what was my previous message" remain general_chat, even if they mention recycling.
- Questions like "any interesting ways to recycle a plastic bottle" or "creative ideas for recycling this" should stay general_chat unless the user is clearly asking to execute a recycling task.
- Asking for nearby places, location-based help, or map results for an existing case is recycling_follow_up with follow_up_type=nearby_search.
- Asking to verify completion, retry a proof photo, or discuss why verification passed/failed is recycling_follow_up with follow_up_type=task_verification.
- Prioritize location intent words such as "near me", "nearby", "drop-off location", "where should I take it", "location", and "map" over broad guidance wording when an active case already exists.
- Treat first-turn disposal questions about a concrete item, including "which bin", "where should I dispose of", and "where do I take this", as recycling_analysis unless the user is clearly continuing an existing case's location search.
- If the current message explicitly asks for location help, do not keep the request in guidance_follow_up just because the previous turn discussed alternative methods or upcycling.
- If the current message explicitly asks for verification, do not keep the request in guidance_follow_up just because the previous turn discussed advice or reuse ideas.
- Use needs_clarification only when the user is clearly referring to an existing recycling task but the target is ambiguous.
- If clarification is unnecessary, clarification_options must be [].
- Mark possible_preference_signal true only when the current user message appears to express a stable preference explicitly.
- Match the patterns in the examples below closely when the current message is similar.
- Return JSON only.

{_format_router_few_shots()}
""".strip()
