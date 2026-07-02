from __future__ import annotations

from copy import deepcopy
from typing import Any


PROMPTS: dict[str, dict[str, Any]] = {
    "router": {
        "name": "router",
        "version": "router-v1",
        "purpose": "Classify the current user message for CarbonSnap AI routing.",
        "input_schema": {
            "message": "string",
            "image_data_url": "string|null",
            "recent_history": "array",
            "case_summaries": "array",
            "conversation_state": "object",
            "prompt_memory": "object",
        },
        "output_schema": {
            "intent": "general_chat|recycling_analysis|recycling_follow_up",
            "follow_up_type": "guidance_follow_up|nearby_search|task_verification|null",
            "confidence": "number",
            "needs_clarification": "boolean",
        },
        "safety_notes": "The router must classify only; it must not answer the user or execute tools.",
    },
    "general_chat_answer": {
        "name": "general_chat_answer",
        "version": "general-chat-answer-v1",
        "purpose": "Generate normal assistant replies using short-term memory and optional forum evidence.",
        "input_schema": {
            "message": "string",
            "history": "array",
            "system_prompt": "string|null",
            "prompt_memory": "object",
            "forum_candidates": "array",
        },
        "output_schema": {
            "reply": "string",
            "forum_references": "array",
        },
        "safety_notes": "Use forum evidence only when grounded in provided citations; do not invent links.",
    },
    "recycling_analysis_stage1": {
        "name": "recycling_analysis_stage1",
        "version": "recycling-analysis-stage1-v1",
        "purpose": "Analyze a recycling item from user text and optional image context.",
        "input_schema": {
            "message": "string",
            "image_data_url": "string|null",
            "forum_candidates": "array",
            "prompt_memory": "object",
        },
        "output_schema": {
            "waste_type": "string",
            "confidence": "number",
            "recycle_suggestions": "array",
            "forum_references": "array",
        },
        "safety_notes": "Return structured JSON and cite only supplied forum references.",
    },
    "recycling_follow_up": {
        "name": "recycling_follow_up",
        "version": "recycling-follow-up-v1",
        "purpose": "Answer follow-up questions for an existing recycling case.",
        "input_schema": {
            "message": "string",
            "case_context": "object",
            "runtime_context": "object",
            "forum_candidates": "array",
        },
        "output_schema": {
            "reply": "string",
            "forum_references": "array",
        },
        "safety_notes": "Use only the active case context and provided sources; do not fabricate locations.",
    },
}


def get_prompt_definition(name: str) -> dict[str, Any]:
    normalized_name = str(name or "").strip()
    if normalized_name not in PROMPTS:
        raise KeyError(f"Unknown prompt: {name}")
    return deepcopy(PROMPTS[normalized_name])


def get_prompt_version(name: str) -> str:
    return str(get_prompt_definition(name)["version"])


def list_prompt_definitions() -> list[dict[str, Any]]:
    return [get_prompt_definition(name) for name in sorted(PROMPTS)]
