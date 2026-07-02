import uuid

from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.ai import AIConversation, AIMessage, RecyclingCase
from app.models.user import User
from app.services.ai.conversation_context_builder import (
    build_context_bundle,
    build_runtime_reply_context,
)


def _make_user(username: str = "ctx", email: str = "ctx@example.com") -> User:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"{username}_{suffix}",
        email=f"{suffix}_{email}",
        password_hash=generate_password_hash("password123"),
    )
    db.session.add(user)
    db.session.flush()
    return user


def _make_conversation(user: User, title: str = "Context chat") -> AIConversation:
    conversation = AIConversation(
        user_id=user.id,
        title=title,
        session_context_json='{"location_state":{"permission_state":"granted","normalized_area":"Shanghai"}}',
    )
    db.session.add(conversation)
    db.session.flush()
    return conversation


def _append_message(
    conversation: AIConversation,
    *,
    role: str,
    message_type: str,
    content_text: str,
    sequence_no: int,
) -> AIMessage:
    message = AIMessage(
        conversation_id=conversation.id,
        role=role,
        message_type=message_type,
        content_text=content_text,
        sequence_no=sequence_no,
    )
    db.session.add(message)
    db.session.flush()
    return message


class TestConversationContextBuilder:
    def test_build_context_bundle_uses_current_conversation_only(self):
        user = _make_user()
        conversation = _make_conversation(user, title="Primary")
        other = _make_conversation(user, title="Other")

        _append_message(conversation, role="user", message_type="text", content_text="hello", sequence_no=1)
        _append_message(conversation, role="assistant", message_type="text", content_text="hi", sequence_no=2)
        _append_message(other, role="user", message_type="text", content_text="other chat", sequence_no=1)

        bundle = build_context_bundle(conversation_id=conversation.id, max_turns=5)

        assert bundle["recent_history"] == [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]

    def test_build_runtime_reply_context_includes_memory_and_location_state(self):
        user = _make_user("runtime", "runtime@example.com")
        user.preferences_json = '{"response_style":"concise"}'
        conversation = _make_conversation(user)
        origin = _append_message(
            conversation,
            role="user",
            message_type="text",
            content_text="Analyze this bottle",
            sequence_no=1,
        )
        _append_message(
            conversation,
            role="assistant",
            message_type="analysis_result",
            content_text="Bottle analysis result",
            sequence_no=2,
        )
        case = RecyclingCase(
            user_id=user.id,
            conversation_id=conversation.id,
            origin_message_id=origin.id,
            waste_type_predicted="plastic bottle",
            confidence=0.88,
            estimated_weight_kg=0.2,
            expected_co2_saved_kg=0.3,
            expected_carbon_points=3.0,
        )
        db.session.add(case)
        db.session.flush()

        runtime_context = build_runtime_reply_context(
            conversation_id=conversation.id,
            user_id=user.id,
            max_turns=5,
        )

        assert runtime_context["long_term_memory"]["response_style"] == "concise"
        assert runtime_context["location_state"]["normalized_area"] == "Shanghai"
        assert runtime_context["case_summaries"][0]["case_id"] == case.id
        assert runtime_context["working_memory"]["latest_analysis"] == "Bottle analysis result"
