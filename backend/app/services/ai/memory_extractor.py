from __future__ import annotations

import json
from typing import Any

from app.services.ai.openrouter_service import complete_json_diagnostic


def _normalize(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def extract_explicit_memory_candidates(
    text: str,
    *,
    recent_history: list[dict[str, Any]] | None = None,
    prompt_memory: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return extract_explicit_memory_candidates_detailed(
        text,
        recent_history=recent_history,
        prompt_memory=prompt_memory,
        allow_heuristic_fallback=True,
    )["candidates"]


def extract_explicit_memory_candidates_detailed(
    text: str,
    *,
    recent_history: list[dict[str, Any]] | None = None,
    prompt_memory: dict[str, Any] | None = None,
    allow_heuristic_fallback: bool,
) -> dict[str, Any]:
    normalized = _normalize(text)
    if not normalized:
        return {
            "candidates": [],
            "extractor_failure_reason": None,
            "raw_extractor_payload": None,
            "used_fallback": False,
            "fallback_mode": None,
        }

    diagnostic = complete_json_diagnostic(
        user_message=json.dumps(
            {
                "message": text,
                "recent_history": recent_history or [],
                "existing_memory_summary": prompt_memory or {},
            },
            ensure_ascii=False,
        ),
        system_prompt=_memory_extractor_system_prompt(),
        auxiliary=True,
    )

    payload = diagnostic.get("payload")
    normalized_candidates = _normalize_candidates(payload) if isinstance(payload, dict) else None
    if normalized_candidates is not None:
        candidates = (
            _merge_with_fallback(normalized_candidates, _heuristic_fallback_extract(normalized))
            if allow_heuristic_fallback
            else normalized_candidates
        )
        return {
            "candidates": candidates,
            "extractor_failure_reason": None,
            "raw_extractor_payload": diagnostic.get("raw_reply"),
            "used_fallback": False,
            "fallback_mode": None,
        }

    candidates = _heuristic_fallback_extract(normalized) if allow_heuristic_fallback else []
    return {
        "candidates": candidates,
        "extractor_failure_reason": str(diagnostic.get("error") or "invalid_memory_payload"),
        "raw_extractor_payload": diagnostic.get("raw_reply"),
        "used_fallback": bool(allow_heuristic_fallback and candidates),
        "fallback_mode": "heuristic_fallback"
        if allow_heuristic_fallback and candidates
        else "safe_default",
    }


def _normalize_candidates(raw: dict[str, Any]) -> list[dict[str, Any]] | None:
    candidates = raw.get("memory_candidates")
    if candidates is None:
        if raw.get("is_explicit_preference") is False:
            return []
        return None
    if not isinstance(candidates, list):
        return None

    normalized_items: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        memory_type = str(item.get("memory_type") or "").strip()
        memory_key = str(item.get("memory_key") or "").strip()
        value = item.get("value")
        if memory_type and memory_key and isinstance(value, dict) and value:
            if memory_type == "response_style":
                memory_key = "response_style"
            elif memory_type == "topic_interest":
                memory_key = str(value.get("topic") or memory_key).strip()
            elif memory_type == "item_method_preference":
                memory_key = str(value.get("item_type") or memory_key).strip()
            normalized_items.append(
                {
                    "memory_type": memory_type,
                    "memory_key": memory_key,
                    "value": value,
                }
            )
    return normalized_items


def _heuristic_fallback_extract(normalized: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    if any(phrase in normalized for phrase in ("more concise", "be concise", "concisely")):
        candidates.append(
            {
                "memory_type": "response_style",
                "memory_key": "response_style",
                "value": {"value": "concise"},
            }
        )
    elif any(
        phrase in normalized
        for phrase in (
            "more detailed",
            "be detailed",
            "longer answers",
            "longer response",
            "answer in detail",
        )
    ):
        candidates.append(
            {
                "memory_type": "response_style",
                "memory_key": "response_style",
                "value": {"value": "detailed"},
            }
        )

    if "don't use my location" in normalized or "do not use my location" in normalized:
        candidates.append(
            {
                "memory_type": "recycling_preference",
                "memory_key": "prefer_nearby_options",
                "value": {"value": False},
            }
        )

    if "manual area" in normalized:
        candidates.append(
            {
                "memory_type": "recycling_preference",
                "memory_key": "allow_manual_area_input",
                "value": {"value": True},
            }
        )

    if "battery" in normalized and "specialized" in normalized:
        candidates.append(
            {
                "memory_type": "item_method_preference",
                "memory_key": "battery",
                "value": {
                    "item_type": "battery",
                    "preferred_method": "specialized_dropoff",
                },
            }
        )

    return candidates


def _merge_with_fallback(
    candidates: list[dict[str, Any]],
    fallback_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}

    for candidate in candidates:
        merged[(candidate["memory_type"], candidate["memory_key"])] = candidate

    for candidate in fallback_candidates:
        merged[(candidate["memory_type"], candidate["memory_key"])] = candidate

    return list(merged.values())


def _memory_extractor_system_prompt() -> str:
    return """
You are CarbonSnap's long-term memory extractor.
Only extract stable user preferences that are explicitly stated in the CURRENT user message.
Use recent_history only to clarify meaning, never to invent a preference that the current message did not clearly express.

Return exactly one JSON object with:
- is_explicit_preference: boolean
- memory_candidates: array

Each memory candidate object must include:
- memory_type: one of response_style, recycling_preference, topic_interest, item_method_preference
- memory_key: string
- value: object

Rules:
- If there is no explicit stable preference, return {"is_explicit_preference": false, "memory_candidates": []}
- response_style values should usually be concise or detailed
- recycling_preference examples: prefer_nearby_options, allow_manual_area_input
- topic_interest value should look like {"topic":"battery"}
- item_method_preference value should look like {"item_type":"battery","preferred_method":"specialized_dropoff"}
- Return JSON only.
""".strip()
