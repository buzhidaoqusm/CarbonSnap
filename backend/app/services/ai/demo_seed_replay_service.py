from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

from flask import current_app

from app.extensions.db import db
from app.models.ai import RecyclingCase
from app.repositories.ai import conversation_repository
from app.repositories.ai import recycling_case_repository
from app.repositories.ledger import ledger_repository
from app.services.ai.image_storage_service import store_data_url_image
from app.services.ai.memory_service import upsert_memory_item
from app.services.ai.recycling_session_service import (
    clear_paused_context,
    create_or_get_session,
    get_paused_context,
    serialize_session,
    set_paused_context,
    set_workflow_reference,
)


_DATA_URL_PATTERN = re.compile(r"^data:[^,]*;base64,", re.IGNORECASE)
_LOCATION_OPTIONS = [
    {"key": "allow_browser_location", "label": "Allow browser location"},
    {"key": "enter_manual_area", "label": "Enter area manually"},
    {"key": "skip_nearby_search", "label": "Skip nearby search"},
]
_NEARBY_POSITIVE_HINTS = (
    "nearby",
    "drop-off",
    "dropoff",
    "near me",
)


@dataclass(frozen=True)
class SeedMessage:
    seed_key: str
    conversation_ref: str
    role: str
    message_type: str
    content_text: str
    content_json: dict[str, Any]
    sequence_no: int


@dataclass(frozen=True)
class SeedReplayMatch:
    user_message: SeedMessage
    assistant_messages: tuple[SeedMessage, ...]


@dataclass(frozen=True)
class SeedAuditReplayMatch:
    user_message: SeedMessage
    assistant_message: SeedMessage


def get_seed_demo_replay_stream(
    *,
    user_id: int | None,
    message: str,
    image_data_url: str | None,
    conversation_id: int | None,
) -> Generator[dict[str, Any], None, None] | None:
    if not current_app.config.get("AI_DEMO_REPLAY_ENABLED"):
        return None

    match = find_seed_replay_match(message=message, image_data_url=image_data_url)
    if match is None:
        return None

    return stream_seed_demo_replay(
        user_id=user_id,
        message=message,
        image_data_url=image_data_url,
        conversation_id=conversation_id,
        match=match,
    )


def find_seed_replay_match(
    *,
    message: str,
    image_data_url: str | None,
) -> SeedReplayMatch | None:
    image_hash = _hash_data_url_image(image_data_url)
    normalized_message = _normalize_message_text(message)

    for candidate in _load_seed_replay_candidates():
        seed_image_url = str(candidate.user_message.content_json.get("image_url") or "")
        has_seed_image = bool(seed_image_url)

        if image_hash:
            seed_image_path = _seed_asset_path_from_upload_url(seed_image_url)
            if not has_seed_image or seed_image_path is None or not seed_image_path.is_file():
                continue
            if _hash_file(seed_image_path) != image_hash:
                continue
        elif has_seed_image:
            continue

        if _normalize_message_text(candidate.user_message.content_text) == normalized_message:
            return candidate

    return None


def stream_seed_demo_replay(
    *,
    user_id: int | None,
    message: str,
    image_data_url: str | None,
    conversation_id: int | None,
    match: SeedReplayMatch,
) -> Generator[dict[str, Any], None, None]:
    conversation = None
    user_message = None
    case_id_by_seed_key: dict[str, int] = {}
    seed_memory_updates = _first_seed_memory_updates(match)
    persisted_memory_updates: list[dict[str, Any]] = []

    if user_id is not None:
        if conversation_id is None:
            conversation = conversation_repository.create_conversation(
                user_id=user_id,
                title=_title_from_conversation_seed(match.user_message.conversation_ref),
            )
        else:
            conversation = conversation_repository.get_conversation(conversation_id, user_id)
            if conversation is None:
                raise ValueError(f"Conversation {conversation_id} not found.")

        stored_image_url = store_data_url_image(image_data_url, namespace="chat") if image_data_url else None
        user_message = conversation_repository.append_message(
            conversation_id=conversation.id,
            role="user",
            message_type="image" if image_data_url else "text",
            content_text=message,
            content_json=json.dumps(
                {
                    "has_image": bool(image_data_url),
                    "image_url": stored_image_url,
                    "demo_replay": True,
                    "demo_seed_message_key": match.user_message.seed_key,
                },
                ensure_ascii=False,
            ),
        )
        persisted_memory_updates = _persist_seed_memory_updates(
            user_id=user_id,
            conversation_id=conversation.id,
            source_message_id=user_message.id,
            user_message=message,
            seed_memory_updates=seed_memory_updates,
        )

    memory_updates = persisted_memory_updates or seed_memory_updates

    yield {
        "type": "meta",
        "conversation_id": conversation.id if conversation is not None else conversation_id,
        "conversation_title": conversation.title if conversation is not None else None,
        "user_message_id": user_message.id if user_message is not None else None,
        "memory_updates": memory_updates,
        "demo_replay": True,
        "demo_seed_message_key": match.user_message.seed_key,
    }

    final_stage = "completed"
    for index, assistant_seed in enumerate(match.assistant_messages):
        content_json = _replace_seed_refs(
            assistant_seed.content_json,
            user_id=user_id,
            conversation_id=conversation.id if conversation is not None else None,
            origin_message_id=user_message.id if user_message is not None else None,
            case_id_by_seed_key=case_id_by_seed_key,
        )
        if memory_updates and isinstance(content_json.get("memory_updates"), list):
            content_json["memory_updates"] = memory_updates
        assistant_message = None
        if conversation is not None:
            assistant_message = conversation_repository.append_message(
                conversation_id=conversation.id,
                role="assistant",
                message_type=assistant_seed.message_type,
                content_text=assistant_seed.content_text,
                content_json=json.dumps(
                    {
                        **content_json,
                        "demo_replay": True,
                        "demo_seed_message_key": assistant_seed.seed_key,
                    },
                    ensure_ascii=False,
                ),
            )

        stream_stage = str(content_json.get("stream_stage") or "")
        if assistant_seed.message_type == "analysis_result":
            yield from _stream_analysis_seed_message(
                seed_message=assistant_seed,
                content_json=content_json,
                conversation_id=conversation.id if conversation is not None else None,
                user_message_id=user_message.id if user_message is not None else None,
                assistant_message_id=assistant_message.id if assistant_message is not None else None,
                remaining_assistant_messages=match.assistant_messages[index + 1 :],
            )
            if _analysis_requires_location(content_json):
                yield from _stream_awaiting_location(
                    content_json=content_json,
                    message=message,
                    conversation_id=conversation.id if conversation is not None else None,
                    user_message_id=user_message.id if user_message is not None else None,
                    remaining_assistant_messages=match.assistant_messages[index + 1 :],
                )
                return
            final_stage = "analysis"
            continue

        if assistant_seed.message_type == "tool_result" and stream_stage == "nearby_search":
            yield from _stream_nearby_seed_message(
                seed_message=assistant_seed,
                content_json=content_json,
                include_stage_start=False,
                suppress_completion_audit=True,
            )
            final_stage = "completed"
            continue

        if stream_stage == "clarification":
            if assistant_message is not None:
                yield {
                    "type": "meta",
                    "conversation_id": conversation.id if conversation is not None else None,
                    "assistant_message_id": assistant_message.id,
                    "demo_replay": True,
                }
            yield _clarification_event_from_seed(assistant_seed, content_json)
            yield {"type": "done", "stream_stage": "clarification"}
            return

        yield from _stream_text_as_deltas(assistant_seed.content_text, stage=stream_stage or assistant_seed.message_type)
        final_stage = "completed"

    if conversation is not None:
        conversation_repository.update_conversation_state(
            conversation.id,
            status="completed" if final_stage == "completed" else "active",
            current_pending_action="none",
        )

    yield {"type": "done", "stream_stage": "completed" if final_stage == "completed" else final_stage}


def complete_seed_demo_replay(
    *,
    user_id: int | None,
    message: str,
    image_data_url: str | None,
    conversation_id: int | None,
) -> dict[str, Any] | None:
    stream = get_seed_demo_replay_stream(
        user_id=user_id,
        message=message,
        image_data_url=image_data_url,
        conversation_id=conversation_id,
    )
    if stream is None:
        return None

    reply_parts: list[str] = []
    meta: dict[str, Any] = {}
    final_stage = "completed"
    for event in stream:
        if event.get("type") == "meta":
            meta = event
        elif event.get("type") == "delta":
            reply_parts.append(str(event.get("content", "")))
        elif event.get("type") == "done":
            final_stage = str(event.get("stream_stage") or "completed")

    return {
        "reply": "".join(reply_parts).strip(),
        "model": None,
        "usage": {},
        "conversation_id": meta.get("conversation_id"),
        "conversation_title": meta.get("conversation_title"),
        "user_message_id": meta.get("user_message_id"),
        "assistant_message_id": None,
        "memory_updates": meta.get("memory_updates") or [],
        "stream_stage": final_stage,
        "demo_replay": True,
    }


def get_seed_demo_resume_stream(session_id: str) -> Generator[dict[str, Any], None, None] | None:
    if not current_app.config.get("AI_DEMO_REPLAY_ENABLED"):
        return None

    paused_context = get_paused_context(session_id)
    if not paused_context or not paused_context.get("demo_replay"):
        return None

    seed_keys = paused_context.get("demo_remaining_assistant_seed_keys") or []
    seed_messages = [_load_seed_message_by_key(str(seed_key)) for seed_key in seed_keys]
    remaining_messages = [message for message in seed_messages if message is not None]
    if not remaining_messages:
        return None

    return stream_seed_demo_resume(
        session_id=session_id,
        paused_context=paused_context,
        assistant_messages=remaining_messages,
    )


def stream_seed_demo_resume(
    *,
    session_id: str,
    paused_context: dict[str, Any],
    assistant_messages: list[SeedMessage],
) -> Generator[dict[str, Any], None, None]:
    conversation_id = paused_context.get("conversation_id")
    recycling_case_id = paused_context.get("recycling_case_id")
    case_id_by_seed_key = {
        _seed_key_from_ref(paused_context.get("demo_recycling_case_ref") or ""): recycling_case_id
    }

    yield {
        "type": "meta",
        "session_id": session_id,
        "conversation_id": conversation_id,
        "demo_replay": True,
    }

    for assistant_seed in assistant_messages:
        content_json = _replace_seed_refs(
            assistant_seed.content_json,
            user_id=None,
            conversation_id=conversation_id,
            origin_message_id=None,
            case_id_by_seed_key=case_id_by_seed_key,
        )
        if recycling_case_id is not None:
            content_json["recycling_case_id"] = recycling_case_id

        assistant_message = None
        if conversation_id is not None:
            assistant_message = conversation_repository.append_message(
                conversation_id=int(conversation_id),
                role="assistant",
                message_type=assistant_seed.message_type,
                content_text=assistant_seed.content_text,
                content_json=json.dumps(
                    {
                        **content_json,
                        "demo_replay": True,
                        "demo_seed_message_key": assistant_seed.seed_key,
                    },
                    ensure_ascii=False,
                ),
            )

        if assistant_seed.message_type == "tool_result" and content_json.get("stream_stage") == "nearby_search":
            yield from _stream_nearby_seed_message(
                seed_message=assistant_seed,
                content_json=content_json,
                include_stage_start=True,
                suppress_completion_audit=False,
            )
        else:
            yield from _stream_text_as_deltas(
                assistant_seed.content_text,
                stage=str(content_json.get("stream_stage") or assistant_seed.message_type),
            )

        if assistant_message is not None:
            yield {
                "type": "meta",
                "conversation_id": conversation_id,
                "assistant_message_id": assistant_message.id,
                "demo_replay": True,
            }

    cleared_session = clear_paused_context(session_id)
    if conversation_id is not None:
        conversation_repository.update_conversation_state(
            int(conversation_id),
            status="completed",
            current_pending_action="none",
            session_context_json=json.dumps(serialize_session(cleared_session), ensure_ascii=False),
        )
    yield {"type": "done", "stream_stage": "completed"}


def get_seed_demo_audit_stream(
    *,
    user_id: int,
    conversation_id: int,
    case: RecyclingCase,
    message: str,
    image_data_url: str,
) -> Generator[dict[str, Any], None, None] | None:
    if not current_app.config.get("AI_DEMO_REPLAY_ENABLED"):
        return None

    seed_case_ref = _seed_case_ref_for_replayed_case(
        conversation_id=conversation_id,
        recycling_case_id=case.id,
    )
    if not seed_case_ref:
        return None

    match = _find_seed_audit_replay_match(
        seed_case_ref=seed_case_ref,
        message=message,
        image_data_url=image_data_url,
    )
    if match is None:
        return None

    return stream_seed_demo_audit(
        user_id=user_id,
        conversation_id=conversation_id,
        case=case,
        message=message,
        image_data_url=image_data_url,
        match=match,
    )


def stream_seed_demo_audit(
    *,
    user_id: int,
    conversation_id: int,
    case: RecyclingCase,
    message: str,
    image_data_url: str,
    match: SeedAuditReplayMatch,
) -> Generator[dict[str, Any], None, None]:
    stored_image_url = store_data_url_image(image_data_url, namespace="recycling-audit")
    user_message = conversation_repository.append_message(
        conversation_id=conversation_id,
        role="user",
        message_type="image",
        content_text=message or "Completion photo uploaded.",
        content_json=json.dumps(
            {
                "purpose": "completion_audit",
                "image_url": stored_image_url,
                "recycling_case_id": case.id,
                "demo_replay": True,
                "demo_seed_message_key": match.user_message.seed_key,
            },
            ensure_ascii=False,
        ),
    )

    yield {
        "type": "meta",
        "conversation_id": conversation_id,
        "recycling_case_id": case.id,
        "user_message_id": user_message.id,
        "demo_replay": True,
        "demo_seed_message_key": match.user_message.seed_key,
    }
    yield {"type": "stage_start", "stage": "audit"}

    seed_payload = json.loads(json.dumps(match.assistant_message.content_json))
    audit_payload = dict(seed_payload.get("audit_result") or {})
    audit_attempt = recycling_case_repository.create_audit_attempt(
        recycling_case_id=case.id,
        user_id=user_id,
        conversation_id=conversation_id,
        audit_image_url=stored_image_url,
        audit_result=str(audit_payload.get("audit_result") or "unclear"),
        auditor_confidence=float(audit_payload.get("auditor_confidence") or 0.0),
        audit_reason=str(audit_payload.get("audit_reason") or ""),
        audit_response_json=json.dumps(
            {
                **audit_payload,
                "case_summary": _case_summary(case),
                "demo_replay": True,
            },
            ensure_ascii=False,
        ),
    )
    serialized_attempt = _serialize_audit_attempt(audit_attempt)

    finalized_record_id = None
    transaction_id = None
    user_points = seed_payload.get("user_points")
    user_carbon_amount = seed_payload.get("user_carbon_amount")
    finalized = bool(seed_payload.get("finalized"))

    if finalized and audit_attempt.audit_result == "passed":
        record, transaction, user = ledger_repository.finalize_approved_recycling_case_and_earn(
            user_id=user_id,
            conversation_id=conversation_id,
            recycling_case_id=case.id,
            approved_audit_attempt_id=audit_attempt.id,
            image_url=stored_image_url,
            waste_type=case.waste_type_predicted,
            confidence=case.confidence,
            estimated_weight_kg=case.estimated_weight_kg,
            co2_saved_kg=case.expected_co2_saved_kg,
            carbon_points=int(round(case.expected_carbon_points)),
            raw_ai_response_json=json.dumps(
                {
                    **audit_payload,
                    "case_summary": _case_summary(case),
                    "finalized": True,
                    "demo_replay": True,
                },
                ensure_ascii=False,
            ),
        )
        finalized_record_id = record.id
        transaction_id = transaction.id
        user_points = user.current_points
        user_carbon_amount = user.total_carbon_amount

    assistant_payload = {
        "audit_result": audit_payload,
        "audit_attempt": serialized_attempt,
        "finalized": finalized,
        "recycling_case_id": case.id,
        "analysis_record_id": finalized_record_id,
        "transaction_id": transaction_id,
        "user_points": user_points,
        "user_carbon_amount": user_carbon_amount,
        "demo_replay": True,
        "demo_seed_message_key": match.assistant_message.seed_key,
    }
    if not finalized:
        assistant_payload["retryable"] = True

    assistant_message = conversation_repository.append_message(
        conversation_id=conversation_id,
        role="assistant",
        message_type="audit_result",
        content_text=match.assistant_message.content_text,
        content_json=json.dumps(assistant_payload, ensure_ascii=False),
        related_analysis_id=finalized_record_id,
    )
    conversation_repository.update_conversation_state(
        conversation_id,
        status="completed" if finalized else "active",
        current_pending_action="none",
    )

    yield {
        "type": "stage_payload",
        "stage": "finalize" if finalized else "audit",
        "data": {
            **assistant_payload,
            "assistant_message_id": assistant_message.id,
            "audit_attempt_id": audit_attempt.id,
            "conversation_id": conversation_id,
        },
    }
    yield {"type": "done", "stream_stage": "finalized" if finalized else "audit"}


def _stream_analysis_seed_message(
    *,
    seed_message: SeedMessage,
    content_json: dict[str, Any],
    conversation_id: int | None,
    user_message_id: int | None,
    assistant_message_id: int | None,
    remaining_assistant_messages: tuple[SeedMessage, ...],
) -> Generator[dict[str, Any], None, None]:
    yield {"type": "stage_start", "stage": "analysis"}
    analysis_payload = dict(content_json.get("analysis_payload") or {})
    recycling_case_id = content_json.get("recycling_case_id")
    yield {
        "type": "stage_payload",
        "stage": "analysis",
        "data": {
            **analysis_payload,
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
            "recycling_case_id": recycling_case_id,
            "stream_stage": "analysis",
        },
    }
    yield from _stream_text_as_deltas(seed_message.content_text, stage="analysis")


def _stream_nearby_seed_message(
    *,
    seed_message: SeedMessage,
    content_json: dict[str, Any],
    include_stage_start: bool,
    suppress_completion_audit: bool,
) -> Generator[dict[str, Any], None, None]:
    if include_stage_start:
        yield {"type": "stage_start", "stage": "nearby_search"}
    payload = {
        **dict(content_json.get("analysis_payload") or {}),
        "nearby_locations": content_json.get("nearby_locations") or [],
        "location_state": content_json.get("location_state"),
        "recycling_case_id": content_json.get("recycling_case_id"),
        "suppress_completion_audit": suppress_completion_audit,
        "stream_stage": "completed",
    }
    yield {"type": "nearby_results", "data": payload}
    yield from _stream_text_as_deltas(seed_message.content_text, stage="nearby_search")


def _stream_awaiting_location(
    *,
    content_json: dict[str, Any],
    message: str,
    conversation_id: int | None,
    user_message_id: int | None,
    remaining_assistant_messages: tuple[SeedMessage, ...],
) -> Generator[dict[str, Any], None, None]:
    session = create_or_get_session(None)
    recycling_case_id = content_json.get("recycling_case_id")
    session = set_workflow_reference(
        session["session_id"],
        conversation_id=conversation_id,
        recycling_case_id=recycling_case_id,
    )
    session = set_paused_context(
        session["session_id"],
        {
            "analysis_payload": content_json.get("analysis_payload") or {},
            "original_prompt": message,
            "conversation_id": conversation_id,
            "recycling_case_id": recycling_case_id,
            "user_message_id": user_message_id,
            "demo_replay": True,
            "demo_recycling_case_ref": content_json.get("demo_recycling_case_ref"),
            "demo_remaining_assistant_seed_keys": [
                message.seed_key for message in remaining_assistant_messages
            ],
        },
    )
    if conversation_id is not None:
        conversation_repository.update_conversation_state(
            conversation_id,
            status="awaiting_location",
            current_pending_action="location_permission",
            session_context_json=json.dumps(serialize_session(session), ensure_ascii=False),
        )

    analysis_payload = content_json.get("analysis_payload") if isinstance(content_json.get("analysis_payload"), dict) else {}
    yield {
        "type": "awaiting_location",
        "data": {
            "requires_location_decision": True,
            "stream_stage": "awaiting_location",
            "location_options": analysis_payload.get("location_options") or _LOCATION_OPTIONS,
            "session_id": session["session_id"],
            "permission_state": "unknown",
            "recycling_case_id": recycling_case_id,
        },
    }
    yield {"type": "done", "stream_stage": "awaiting_location"}


def _stream_text_as_deltas(text: str, *, stage: str) -> Generator[dict[str, Any], None, None]:
    chunk_size = int(current_app.config.get("AI_DEMO_REPLAY_CHUNK_SIZE", 120) or 120)
    for index in range(0, len(text), chunk_size):
        yield {
            "type": "delta",
            "stage": stage,
            "content": text[index : index + chunk_size],
        }


def _clarification_event_from_seed(seed_message: SeedMessage, content_json: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "clarification",
        "data": {
            "question": seed_message.content_text
            or "Could you clarify which recycling task you mean?",
            "options": content_json.get("clarification_options") or [],
        },
    }


def _first_seed_memory_updates(match: SeedReplayMatch) -> list[dict[str, Any]]:
    for message in match.assistant_messages:
        updates = message.content_json.get("memory_updates")
        if isinstance(updates, list):
            return [
                {
                    "id": item.get("id"),
                    "memory_type": str(item.get("memory_type") or ""),
                    "memory_key": str(item.get("memory_key") or ""),
                }
                for item in updates
                if isinstance(item, dict)
            ]
    return []


def _build_memory_value_from_seed_update(update: dict[str, Any], user_message: str) -> dict[str, Any] | None:
    memory_type = str(update.get("memory_type") or "").strip()
    memory_key = str(update.get("memory_key") or "").strip()
    normalized = _normalize_message_text(user_message)

    if memory_type == "recycling_preference" and memory_key == "prefer_nearby_options":
        if "don't use my location" in normalized or "do not use my location" in normalized:
            return {"value": False}
        if any(token in normalized for token in _NEARBY_POSITIVE_HINTS):
            return {"value": True}
        # Seed-marked update defaults to enabling nearby preference.
        return {"value": True}

    if memory_type == "recycling_preference" and memory_key == "allow_manual_area_input":
        return {"value": True}

    if memory_type == "response_style" and memory_key == "response_style":
        if any(phrase in normalized for phrase in ("more concise", "be concise", "concisely")):
            return {"value": "concise"}
        if any(
            phrase in normalized
            for phrase in ("more detailed", "be detailed", "longer answers", "answer in detail")
        ):
            return {"value": "detailed"}

    return None


def _persist_seed_memory_updates(
    *,
    user_id: int,
    conversation_id: int,
    source_message_id: int,
    user_message: str,
    seed_memory_updates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not seed_memory_updates:
        return []

    persisted: list[dict[str, Any]] = []
    for update in seed_memory_updates:
        value = _build_memory_value_from_seed_update(update, user_message)
        if not isinstance(value, dict) or not value:
            continue

        memory_type = str(update.get("memory_type") or "").strip()
        memory_key = str(update.get("memory_key") or "").strip()
        if not memory_type or not memory_key:
            continue

        try:
            item = upsert_memory_item(
                user_id=user_id,
                memory_type=memory_type,
                memory_key=memory_key,
                value=value,
                source_type="explicit_chat",
                source_message_id=source_message_id,
                conversation_id=conversation_id,
            )
        except Exception:
            continue

        persisted.append(
            {
                "id": item.id,
                "memory_type": item.memory_type,
                "memory_key": item.memory_key,
            }
        )

    return persisted


def _analysis_requires_location(content_json: dict[str, Any]) -> bool:
    analysis_payload = content_json.get("analysis_payload")
    if not isinstance(analysis_payload, dict):
        return False
    return bool(analysis_payload.get("requires_location_decision"))


def _seed_case_ref_for_replayed_case(*, conversation_id: int, recycling_case_id: int) -> str | None:
    for message in conversation_repository.list_messages(conversation_id):
        if message.role != "assistant":
            continue
        try:
            payload = json.loads(message.content_json or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if int(payload.get("recycling_case_id") or 0) == recycling_case_id and payload.get("demo_recycling_case_ref"):
            return str(payload["demo_recycling_case_ref"])
    return None


def _find_seed_audit_replay_match(
    *,
    seed_case_ref: str,
    message: str,
    image_data_url: str,
) -> SeedAuditReplayMatch | None:
    image_hash = _hash_data_url_image(image_data_url)
    if not image_hash:
        return None

    normalized_message = _normalize_message_text(message)
    fallback_match: SeedAuditReplayMatch | None = None
    messages = _load_seed_messages()
    by_conversation: dict[str, list[SeedMessage]] = {}
    for seed_message in messages:
        by_conversation.setdefault(seed_message.conversation_ref, []).append(seed_message)

    for conversation_messages in by_conversation.values():
        ordered = sorted(conversation_messages, key=lambda item: item.sequence_no)
        for index, seed_message in enumerate(ordered):
            if seed_message.role != "user":
                continue
            if seed_message.content_json.get("purpose") != "completion_audit":
                continue
            if seed_message.content_json.get("recycling_case_ref") != seed_case_ref:
                continue
            seed_image_path = _seed_asset_path_from_upload_url(str(seed_message.content_json.get("image_url") or ""))
            if seed_image_path is None or not seed_image_path.is_file() or _hash_file(seed_image_path) != image_hash:
                continue
            for following in ordered[index + 1 :]:
                if following.role == "user":
                    break
                if following.role == "assistant" and following.message_type == "audit_result":
                    match = SeedAuditReplayMatch(seed_message, following)
                    if _normalize_message_text(seed_message.content_text) == normalized_message:
                        return match
                    if fallback_match is None:
                        fallback_match = match
                    break
    return fallback_match


def _case_summary(case: RecyclingCase) -> dict[str, Any]:
    return {
        "id": case.id,
        "waste_type_predicted": case.waste_type_predicted,
        "confidence": case.confidence,
        "estimated_weight_kg": case.estimated_weight_kg,
        "expected_co2_saved_kg": case.expected_co2_saved_kg,
        "expected_carbon_points": case.expected_carbon_points,
        "status": case.status,
    }


def _serialize_audit_attempt(attempt: Any) -> dict[str, Any]:
    return {
        "id": attempt.id,
        "recycling_case_id": attempt.recycling_case_id,
        "attempt_no": attempt.attempt_no,
        "audit_result": attempt.audit_result,
        "auditor_confidence": attempt.auditor_confidence,
        "audit_reason": attempt.audit_reason,
        "audit_image_url": attempt.audit_image_url,
        "created_at": attempt.created_at.isoformat() if attempt.created_at else None,
    }


def _replace_seed_refs(
    content_json: dict[str, Any],
    *,
    user_id: int | None,
    conversation_id: int | None,
    origin_message_id: int | None,
    case_id_by_seed_key: dict[str, int],
) -> dict[str, Any]:
    payload = json.loads(json.dumps(content_json))
    case_ref = payload.pop("recycling_case_ref", None)
    if case_ref:
        payload["demo_recycling_case_ref"] = case_ref
        case_id = case_id_by_seed_key.get(_seed_key_from_ref(case_ref))
        if case_id is None and user_id is not None and conversation_id is not None and origin_message_id is not None:
            case = _create_case_from_seed_ref(
                case_ref,
                user_id=user_id,
                conversation_id=conversation_id,
                origin_message_id=origin_message_id,
            )
            if case is not None:
                case_id = case.id
                case_id_by_seed_key[_seed_key_from_ref(case_ref)] = case_id
        if case_id is not None:
            payload["recycling_case_id"] = case_id

    return payload


def _create_case_from_seed_ref(
    case_ref: str,
    *,
    user_id: int,
    conversation_id: int,
    origin_message_id: int,
) -> RecyclingCase | None:
    seed_key = _seed_key_from_ref(case_ref)
    seed_case = _load_seed_json("recycling_cases", f"{seed_key}.json")
    if not seed_case:
        return None

    case = RecyclingCase(
        user_id=user_id,
        conversation_id=conversation_id,
        origin_message_id=origin_message_id,
        waste_type_predicted=str(seed_case.get("waste_type_predicted") or "unknown"),
        confidence=float(seed_case.get("confidence") or 0.0),
        estimated_weight_kg=float(seed_case.get("estimated_weight_kg") or 0.0),
        expected_co2_saved_kg=float(seed_case.get("expected_co2_saved_kg") or 0.0),
        expected_carbon_points=float(seed_case.get("expected_carbon_points") or 0.0),
        status="pending_audit",
        latest_audit_attempt_no=0,
    )
    db.session.add(case)
    db.session.commit()
    return case


def _load_seed_replay_candidates() -> tuple[SeedReplayMatch, ...]:
    messages = _load_seed_messages()
    by_conversation: dict[str, list[SeedMessage]] = {}
    for message in messages:
        by_conversation.setdefault(message.conversation_ref, []).append(message)

    candidates: list[SeedReplayMatch] = []
    for conversation_messages in by_conversation.values():
        ordered = sorted(conversation_messages, key=lambda item: item.sequence_no)
        for index, message in enumerate(ordered):
            if message.role != "user":
                continue
            assistant_messages: list[SeedMessage] = []
            for following in ordered[index + 1 :]:
                if following.role == "user":
                    break
                if following.role == "assistant":
                    assistant_messages.append(following)
            if assistant_messages:
                candidates.append(SeedReplayMatch(message, tuple(assistant_messages)))
    return tuple(candidates)


def _load_seed_messages() -> tuple[SeedMessage, ...]:
    messages_root = _seeds_root() / "ai_messages"
    loaded: list[SeedMessage] = []
    for seed_path in sorted(messages_root.glob("*.json")):
        if seed_path.name == "template.json":
            continue
        payload = json.loads(seed_path.read_text(encoding="utf-8"))
        loaded.append(
            SeedMessage(
                seed_key=str(payload.get("_seed_key") or seed_path.stem),
                conversation_ref=str(payload.get("conversation_ref") or ""),
                role=str(payload.get("role") or ""),
                message_type=str(payload.get("message_type") or "text"),
                content_text=str(payload.get("content_text") or ""),
                content_json=payload.get("content_json") if isinstance(payload.get("content_json"), dict) else {},
                sequence_no=int(payload.get("sequence_no") or 0),
            )
        )
    return tuple(loaded)


def _load_seed_message_by_key(seed_key: str) -> SeedMessage | None:
    for message in _load_seed_messages():
        if message.seed_key == seed_key:
            return message
    return None


def _title_from_conversation_seed(conversation_ref: str) -> str:
    seed_key = _seed_key_from_ref(conversation_ref)
    payload = _load_seed_json("ai_conversations", f"{seed_key}.json")
    return str((payload or {}).get("title") or "Demo replay chat")


def _load_seed_json(folder: str, filename: str) -> dict[str, Any] | None:
    path = _seeds_root() / folder / filename
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _seed_asset_path_from_upload_url(upload_url: str) -> Path | None:
    uploads_prefix = str(current_app.config.get("UPLOAD_URL_PREFIX") or "/api/uploads").rstrip("/")
    if not upload_url.startswith(f"{uploads_prefix}/"):
        return None
    relative_path = upload_url[len(uploads_prefix) + 1 :]
    return _seeds_root() / "assets" / relative_path


def _seeds_root() -> Path:
    return Path(current_app.root_path).resolve().parents[1] / "data" / "seeds"


def _seed_key_from_ref(ref: str) -> str:
    return str(ref).rsplit(".", 1)[-1]


def _normalize_message_text(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _hash_data_url_image(data_url: str | None) -> str | None:
    if not data_url:
        return None
    raw_value = str(data_url).strip()
    try:
        if _DATA_URL_PATTERN.match(raw_value):
            _, encoded = raw_value.split(",", 1)
            return hashlib.sha256(base64.b64decode(encoded, validate=True)).hexdigest()
        if raw_value.startswith("/api/uploads/"):
            return None
    except (ValueError, binascii.Error):
        return None
    return None


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
