"""Focused tests for approved recycling case finalization and ledger writes."""

import importlib
import uuid

import pytest
from sqlalchemy import func, select
from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.ai import AIConversation, AIMessage, RecyclingAuditAttempt, RecyclingCase, WasteAnalysisRecord
from app.models.ledger import Transaction
from app.models.user import User
from app.services.ai import recycling_audit_service

_VALID_IMAGE_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0vcAAAAASUVORK5CYII="
)


ledger_repository = importlib.import_module("app.repositories.ledger.ledger_repository")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(
    username: str = "alice",
    email: str = "alice@example.com",
    *,
    points: int = 0,
    carbon_amount: float = 0.0,
) -> User:
    unique_suffix = uuid.uuid4().hex[:8]
    db.metadata.create_all(bind=db.session.connection())
    user = User(
        username=f"{username}_{unique_suffix}",
        email=f"{unique_suffix}_{email}",
        password_hash=generate_password_hash("password123"),
        current_points=points,
        total_carbon_amount=carbon_amount,
    )
    db.session.add(user)
    db.session.flush()
    return user


def _make_conversation(user: User, title: str = "AI Chat") -> AIConversation:
    conversation = AIConversation(user_id=user.id, title=title)
    db.session.add(conversation)
    db.session.flush()
    return conversation


def _make_origin_message(conversation: AIConversation, text: str = "Please analyze this item.") -> AIMessage:
    message = AIMessage(
        conversation_id=conversation.id,
        role="user",
        message_type="text",
        content_text=text,
        sequence_no=1,
    )
    db.session.add(message)
    db.session.flush()
    return message


def _make_case(
    user: User,
    conversation: AIConversation,
    origin_message: AIMessage,
    *,
    waste_type_predicted: str = "plastic bottle",
    confidence: float = 0.81,
    estimated_weight_kg: float = 0.25,
    expected_co2_saved_kg: float = 0.32,
    expected_carbon_points: float = 4.0,
) -> RecyclingCase:
    case = RecyclingCase(
        user_id=user.id,
        conversation_id=conversation.id,
        origin_message_id=origin_message.id,
        waste_type_predicted=waste_type_predicted,
        confidence=confidence,
        estimated_weight_kg=estimated_weight_kg,
        expected_co2_saved_kg=expected_co2_saved_kg,
        expected_carbon_points=expected_carbon_points,
    )
    db.session.add(case)
    db.session.flush()
    return case


def _make_attempt(
    case: RecyclingCase,
    user: User,
    conversation: AIConversation,
    *,
    audit_result: str = "passed",
    attempt_no: int = 1,
    audit_image_url: str = "https://example.com/completion.jpg",
) -> RecyclingAuditAttempt:
    attempt = RecyclingAuditAttempt(
        recycling_case_id=case.id,
        user_id=user.id,
        conversation_id=conversation.id,
        audit_image_url=audit_image_url,
        attempt_no=attempt_no,
        audit_result=audit_result,
        auditor_confidence=0.93,
        audit_reason="Looks complete",
        audit_response_json='{"result":"approved"}',
    )
    db.session.add(attempt)
    db.session.flush()
    return attempt


def _make_completion_photo(data: str = _VALID_IMAGE_DATA_URL) -> str:
    return data


# ---------------------------------------------------------------------------
# Finalization behavior
# ---------------------------------------------------------------------------

def test_finalize_approved_case_creates_analysis_and_transaction():
    user = _make_user(points=12, carbon_amount=1.5)
    conversation = _make_conversation(user)
    origin_message = _make_origin_message(conversation)
    case = _make_case(user, conversation, origin_message)
    approved_attempt = _make_attempt(case, user, conversation, audit_result="passed")

    record, txn, returned_user = ledger_repository.finalize_approved_recycling_case_and_earn(
        user_id=user.id,
        conversation_id=conversation.id,
        recycling_case_id=case.id,
        approved_audit_attempt_id=approved_attempt.id,
        image_url="https://example.com/final.jpg",
        waste_type="plastic bottle",
        confidence=0.94,
        estimated_weight_kg=0.27,
        co2_saved_kg=0.38,
        carbon_points=5,
        raw_ai_response_json='{"stage":"finalized"}',
    )

    db.session.refresh(user)
    db.session.refresh(case)

    persisted_record = db.session.get(WasteAnalysisRecord, record.id)
    persisted_txn = db.session.get(Transaction, txn.id)

    assert returned_user.id == user.id
    assert persisted_record is not None
    assert persisted_record.user_id == user.id
    assert persisted_record.conversation_id == conversation.id
    assert persisted_record.recycling_case_id == case.id
    assert persisted_record.approved_audit_attempt_id == approved_attempt.id
    assert persisted_record.image_url == "https://example.com/final.jpg"
    assert persisted_record.waste_type == "plastic bottle"
    assert persisted_record.confidence == pytest.approx(0.94)
    assert persisted_record.estimated_weight_kg == pytest.approx(0.27)
    assert persisted_record.co2_saved_kg == pytest.approx(0.38)
    assert persisted_record.carbon_points == 5
    assert persisted_record.raw_ai_response_json == '{"stage":"finalized"}'

    assert persisted_txn is not None
    assert persisted_txn.type == "earn"
    assert persisted_txn.points_delta == 5
    assert persisted_txn.co2_delta_kg == pytest.approx(0.38)
    assert persisted_txn.source_type == "waste_analysis"
    assert persisted_txn.source_id == persisted_record.id

    assert user.current_points == 17
    assert user.total_carbon_amount == pytest.approx(1.88)
    assert case.approved_analysis_id == persisted_record.id
    assert case.status == "audit_passed"


def test_finalize_approved_case_rejects_duplicate_finalization():
    user = _make_user(points=2)
    conversation = _make_conversation(user)
    origin_message = _make_origin_message(conversation)
    case = _make_case(user, conversation, origin_message)
    approved_attempt = _make_attempt(case, user, conversation, audit_result="passed")

    first_record, _, _ = ledger_repository.finalize_approved_recycling_case_and_earn(
        user_id=user.id,
        conversation_id=conversation.id,
        recycling_case_id=case.id,
        approved_audit_attempt_id=approved_attempt.id,
        image_url="https://example.com/final.jpg",
        waste_type="plastic bottle",
        confidence=0.9,
        estimated_weight_kg=0.2,
        co2_saved_kg=0.3,
        carbon_points=3,
        raw_ai_response_json='{"stage":"finalized"}',
    )

    with pytest.raises(ValueError, match="already been finalized"):
        ledger_repository.finalize_approved_recycling_case_and_earn(
            user_id=user.id,
            conversation_id=conversation.id,
            recycling_case_id=case.id,
            approved_audit_attempt_id=approved_attempt.id,
            image_url="https://example.com/final.jpg",
            waste_type="plastic bottle",
            confidence=0.9,
            estimated_weight_kg=0.2,
            co2_saved_kg=0.3,
            carbon_points=3,
            raw_ai_response_json='{"stage":"finalized"}',
        )

    db.session.refresh(case)
    assert case.approved_analysis_id == first_record.id


def test_finalize_approved_case_rejects_missing_user():
    user = _make_user(points=0)
    conversation = _make_conversation(user)
    origin_message = _make_origin_message(conversation)
    case = _make_case(user, conversation, origin_message)
    approved_attempt = _make_attempt(case, user, conversation, audit_result="passed")

    with pytest.raises(ValueError, match="User 999999 not found"):
        ledger_repository.finalize_approved_recycling_case_and_earn(
            user_id=999999,
            conversation_id=conversation.id,
            recycling_case_id=case.id,
            approved_audit_attempt_id=approved_attempt.id,
            image_url=None,
            waste_type="plastic bottle",
            confidence=0.9,
            estimated_weight_kg=0.2,
            co2_saved_kg=0.3,
            carbon_points=3,
            raw_ai_response_json=None,
        )


def test_finalize_approved_case_rejects_conversation_mismatch():
    owner = _make_user(username="owner", email="owner@example.com")
    other_conversation = _make_conversation(owner, title="Other conversation")
    conversation = _make_conversation(owner)
    origin_message = _make_origin_message(conversation)
    case = _make_case(owner, conversation, origin_message)
    approved_attempt = _make_attempt(case, owner, conversation, audit_result="passed")

    with pytest.raises(ValueError, match="does not belong to conversation"):
        ledger_repository.finalize_approved_recycling_case_and_earn(
            user_id=owner.id,
            conversation_id=other_conversation.id,
            recycling_case_id=case.id,
            approved_audit_attempt_id=approved_attempt.id,
            image_url=None,
            waste_type="plastic bottle",
            confidence=0.9,
            estimated_weight_kg=0.2,
            co2_saved_kg=0.3,
            carbon_points=3,
            raw_ai_response_json=None,
        )


def test_failed_audit_keeps_case_open_for_retry(monkeypatch):
    user = _make_user(points=1)
    conversation = _make_conversation(user, title="Audit flow")
    origin_message = _make_origin_message(conversation, text="Analyze this bottle.")
    case = _make_case(user, conversation, origin_message)

    monkeypatch.setattr(recycling_audit_service, "_get_authenticated_user_id", lambda: user.id)
    monkeypatch.setattr(
        recycling_audit_service,
        "complete_json",
        lambda **kwargs: {
            "audit_result": "failed",
            "auditor_confidence": 0.42,
            "audit_reason": "The recycling task is not clearly completed.",
        },
    )

    events = list(
        recycling_audit_service.stream_recycling_audit(
            conversation_id=conversation.id,
            recycling_case_id=case.id,
            message="Here is my completion photo.",
            image_data_url=_make_completion_photo(),
        )
    )

    refreshed_case = db.session.get(RecyclingCase, case.id)
    attempts = list(
        db.session.scalars(
            select(RecyclingAuditAttempt).where(RecyclingAuditAttempt.recycling_case_id == case.id)
        )
    )
    messages = list(
        db.session.scalars(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation.id)
            .order_by(AIMessage.sequence_no.asc())
        )
    )
    transaction_count = db.session.scalar(select(func.count(Transaction.id))) or 0

    assert [event["type"] for event in events] == ["meta", "stage_start", "stage_payload", "done"]
    assert refreshed_case.status == "audit_failed"
    assert refreshed_case.approved_analysis_id is None
    assert len(attempts) == 1
    assert attempts[0].audit_result == "failed"
    assert [message.role for message in messages] == ["user", "user", "assistant"]
    assert messages[-1].message_type == "audit_result"
    assert conversation.status == "active"
    assert transaction_count == 0


def test_passed_audit_finalizes_case_and_awards_points(monkeypatch):
    user = _make_user(points=5, carbon_amount=0.5)
    conversation = _make_conversation(user, title="Audit flow pass")
    origin_message = _make_origin_message(conversation, text="Analyze this bottle.")
    case = _make_case(user, conversation, origin_message)

    monkeypatch.setattr(recycling_audit_service, "_get_authenticated_user_id", lambda: user.id)
    monkeypatch.setattr(
        recycling_audit_service,
        "complete_json",
        lambda **kwargs: {
            "audit_result": "passed",
            "auditor_confidence": 0.97,
            "audit_reason": "The completion photo clearly shows the task was completed.",
        },
    )

    events = list(
        recycling_audit_service.stream_recycling_audit(
            conversation_id=conversation.id,
            recycling_case_id=case.id,
            message="Here is my completion photo.",
            image_data_url=_make_completion_photo(),
        )
    )

    refreshed_case = db.session.get(RecyclingCase, case.id)
    attempts = list(
        db.session.scalars(
            select(RecyclingAuditAttempt).where(RecyclingAuditAttempt.recycling_case_id == case.id)
        )
    )
    record = db.session.scalar(
        select(WasteAnalysisRecord).where(WasteAnalysisRecord.recycling_case_id == case.id)
    )
    messages = list(
        db.session.scalars(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation.id)
            .order_by(AIMessage.sequence_no.asc())
        )
    )
    transaction_count = db.session.scalar(select(func.count(Transaction.id))) or 0

    assert [event["type"] for event in events] == ["meta", "stage_start", "stage_payload", "done"]
    assert refreshed_case.status == "audit_passed"
    assert record is not None
    assert refreshed_case.approved_analysis_id == record.id
    assert len(attempts) == 1
    assert attempts[0].audit_result == "passed"
    assert record.user_id == user.id
    assert transaction_count == 1
    assert user.current_points == 9
    assert user.total_carbon_amount > 0.5
    assert [message.role for message in messages] == ["user", "user", "assistant"]
    assert messages[-1].message_type == "audit_result"
    assert conversation.status == "completed"


def test_retry_after_failed_audit_can_later_finalize(monkeypatch):
    user = _make_user(points=0, carbon_amount=0.0)
    conversation = _make_conversation(user, title="Audit retry flow")
    origin_message = _make_origin_message(conversation, text="Analyze this can.")
    case = _make_case(
        user,
        conversation,
        origin_message,
        waste_type_predicted="metal can",
        expected_co2_saved_kg=0.22,
        expected_carbon_points=2.0,
    )

    monkeypatch.setattr(recycling_audit_service, "_get_authenticated_user_id", lambda: user.id)

    results = iter(
        [
            {
                "audit_result": "failed",
                "auditor_confidence": 0.4,
                "audit_reason": "The first photo is not enough to verify completion.",
            },
            {
                "audit_result": "passed",
                "auditor_confidence": 0.96,
                "audit_reason": "The second photo clearly shows completion.",
            },
        ]
    )
    monkeypatch.setattr(recycling_audit_service, "complete_json", lambda **kwargs: next(results))

    list(
        recycling_audit_service.stream_recycling_audit(
            conversation_id=conversation.id,
            recycling_case_id=case.id,
            message="First completion photo.",
            image_data_url=_make_completion_photo(),
        )
    )
    list(
        recycling_audit_service.stream_recycling_audit(
            conversation_id=conversation.id,
            recycling_case_id=case.id,
            message="Second completion photo.",
            image_data_url=_make_completion_photo(),
        )
    )

    refreshed_case = db.session.get(RecyclingCase, case.id)
    attempts = list(
        db.session.scalars(
            select(RecyclingAuditAttempt)
            .where(RecyclingAuditAttempt.recycling_case_id == case.id)
            .order_by(RecyclingAuditAttempt.attempt_no.asc())
        )
    )
    record = db.session.scalar(
        select(WasteAnalysisRecord).where(WasteAnalysisRecord.recycling_case_id == case.id)
    )
    transaction_count = db.session.scalar(select(func.count(Transaction.id))) or 0

    assert refreshed_case.status == "audit_passed"
    assert refreshed_case.approved_analysis_id == record.id
    assert [attempt.audit_result for attempt in attempts] == ["failed", "passed"]
    assert [attempt.attempt_no for attempt in attempts] == [1, 2]
    assert transaction_count == 1
    assert user.current_points == 2


def test_audit_prompt_requires_disposal_path_to_match_waste_type():
    prompt = recycling_audit_service._build_audit_prompt(
        "I threw it into the recycling bin.",
        {
            "id": 9,
            "waste_type_predicted": "Portable Power Bank (E-waste)",
            "status": "pending_audit",
        },
    )
    system_prompt = recycling_audit_service._audit_system_prompt()
    normalized_system_prompt = " ".join(system_prompt.split())

    assert "disposal suitability for the case's waste type" in prompt
    assert "generic recycling bin" in prompt
    assert "ordinary recycling bin is not enough evidence" in normalized_system_prompt
    assert "appropriate for the case's waste type" in normalized_system_prompt
