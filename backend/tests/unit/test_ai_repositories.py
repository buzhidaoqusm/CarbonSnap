"""Schema-focused tests for the AI persistence models.

These tests intentionally stay at the model layer so Task 1 can validate the
new table shape and basic constraints before repository/service code lands.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.ai import (
    AIConversation,
    AIMessageDecision,
    AIMessage,
    RecyclingAuditAttempt,
    RecyclingCase,
    WasteAnalysisRecord,
)
from app.models.user import User
from app.repositories.ai import (
    conversation_repository,
    message_decision_repository,
    recycling_case_repository,
)


def _make_user(username: str = "alice", email: str = "alice@example.com") -> User:
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"{username}_{unique_suffix}",
        email=f"{unique_suffix}_{email}",
        password_hash=generate_password_hash("password123"),
    )
    db.session.add(user)
    db.session.flush()
    return user


def _make_conversation(user: User, title: str = "AI Chat") -> AIConversation:
    conversation = AIConversation(user_id=user.id, title=title)
    db.session.add(conversation)
    db.session.flush()
    return conversation


def _make_message(
    conversation: AIConversation,
    *,
    role: str = "user",
    message_type: str = "text",
    content_text: str = "Hello",
) -> AIMessage:
    message = AIMessage(
        conversation_id=conversation.id,
        role=role,
        message_type=message_type,
        content_text=content_text,
        sequence_no=1,
    )
    db.session.add(message)
    db.session.flush()
    return message


class TestRecyclingCaseModel:
    def test_defaults_are_initialized(self):
        user = _make_user()
        conversation = _make_conversation(user)
        origin_message = _make_message(conversation, content_text="Please analyze this item.")

        case = RecyclingCase(
            user_id=user.id,
            conversation_id=conversation.id,
            origin_message_id=origin_message.id,
            waste_type_predicted="plastic bottle",
            expected_co2_saved_kg=0.3,
            expected_carbon_points=3.0,
        )
        db.session.add(case)
        db.session.flush()

        assert case.status == "pending_audit"
        assert case.latest_audit_attempt_no == 0
        assert case.approved_analysis_id is None
        assert case.confidence == 0.0
        assert case.estimated_weight_kg == 0.0
        assert case.expected_co2_saved_kg == 0.3
        assert case.expected_carbon_points == 3.0
        assert case.created_at is not None
        assert case.updated_at is not None


class TestAiMessageDecisionModel:
    def test_defaults_are_initialized(self):
        user = _make_user("decider", "decider@example.com")
        conversation = _make_conversation(user)
        message = _make_message(conversation, content_text="What should I do next?")

        decision = AIMessageDecision(
            conversation_id=conversation.id,
            user_message_id=message.id,
            intent="general_chat",
            decision_json='{"intent":"general_chat"}',
            engine_version="decision-engine-v1",
        )
        db.session.add(decision)
        db.session.flush()

        assert decision.id is not None
        assert decision.follow_up_type is None
        assert decision.target_case_id is None
        assert decision.needs_clarification is False
        assert decision.created_at is not None


class TestRecyclingAuditAttemptModel:
    def test_attempt_number_is_unique_per_case_but_not_global(self):
        user = _make_user()
        conversation = _make_conversation(user)
        origin_message = _make_message(conversation, content_text="Please analyze this item.")

        case_one = RecyclingCase(
            user_id=user.id,
            conversation_id=conversation.id,
            origin_message_id=origin_message.id,
            waste_type_predicted="plastic bottle",
            expected_co2_saved_kg=0.3,
            expected_carbon_points=3.0,
        )
        case_two = RecyclingCase(
            user_id=user.id,
            conversation_id=conversation.id,
            origin_message_id=origin_message.id,
            waste_type_predicted="paper",
            expected_co2_saved_kg=0.1,
            expected_carbon_points=1.0,
        )
        db.session.add_all([case_one, case_two])
        db.session.flush()

        first_attempt = RecyclingAuditAttempt(
            recycling_case_id=case_one.id,
            user_id=user.id,
            conversation_id=conversation.id,
            audit_image_url="https://example.com/case-one-1.jpg",
            attempt_no=1,
            audit_result="failed",
            auditor_confidence=0.41,
        )
        second_case_attempt = RecyclingAuditAttempt(
            recycling_case_id=case_two.id,
            user_id=user.id,
            conversation_id=conversation.id,
            audit_image_url="https://example.com/case-two-1.jpg",
            attempt_no=1,
            audit_result="passed",
            auditor_confidence=0.91,
        )
        db.session.add_all([first_attempt, second_case_attempt])
        db.session.flush()

        duplicate_attempt = RecyclingAuditAttempt(
            recycling_case_id=case_one.id,
            user_id=user.id,
            conversation_id=conversation.id,
            audit_image_url="https://example.com/case-one-dup.jpg",
            attempt_no=1,
            audit_result="failed",
            auditor_confidence=0.12,
        )
        db.session.add(duplicate_attempt)

        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()

    def test_attempt_defaults_are_persisted(self):
        user = _make_user("brian", "brian@example.com")
        conversation = _make_conversation(user, title="Audit")
        origin_message = _make_message(conversation, content_text="Waiting for completion photo.")

        case = RecyclingCase(
            user_id=user.id,
            conversation_id=conversation.id,
            origin_message_id=origin_message.id,
            waste_type_predicted="glass",
            expected_co2_saved_kg=0.2,
            expected_carbon_points=2.0,
        )
        db.session.add(case)
        db.session.flush()

        attempt = RecyclingAuditAttempt(
            recycling_case_id=case.id,
            user_id=user.id,
            conversation_id=conversation.id,
            audit_image_url="https://example.com/completion.jpg",
            attempt_no=1,
            audit_result="unclear",
        )
        db.session.add(attempt)
        db.session.flush()

        assert attempt.attempt_no == 1
        assert attempt.auditor_confidence == 0.0
        assert attempt.audit_reason is None
        assert attempt.audit_response_json is None
        assert attempt.created_at is not None


class TestConversationRepository:
    def test_create_conversation_uses_default_title(self):
        user = _make_user("dylan", "dylan@example.com")

        conversation = conversation_repository.create_conversation(user_id=user.id)

        assert conversation.title == "New chat"
        assert conversation.status == "active"
        assert conversation.current_pending_action == "none"
        assert conversation.user_id == user.id

    def test_append_message_increments_sequence_numbers(self):
        user = _make_user("erin", "erin@example.com")
        conversation = _make_conversation(user)

        first = conversation_repository.append_message(
            conversation_id=conversation.id,
            role="user",
            message_type="text",
            content_text="hello",
        )
        second = conversation_repository.append_message(
            conversation_id=conversation.id,
            role="assistant",
            message_type="text",
            content_text="hi there",
        )

        messages = conversation_repository.list_messages(conversation.id)
        assert first.sequence_no == 1
        assert second.sequence_no == 2
        assert [message.sequence_no for message in messages] == [1, 2]

    def test_update_conversation_state_and_list_order(self):
        user = _make_user("frank", "frank@example.com")
        first_conversation = conversation_repository.create_conversation(user_id=user.id, title="First")
        second_conversation = conversation_repository.create_conversation(user_id=user.id, title="Second")

        conversation_repository.append_message(
            conversation_id=first_conversation.id,
            role="user",
            message_type="text",
            content_text="old chat",
        )
        conversation_repository.append_message(
            conversation_id=second_conversation.id,
            role="user",
            message_type="text",
            content_text="new chat",
        )

        ordered = conversation_repository.list_conversations(user.id)
        assert ordered[0].id == second_conversation.id
        assert ordered[1].id == first_conversation.id

        updated = conversation_repository.update_conversation_state(
            first_conversation.id,
            status="awaiting_location",
            current_pending_action="location_permission",
            session_context_json='{"step":"paused"}',
            title="Renamed",
        )
        assert updated.status == "awaiting_location"
        assert updated.current_pending_action == "location_permission"
        assert updated.session_context_json == '{"step":"paused"}'
        assert updated.title == "Renamed"


class TestMessageDecisionRepository:
    def test_create_message_decision_persists_target_case(self):
        user = _make_user("router", "router@example.com")
        conversation = _make_conversation(user)
        origin_message = _make_message(conversation, content_text="Analyze this bottle.")
        recycling_case = recycling_case_repository.create_recycling_case(
            user_id=user.id,
            conversation_id=conversation.id,
            origin_message_id=origin_message.id,
            waste_type_predicted="plastic bottle",
            confidence=0.82,
            estimated_weight_kg=0.24,
            expected_co2_saved_kg=0.36,
            expected_carbon_points=4.0,
        )
        user_message = conversation_repository.append_message(
            conversation_id=conversation.id,
            role="user",
            message_type="text",
            content_text="Show me nearby options for that bottle.",
        )

        decision = message_decision_repository.create_message_decision(
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            intent="recycling_follow_up",
            follow_up_type="nearby_search",
            target_case_id=recycling_case.id,
            confidence=0.91,
            needs_clarification=False,
            decision_payload={"intent": "recycling_follow_up"},
            engine_version="decision-engine-v1",
        )

        latest = message_decision_repository.get_latest_message_decision_for_message(user_message.id)
        all_for_conversation = message_decision_repository.list_message_decisions_for_conversation(conversation.id)

        assert decision.target_case_id == recycling_case.id
        assert decision.intent == "recycling_follow_up"
        assert latest is not None
        assert latest.id == decision.id
        assert len(all_for_conversation) == 1


class TestRecyclingCaseRepository:
    def test_create_case_and_fetch_pending_case(self):
        user = _make_user("gail", "gail@example.com")
        conversation = _make_conversation(user)
        origin_message = _make_message(conversation, content_text="Analyze this bottle.")

        case = recycling_case_repository.create_recycling_case(
            user_id=user.id,
            conversation_id=conversation.id,
            origin_message_id=origin_message.id,
            waste_type_predicted="plastic bottle",
            confidence=0.82,
            estimated_weight_kg=0.24,
            expected_co2_saved_kg=0.36,
            expected_carbon_points=4.0,
        )

        pending = recycling_case_repository.get_pending_case_for_conversation(conversation.id)
        fetched = recycling_case_repository.get_case(case.id, user.id)

        assert pending is not None
        assert pending.id == case.id
        assert fetched is not None
        assert fetched.waste_type_predicted == "plastic bottle"
        assert fetched.status == "pending_audit"

    def test_create_audit_attempt_updates_case_state(self):
        user = _make_user("helen", "helen@example.com")
        conversation = _make_conversation(user)
        origin_message = _make_message(conversation, content_text="Analyze this item.")
        case = recycling_case_repository.create_recycling_case(
            user_id=user.id,
            conversation_id=conversation.id,
            origin_message_id=origin_message.id,
            waste_type_predicted="paper",
            confidence=0.75,
            estimated_weight_kg=0.1,
            expected_co2_saved_kg=0.1,
            expected_carbon_points=1.0,
        )

        first_attempt = recycling_case_repository.create_audit_attempt(
            recycling_case_id=case.id,
            user_id=user.id,
            conversation_id=conversation.id,
            audit_image_url="https://example.com/audit-1.jpg",
            audit_result="failed",
            auditor_confidence=0.41,
        )
        second_attempt = recycling_case_repository.create_audit_attempt(
            recycling_case_id=case.id,
            user_id=user.id,
            conversation_id=conversation.id,
            audit_image_url="https://example.com/audit-2.jpg",
            audit_result="passed",
            auditor_confidence=0.96,
        )

        attempts = recycling_case_repository.list_audit_attempts(case.id)
        refreshed_case = recycling_case_repository.get_case(case.id, user.id)

        assert first_attempt.attempt_no == 1
        assert second_attempt.attempt_no == 2
        assert [attempt.attempt_no for attempt in attempts] == [1, 2]
        assert refreshed_case is not None
        assert refreshed_case.latest_audit_attempt_no == 2
        assert refreshed_case.status == "audit_failed"

        marked = recycling_case_repository.mark_case_audit_passed(case.id, approved_analysis_id=42)
        assert marked.approved_analysis_id == 42
        assert marked.status == "audit_passed"


class TestWasteAnalysisRecordModel:
    def test_accepts_new_link_fields_and_defaults(self):
        user = _make_user("cathy", "cathy@example.com")
        conversation = _make_conversation(user, title="Finalized case")
        origin_message = _make_message(conversation, content_text="Analyze my recycling item.")

        case = RecyclingCase(
            user_id=user.id,
            conversation_id=conversation.id,
            origin_message_id=origin_message.id,
            waste_type_predicted="plastic bottle",
            expected_co2_saved_kg=0.3,
            expected_carbon_points=3.0,
        )
        db.session.add(case)
        db.session.flush()

        attempt = RecyclingAuditAttempt(
            recycling_case_id=case.id,
            user_id=user.id,
            conversation_id=conversation.id,
            audit_image_url="https://example.com/final.jpg",
            attempt_no=1,
            audit_result="passed",
            auditor_confidence=0.93,
        )
        db.session.add(attempt)
        db.session.flush()

        record = WasteAnalysisRecord(
            user_id=user.id,
            conversation_id=conversation.id,
            recycling_case_id=case.id,
            approved_audit_attempt_id=attempt.id,
            image_url="https://example.com/final.jpg",
            waste_type="plastic bottle",
            raw_ai_response_json='{"result":"passed"}',
        )
        db.session.add(record)
        db.session.flush()

        assert record.conversation_id == conversation.id
        assert record.recycling_case_id == case.id
        assert record.approved_audit_attempt_id == attempt.id
        assert record.confidence == 0.0
        assert record.estimated_weight_kg == 0.0
        assert record.co2_saved_kg == 0.0
        assert record.carbon_points == 0
