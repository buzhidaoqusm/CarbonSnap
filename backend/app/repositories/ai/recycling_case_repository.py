from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai import RecyclingAuditAttempt, RecyclingCase


def _utc_now() -> datetime:
    return datetime.now(UTC)


def create_recycling_case(
    session: Session,
    *,
    user_id: int,
    conversation_id: int,
    origin_message_id: int,
    waste_type_predicted: str,
    confidence: float,
    estimated_weight_kg: float,
    expected_co2_saved_kg: float,
    expected_carbon_points: float,
) -> RecyclingCase:
    recycling_case = RecyclingCase(
        user_id=user_id,
        conversation_id=conversation_id,
        origin_message_id=origin_message_id,
        waste_type_predicted=waste_type_predicted,
        confidence=confidence,
        estimated_weight_kg=estimated_weight_kg,
        expected_co2_saved_kg=expected_co2_saved_kg,
        expected_carbon_points=expected_carbon_points,
    )
    session.add(recycling_case)
    session.commit()
    return recycling_case


def get_pending_case_for_conversation(
    session: Session,
    conversation_id: int,
) -> RecyclingCase | None:
    return session.scalar(
        select(RecyclingCase)
        .where(
            RecyclingCase.conversation_id == conversation_id,
            RecyclingCase.status.in_(("pending_audit", "audit_failed")),
        )
        .order_by(RecyclingCase.created_at.desc(), RecyclingCase.id.desc())
    )


def list_cases_for_conversation(session: Session, conversation_id: int) -> list[RecyclingCase]:
    cases = session.scalars(
        select(RecyclingCase)
        .where(RecyclingCase.conversation_id == conversation_id)
        .order_by(RecyclingCase.created_at.asc(), RecyclingCase.id.asc())
    ).all()
    return list(cases)


def list_cases_for_user(session: Session, user_id: int) -> list[RecyclingCase]:
    cases = session.scalars(
        select(RecyclingCase)
        .where(RecyclingCase.user_id == user_id)
        .order_by(RecyclingCase.created_at.desc(), RecyclingCase.id.desc())
    ).all()
    return list(cases)


def list_active_cases_for_conversation(
    session: Session, conversation_id: int
) -> list[RecyclingCase]:
    cases = session.scalars(
        select(RecyclingCase)
        .where(
            RecyclingCase.conversation_id == conversation_id,
            RecyclingCase.status.in_(("pending_audit", "audit_failed")),
        )
        .order_by(RecyclingCase.updated_at.desc(), RecyclingCase.id.desc())
    ).all()
    return list(cases)


def get_case(session: Session, case_id: int, user_id: int) -> RecyclingCase | None:
    return session.scalar(
        select(RecyclingCase).where(
            RecyclingCase.id == case_id,
            RecyclingCase.user_id == user_id,
        )
    )


def create_audit_attempt(
    session: Session,
    *,
    recycling_case_id: int,
    user_id: int,
    conversation_id: int,
    audit_image_url: str,
    audit_result: str,
    auditor_confidence: float = 0.0,
    audit_reason: str | None = None,
    audit_response_json: str | None = None,
) -> RecyclingAuditAttempt:
    recycling_case = session.get(RecyclingCase, recycling_case_id)
    if recycling_case is None:
        raise ValueError(f"Recycling case {recycling_case_id} not found.")

    next_attempt_no = recycling_case.latest_audit_attempt_no + 1
    attempt = RecyclingAuditAttempt(
        recycling_case_id=recycling_case_id,
        user_id=user_id,
        conversation_id=conversation_id,
        audit_image_url=audit_image_url,
        attempt_no=next_attempt_no,
        audit_result=audit_result,
        auditor_confidence=auditor_confidence,
        audit_reason=audit_reason,
        audit_response_json=audit_response_json,
    )

    recycling_case.latest_audit_attempt_no = next_attempt_no
    if audit_result != "passed":
        recycling_case.status = "audit_failed"
    recycling_case.updated_at = _utc_now()

    session.add(attempt)
    session.commit()
    return attempt


def mark_case_audit_passed(
    session: Session,
    recycling_case_id: int,
    *,
    approved_analysis_id: int | None = None,
) -> RecyclingCase:
    recycling_case = session.get(RecyclingCase, recycling_case_id)
    if recycling_case is None:
        raise ValueError(f"Recycling case {recycling_case_id} not found.")

    recycling_case.status = "audit_passed"
    if approved_analysis_id is not None:
        recycling_case.approved_analysis_id = approved_analysis_id
    recycling_case.updated_at = _utc_now()
    session.commit()
    return recycling_case


def list_audit_attempts(session: Session, recycling_case_id: int) -> list[RecyclingAuditAttempt]:
    attempts = session.scalars(
        select(RecyclingAuditAttempt)
        .where(RecyclingAuditAttempt.recycling_case_id == recycling_case_id)
        .order_by(RecyclingAuditAttempt.attempt_no.asc(), RecyclingAuditAttempt.id.asc())
    ).all()
    return list(attempts)
