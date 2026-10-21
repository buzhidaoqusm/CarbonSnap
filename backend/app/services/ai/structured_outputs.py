"""The reply shapes of the four JSON calls on the chat decision path.

Each is sent to the provider as a strict JSON Schema (see app/llm/structured)
and validated on return; the callers' normalizers then apply business rules
(clamping confidence, dropping blank options) to an object of known shape.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Intent = Literal["general_chat", "recycling_analysis", "recycling_follow_up"]
FollowUpType = Literal["guidance_follow_up", "nearby_search", "task_verification"]
MemoryType = Literal[
    "response_style", "recycling_preference", "topic_interest", "item_method_preference"
]


class _Strict(BaseModel):
    # additionalProperties: false, which strict mode requires.
    model_config = ConfigDict(extra="forbid")


class ClarificationOption(_Strict):
    label: str
    reply_text: str


class RouterDecision(_Strict):
    intent: Intent
    follow_up_type: FollowUpType | None
    confidence: float
    possible_preference_signal: bool
    needs_clarification: bool
    clarification_question: str | None
    clarification_options: list[ClarificationOption]


class CaseResolution(_Strict):
    target_case_id: int | None
    confidence: float
    needs_clarification: bool
    clarification_question: str | None
    clarification_options: list[ClarificationOption]


class MemoryCandidate(_Strict):
    """One preference, with a field per kind of value.

    The prompt once asked for a free-form ``value`` object; the model chose
    its own keys ({"style": "concise"}) and memory_service, which reads
    {"value": "concise"}, never saw the preference. Named fields leave no
    such choice; ``memory_value`` builds what memory_service reads.
    """

    memory_type: MemoryType
    memory_key: str
    style: Literal["concise", "detailed"] | None
    enabled: bool | None
    topic: str | None
    item_type: str | None
    preferred_method: str | None


class MemoryExtraction(_Strict):
    is_explicit_preference: bool
    memory_candidates: list[MemoryCandidate]


def memory_value(candidate: dict[str, Any]) -> dict[str, Any] | None:
    """The stored value for a candidate, or None if its field is missing."""
    kind = candidate["memory_type"]
    if kind == "response_style":
        return {"value": candidate["style"]} if candidate["style"] else None
    if kind == "recycling_preference":
        return {"value": candidate["enabled"]} if candidate["enabled"] is not None else None
    if kind == "topic_interest":
        return {"topic": candidate["topic"]} if candidate["topic"] else None
    if candidate["item_type"] and candidate["preferred_method"]:
        return {
            "item_type": candidate["item_type"],
            "preferred_method": candidate["preferred_method"],
        }
    return None


class ForumReference(_Strict):
    title: str
    url: str


class StageOneAnalysis(_Strict):
    waste_type: str
    confidence: float
    estimated_weight_kg: float
    recycle_suggestions: list[str]
    needs_nearby_search: bool
    forum_references: list[ForumReference]
