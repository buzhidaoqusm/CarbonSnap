from __future__ import annotations

import json
from typing import Any

from app.services.ai.openrouter_service import complete_json_diagnostic


def resolve_target_case(
    *,
    message: str,
    recent_history: list[dict[str, Any]],
    case_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    return resolve_target_case_detailed(
        message=message,
        recent_history=recent_history,
        case_summaries=case_summaries,
        allow_heuristic_fallback=True,
    )["result"]


def resolve_target_case_detailed(
    *,
    message: str,
    recent_history: list[dict[str, Any]],
    case_summaries: list[dict[str, Any]],
    allow_heuristic_fallback: bool,
) -> dict[str, Any]:
    if not case_summaries:
        result = {
            "target_case_id": None,
            "confidence": 0.0,
            "needs_clarification": True,
            "clarification_question": "I couldn't find an active recycling case in this chat. Which item would you like to continue?",
            "clarification_options": [],
        }
        return {
            "result": result,
            "resolver_failure_reason": "no_candidate_cases",
            "raw_resolver_payload": None,
            "used_fallback": True,
            "fallback_mode": "safe_default",
        }

    diagnostic = complete_json_diagnostic(
        user_message=json.dumps(
            {
                "message": message,
                "recent_history": recent_history[-6:],
                "case_summaries": case_summaries,
            },
            ensure_ascii=False,
        ),
        system_prompt=_resolver_system_prompt(),
    )

    payload = diagnostic.get("payload")
    normalized = _normalize_resolver_payload(payload) if isinstance(payload, dict) else {}
    if normalized:
        return {
            "result": normalized,
            "resolver_failure_reason": None,
            "raw_resolver_payload": diagnostic.get("raw_reply"),
            "used_fallback": False,
            "fallback_mode": None,
        }

    failure_reason = str(diagnostic.get("error") or "invalid_resolver_payload")
    result = (
        _heuristic_fallback(message=message, case_summaries=case_summaries)
        if allow_heuristic_fallback
        else _safe_default(case_summaries=case_summaries)
    )
    return {
        "result": result,
        "resolver_failure_reason": failure_reason,
        "raw_resolver_payload": diagnostic.get("raw_reply"),
        "used_fallback": True,
        "fallback_mode": "heuristic_fallback" if allow_heuristic_fallback else "safe_default",
    }


def _normalize_resolver_payload(raw: dict[str, Any]) -> dict[str, Any]:
    target_case_id = raw.get("target_case_id")
    try:
        parsed_case_id = int(target_case_id) if target_case_id is not None else None
    except (TypeError, ValueError):
        parsed_case_id = None

    clarification_options = raw.get("clarification_options") or []
    if not isinstance(clarification_options, list):
        clarification_options = []

    try:
        confidence = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "target_case_id": parsed_case_id,
        "confidence": max(0.0, min(1.0, confidence)),
        "needs_clarification": bool(raw.get("needs_clarification", False)),
        "clarification_question": str(raw.get("clarification_question") or "").strip() or None,
        "clarification_options": [
            {
                "label": str(item.get("label") or "").strip(),
                "reply_text": str(item.get("reply_text") or "").strip(),
            }
            for item in clarification_options
            if isinstance(item, dict)
            and str(item.get("label") or "").strip()
            and str(item.get("reply_text") or "").strip()
        ],
    }


def _heuristic_fallback(*, message: str, case_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    if len(case_summaries) == 1:
        return {
            "target_case_id": case_summaries[0]["case_id"],
            "confidence": 0.7,
            "needs_clarification": False,
            "clarification_question": None,
            "clarification_options": [],
        }

    normalized = str(message or "").strip().lower()
    matches = [
        case
        for case in case_summaries
        if str(case.get("predicted_item") or "").strip().lower() in normalized
    ]
    if len(matches) == 1:
        return {
            "target_case_id": matches[0]["case_id"],
            "confidence": 0.66,
            "needs_clarification": False,
            "clarification_question": None,
            "clarification_options": [],
        }

    return _safe_default(case_summaries=case_summaries)


def _safe_default(*, case_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    options = [
        {
            "label": f"{case.get('predicted_item') or 'Recycling case'} ({case.get('current_stage') or case.get('status')})",
            "reply_text": f"I mean the case about {case.get('predicted_item') or 'that item'}.",
        }
        for case in case_summaries[:4]
    ]
    return {
        "target_case_id": None,
        "confidence": 0.0,
        "needs_clarification": True,
        "clarification_question": "I found multiple recycling tasks in this chat. Which one do you mean?",
        "clarification_options": options,
    }


def _resolver_system_prompt() -> str:
    return """
You are CarbonSnap's recycling-case resolver.
Choose which existing recycling case the user's current message refers to.

Return exactly one JSON object with:
- target_case_id: integer or null
- confidence: number between 0 and 1
- needs_clarification: boolean
- clarification_question: string or null
- clarification_options: array of objects with label and reply_text

Rules:
- Resolve only against the provided case_summaries.
- If one case is clearly indicated, choose it.
- If there are multiple plausible cases and confidence is low, ask for clarification.
- Return JSON only.
""".strip()
