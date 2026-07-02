from __future__ import annotations

import json
from typing import Any, Generator

from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.repositories.ai import conversation_repository, recycling_case_repository
from app.repositories.ledger import ledger_repository
from app.services.ai.image_storage_service import store_data_url_image
from app.services.ai.openrouter_service import OpenRouterConfigError, complete_json
from app.services.ai.memory_service import rebuild_user_preferences_summary
from app.services.recommendation import behavior_event_service, preference_profile_service


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


def _build_audit_prompt(message: str, case_summary: dict[str, Any]) -> str:
    return (
        "Audit whether the attached completion photo shows the user's recycling task was completed.\n"
        "Judge both item match and disposal suitability for the case's waste type.\n"
        "Return exactly one JSON object with these fields:\n"
        "- audit_result: one of passed, failed, unclear\n"
        "- auditor_confidence: number between 0 and 1\n"
        "- audit_reason: short explanation\n"
        "Use unclear when the image does not clearly prove completion.\n"
        "Use unclear when the image shows an item in a generic recycling bin but does not clearly show"
        " that the disposal path is appropriate for the case's waste type.\n"
        "Use passed only if the completion is strongly supported by the photo.\n"
        f"User note: {message or 'No extra note provided.'}\n"
        f"Case summary: {json.dumps(case_summary, ensure_ascii=False)}\n"
        "Completion photo: attached"
    )


def _audit_system_prompt() -> str:
    return """
You are CarbonSnap's recycling completion auditor.
Assess only whether the uploaded photo provides enough evidence that the recycling task was completed.
Return exactly one JSON object.

Required JSON fields:
- audit_result: passed, failed, or unclear
- auditor_confidence: number between 0 and 1
- audit_reason: short, user-facing explanation

Rules:
- passed means the photo clearly supports that recycling was completed and that the disposal path is
  appropriate for the case's waste type.
- failed means the photo shows the task was not completed or is inconsistent.
- unclear means the evidence is insufficient.
- For e-waste, batteries, power banks, or similar hazardous/special-drop-off items, an ordinary
  recycling bin is not enough evidence of correct disposal. Return unclear unless the image clearly
  shows an appropriate e-waste or battery collection pathway.
- If the item in the photo does not appear to match the case item, do not return passed.
- Do not include markdown or commentary outside the JSON object.
""".strip()


def _normalize_audit_payload(raw: dict[str, Any]) -> dict[str, Any]:
    audit_result = str(raw.get("audit_result") or "unclear").strip().lower()
    if audit_result not in {"passed", "failed", "unclear"}:
        audit_result = "unclear"

    try:
        auditor_confidence = float(raw.get("auditor_confidence", 0.5))
    except (TypeError, ValueError):
        auditor_confidence = 0.5
    auditor_confidence = max(0.0, min(1.0, auditor_confidence))

    audit_reason = str(raw.get("audit_reason") or "").strip()
    if not audit_reason:
        if audit_result == "passed":
            audit_reason = "The completion photo appears to show the recycling task was completed."
        elif audit_result == "failed":
            audit_reason = "The completion photo does not clearly show a completed recycling task."
        else:
            audit_reason = "The completion photo does not provide enough evidence to verify completion."

    return {
        "audit_result": audit_result,
        "auditor_confidence": round(auditor_confidence, 3),
        "audit_reason": audit_reason,
    }


def _resolve_case_for_audit(
    *,
    user_id: int,
    conversation_id: int,
    recycling_case_id: int | None,
) -> Any:
    conversation = conversation_repository.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found.")

    if recycling_case_id is not None:
        case = recycling_case_repository.get_case(recycling_case_id, user_id)
        if case is None:
            raise ValueError(f"Recycling case {recycling_case_id} not found.")
    else:
        case = recycling_case_repository.get_pending_case_for_conversation(conversation_id)
        if case is None or case.user_id != user_id:
            raise ValueError(
                f"No pending recycling case was found for conversation {conversation_id}."
            )

    if case.conversation_id != conversation_id:
        raise ValueError(
            f"Recycling case {case.id} does not belong to conversation {conversation_id}."
        )
    if case.user_id != user_id:
        raise ValueError(f"Recycling case {case.id} does not belong to user {user_id}.")
    if case.approved_analysis_id is not None or case.status == "audit_passed":
        raise ValueError(f"Recycling case {case.id} has already been finalized.")
    if case.status not in {"pending_audit", "audit_failed"}:
        raise ValueError(f"Recycling case {case.id} is not ready for audit.")

    return case


def _update_conversation_after_audit(
    *,
    conversation_id: int,
    completed: bool,
) -> None:
    conversation_repository.update_conversation_state(
        conversation_id,
        status="completed" if completed else "active",
        current_pending_action="none",
    )


def stream_recycling_audit(
    *,
    conversation_id: int,
    recycling_case_id: int | None,
    message: str,
    image_data_url: str,
) -> Generator[dict[str, Any], None, None]:
    user_id = _get_authenticated_user_id()
    if user_id is None:
        raise ValueError("Authentication is required for recycling audit.")

    case = _resolve_case_for_audit(
        user_id=user_id,
        conversation_id=conversation_id,
        recycling_case_id=recycling_case_id,
    )
    from app.services.ai.demo_seed_replay_service import get_seed_demo_audit_stream

    demo_replay_stream = get_seed_demo_audit_stream(
        user_id=user_id,
        conversation_id=conversation_id,
        case=case,
        message=message,
        image_data_url=image_data_url,
    )
    if demo_replay_stream is not None:
        yield from demo_replay_stream
        return

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
            },
            ensure_ascii=False,
        ),
    )

    yield {
        "type": "meta",
        "conversation_id": conversation_id,
        "recycling_case_id": case.id,
        "user_message_id": user_message.id,
    }
    yield {"type": "stage_start", "stage": "audit"}

    case_summary = {
        "id": case.id,
        "waste_type_predicted": case.waste_type_predicted,
        "confidence": case.confidence,
        "estimated_weight_kg": case.estimated_weight_kg,
        "expected_co2_saved_kg": case.expected_co2_saved_kg,
        "expected_carbon_points": case.expected_carbon_points,
        "status": case.status,
    }

    try:
        raw_audit = complete_json(
            user_message=_build_audit_prompt(message, case_summary),
            image_data_url=image_data_url,
            system_prompt=_audit_system_prompt(),
        )
    except OpenRouterConfigError:
        raise
    except Exception as exc:
        raw_audit = {
            "audit_result": "unclear",
            "auditor_confidence": 0.0,
            "audit_reason": f"Unable to verify completion photo: {exc}",
        }

    audit_payload = _normalize_audit_payload(raw_audit)
    audit_attempt = recycling_case_repository.create_audit_attempt(
        recycling_case_id=case.id,
        user_id=user_id,
        conversation_id=conversation_id,
        audit_image_url=stored_image_url,
        audit_result=audit_payload["audit_result"],
        auditor_confidence=audit_payload["auditor_confidence"],
        audit_reason=audit_payload["audit_reason"],
        audit_response_json=json.dumps(
            {
                **audit_payload,
                "case_summary": case_summary,
            },
            ensure_ascii=False,
        ),
    )
    serialized_attempt = {
        "id": audit_attempt.id,
        "recycling_case_id": audit_attempt.recycling_case_id,
        "attempt_no": audit_attempt.attempt_no,
        "audit_result": audit_attempt.audit_result,
        "auditor_confidence": audit_attempt.auditor_confidence,
        "audit_reason": audit_attempt.audit_reason,
        "audit_image_url": audit_attempt.audit_image_url,
        "created_at": audit_attempt.created_at.isoformat() if audit_attempt.created_at else None,
    }

    finalized_record_id: int | None = None
    if audit_payload["audit_result"] == "passed":
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
                    "case_summary": case_summary,
                    "finalized": True,
                },
                ensure_ascii=False,
            ),
        )
        finalized_record_id = record.id
        try:
            behavior_event_service.record_ai_recycling_case_passed_audit(
                user_id=user_id,
                recycling_case_id=case.id,
            )
            preference_profile_service.recompute_user_preference_profiles(user_id)
        except Exception:
            pass
        rebuild_user_preferences_summary(user_id)
        assistant_text = (
            f"Audit passed. Your recycling case has been verified, and {record.carbon_points} "
            f"points were awarded."
        )
        assistant_payload = {
            "audit_result": audit_payload,
            "audit_attempt": serialized_attempt,
            "finalized": True,
            "recycling_case_id": case.id,
            "analysis_record_id": record.id,
            "transaction_id": transaction.id,
            "user_points": user.current_points,
            "user_carbon_amount": user.total_carbon_amount,
        }
        stream_stage = "finalized"
    else:
        try:
            behavior_event_service.record_ai_recycling_case_failed_audit(
                user_id=user_id,
                recycling_case_id=case.id,
            )
            preference_profile_service.recompute_user_preference_profiles(user_id)
        except Exception:
            pass
        rebuild_user_preferences_summary(user_id)
        assistant_text = f"Audit {audit_payload['audit_result']}. {audit_payload['audit_reason']}"
        assistant_payload = {
            "audit_result": audit_payload,
            "audit_attempt": serialized_attempt,
            "finalized": False,
            "retryable": True,
            "recycling_case_id": case.id,
        }
        stream_stage = "audit"

    assistant_message = conversation_repository.append_message(
        conversation_id=conversation_id,
        role="assistant",
        message_type="audit_result",
        content_text=assistant_text,
        content_json=json.dumps(assistant_payload, ensure_ascii=False),
        related_analysis_id=finalized_record_id,
    )

    _update_conversation_after_audit(
        conversation_id=conversation_id,
        completed=audit_payload["audit_result"] == "passed",
    )

    if audit_payload["audit_result"] == "passed":
        yield {
            "type": "stage_payload",
            "stage": "finalize",
            "data": {
                **assistant_payload,
                "assistant_message_id": assistant_message.id,
                "audit_attempt_id": audit_attempt.id,
                "conversation_id": conversation_id,
            },
        }
        yield {"type": "done", "stream_stage": stream_stage}
        return

    yield {
        "type": "stage_payload",
        "stage": "audit",
        "data": {
            **assistant_payload,
            "assistant_message_id": assistant_message.id,
            "audit_attempt_id": audit_attempt.id,
            "recycling_case_id": case.id,
            "conversation_id": conversation_id,
        },
    }
    yield {"type": "done", "stream_stage": stream_stage}
