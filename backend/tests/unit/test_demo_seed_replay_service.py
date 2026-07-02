from __future__ import annotations

import base64
import json
from pathlib import Path

from sqlalchemy import select
from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.ai import AIConversation, AIMessage, RecyclingAuditAttempt, RecyclingCase, WasteAnalysisRecord
from app.models.ledger import Transaction
from app.models.memory import UserMemoryItem
from app.models.user import User
from app.services.ai import ai_conversation_service, recycling_analysis_service, recycling_audit_service
from app.services.ai.demo_seed_replay_service import find_seed_replay_match


def _make_user() -> User:
    user = User(
        username="demo_replay_user",
        email="demo-replay@example.com",
        password_hash=generate_password_hash("password123"),
    )
    db.session.add(user)
    db.session.flush()
    return user


def _seed_image_data_url(filename: str) -> str:
    seed_path = Path(__file__).resolve().parents[3] / "data" / "seeds" / "assets" / "seed-ai" / filename
    encoded = base64.b64encode(seed_path.read_bytes()).decode("ascii")
    suffix = seed_path.suffix.lower().lstrip(".") or "jpeg"
    media_type = "jpeg" if suffix == "jpg" else suffix
    return f"data:image/{media_type};base64,{encoded}"


def _messages_for_conversation(conversation_id: int) -> list[AIMessage]:
    return list(
        db.session.scalars(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation_id)
            .order_by(AIMessage.sequence_no.asc(), AIMessage.id.asc())
        )
    )


def test_find_seed_replay_match_uses_text_and_image_hash(app):
    image_data_url = _seed_image_data_url("dual-case-recycling-chat-message-01-image_url.jpg")

    with app.app_context():
        match = find_seed_replay_match(
            message="  how   should i recycle this ONE  ",
            image_data_url=image_data_url,
        )

    assert match is not None
    assert match.user_message.seed_key == "dual-case-recycling-chat-message-01"
    assert [message.seed_key for message in match.assistant_messages] == [
        "dual-case-recycling-chat-message-02",
        "dual-case-recycling-chat-message-03",
    ]


def test_find_seed_replay_match_supports_text_only_seed_messages(app):
    with app.app_context():
        match = find_seed_replay_match(message=" hello ", image_data_url=None)

    assert match is not None
    assert match.user_message.seed_key == "memory-preference-chat-message-01"
    assert match.assistant_messages[0].seed_key == "memory-preference-chat-message-02"


def test_stream_routed_chat_message_replays_seed_without_decision_engine(app, monkeypatch):
    image_data_url = _seed_image_data_url("dual-case-recycling-chat-message-01-image_url.jpg")

    def fail_decision_engine(**kwargs):
        raise AssertionError("demo replay should not call the decision engine")

    from app.services.ai import ai_decision_engine

    monkeypatch.setattr(ai_decision_engine, "decide_message", fail_decision_engine)

    with app.app_context():
        monkeypatch.setitem(app.config, "AI_DEMO_REPLAY_ENABLED", True)
        user = _make_user()

        events = list(
            ai_conversation_service.stream_routed_chat_message(
                user_id=user.id,
                message="How should I recycle this one",
                image_data_url=image_data_url,
            )
        )

        meta = events[0]
        conversation = db.session.get(AIConversation, meta["conversation_id"])
        messages = _messages_for_conversation(conversation.id)
        cases = list(db.session.scalars(select(RecyclingCase).where(RecyclingCase.conversation_id == conversation.id)))

    assert meta["type"] == "meta"
    assert meta["demo_replay"] is True
    assert conversation.title == "Dual-Case Recycling Chat"
    assert conversation.status == "awaiting_location"
    assert conversation.current_pending_action == "location_permission"
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[0].message_type == "image"
    assert json.loads(messages[0].content_json)["demo_replay"] is True
    assert messages[1].message_type == "analysis_result"
    assert len(cases) == 1

    analysis_payload_event = next(
        event for event in events if event.get("type") == "stage_payload" and event.get("stage") == "analysis"
    )
    awaiting_event = next(event for event in events if event.get("type") == "awaiting_location")
    done_event = events[-1]
    replayed_text = "".join(str(event.get("content", "")) for event in events if event.get("type") == "delta")

    assert analysis_payload_event["data"]["recycling_case_id"] == cases[0].id
    assert awaiting_event["data"]["recycling_case_id"] == cases[0].id
    assert awaiting_event["data"]["requires_location_decision"] is True
    assert awaiting_event["data"]["session_id"]
    assert cases[0].status == "pending_audit"
    assert cases[0].latest_audit_attempt_no == 0
    assert cases[0].approved_analysis_id is None
    assert "Recycling Suggestion for a Plastic Bottle" in replayed_text
    assert done_event == {"type": "done", "stream_stage": "awaiting_location"}


def test_stream_recycling_resume_continues_demo_replay_after_location(app, monkeypatch):
    image_data_url = _seed_image_data_url("dual-case-recycling-chat-message-01-image_url.jpg")

    with app.app_context():
        monkeypatch.setitem(app.config, "AI_DEMO_REPLAY_ENABLED", True)
        user = _make_user()

        initial_events = list(
            ai_conversation_service.stream_routed_chat_message(
                user_id=user.id,
                message="How should I recycle this one",
                image_data_url=image_data_url,
            )
        )
        awaiting_event = next(event for event in initial_events if event.get("type") == "awaiting_location")
        session_id = awaiting_event["data"]["session_id"]

        recycling_analysis_service.store_location_context(
            {
                "session_id": session_id,
                "permission_state": "granted",
                "browser_location": {
                    "lat": 39.87501048850203,
                    "lng": 116.47902238836137,
                },
            }
        )
        resume_events = list(recycling_analysis_service.stream_recycling_resume(session_id=session_id))
        messages = _messages_for_conversation(initial_events[0]["conversation_id"])
        conversation = db.session.get(AIConversation, initial_events[0]["conversation_id"])

    nearby_event = next(event for event in resume_events if event.get("type") == "nearby_results")
    replayed_text = "".join(str(event.get("content", "")) for event in resume_events if event.get("type") == "delta")

    assert resume_events[0]["demo_replay"] is True
    assert nearby_event["data"]["nearby_locations"][0]["name"] == "Xiaowuji Large Solid Waste Transfer Station"
    assert "Nearby Recycling Options Found" in replayed_text
    assert [message.message_type for message in messages] == ["image", "analysis_result", "tool_result"]
    assert conversation.status == "completed"
    assert conversation.current_pending_action == "none"
    assert resume_events[-1] == {"type": "done", "stream_stage": "completed"}


def test_stream_recycling_audit_replays_seed_audit_result(app, monkeypatch):
    analysis_image_data_url = _seed_image_data_url("dual-case-recycling-chat-message-01-image_url.jpg")
    audit_image_data_url = _seed_image_data_url("dual-case-recycling-chat-audit-01-image.png")

    monkeypatch.setattr(
        recycling_audit_service,
        "complete_json",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("demo audit should not call AI")),
    )

    with app.app_context():
        monkeypatch.setitem(app.config, "AI_DEMO_REPLAY_ENABLED", True)
        user = _make_user()
        monkeypatch.setattr(recycling_audit_service, "_get_authenticated_user_id", lambda: user.id)

        initial_events = list(
            ai_conversation_service.stream_routed_chat_message(
                user_id=user.id,
                message="How should I recycle this one",
                image_data_url=analysis_image_data_url,
            )
        )
        conversation_id = initial_events[0]["conversation_id"]
        awaiting_event = next(event for event in initial_events if event.get("type") == "awaiting_location")
        case_id = awaiting_event["data"]["recycling_case_id"]

        audit_events = list(
            recycling_audit_service.stream_recycling_audit(
                conversation_id=conversation_id,
                recycling_case_id=case_id,
                message="Please audit this completion photo.",
                image_data_url=audit_image_data_url,
            )
        )

        messages = _messages_for_conversation(conversation_id)
        refreshed_case = db.session.get(RecyclingCase, case_id)
        attempts = list(
            db.session.scalars(
                select(RecyclingAuditAttempt).where(RecyclingAuditAttempt.recycling_case_id == case_id)
            )
        )
        record = db.session.scalar(
            select(WasteAnalysisRecord).where(WasteAnalysisRecord.recycling_case_id == case_id)
        )
        transaction = db.session.scalar(select(Transaction).where(Transaction.source_id == record.id))

    payload_event = next(event for event in audit_events if event.get("type") == "stage_payload")
    assert [event["type"] for event in audit_events] == ["meta", "stage_start", "stage_payload", "done"]
    assert payload_event["stage"] == "finalize"
    assert payload_event["data"]["audit_result"]["audit_result"] == "passed"
    assert payload_event["data"]["demo_replay"] is True
    assert "Audit passed. Your recycling case has been verified" in messages[-1].content_text
    assert messages[-2].message_type == "image"
    assert messages[-1].message_type == "audit_result"
    assert refreshed_case.status == "audit_passed"
    assert refreshed_case.approved_analysis_id == record.id
    assert attempts[0].audit_result == "passed"
    assert transaction.points_delta == 1
    assert audit_events[-1] == {"type": "done", "stream_stage": "finalized"}


def test_stream_recycling_audit_matches_retry_by_image_when_text_differs(app, monkeypatch):
    analysis_image_data_url = _seed_image_data_url("dual-case-recycling-chat-message-06-image_url.jpg")
    unclear_audit_image_data_url = _seed_image_data_url("dual-case-recycling-chat-audit-02-image.png")
    passed_audit_image_data_url = _seed_image_data_url("dual-case-recycling-chat-audit-03-image.png")

    monkeypatch.setattr(
        recycling_audit_service,
        "complete_json",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("demo audit should not call AI")),
    )

    with app.app_context():
        monkeypatch.setitem(app.config, "AI_DEMO_REPLAY_ENABLED", True)
        user = _make_user()
        monkeypatch.setattr(recycling_audit_service, "_get_authenticated_user_id", lambda: user.id)

        initial_events = list(
            ai_conversation_service.stream_routed_chat_message(
                user_id=user.id,
                message="How can I recycle this one",
                image_data_url=analysis_image_data_url,
            )
        )
        conversation_id = initial_events[0]["conversation_id"]
        awaiting_event = next(event for event in initial_events if event.get("type") == "awaiting_location")
        case_id = awaiting_event["data"]["recycling_case_id"]

        unclear_events = list(
            recycling_audit_service.stream_recycling_audit(
                conversation_id=conversation_id,
                recycling_case_id=case_id,
                message="Please audit this completion photo.",
                image_data_url=unclear_audit_image_data_url,
            )
        )
        passed_events = list(
            recycling_audit_service.stream_recycling_audit(
                conversation_id=conversation_id,
                recycling_case_id=case_id,
                message="Please audit this completion photo.",
                image_data_url=passed_audit_image_data_url,
            )
        )

        refreshed_case = db.session.get(RecyclingCase, case_id)
        attempts = list(
            db.session.scalars(
                select(RecyclingAuditAttempt)
                .where(RecyclingAuditAttempt.recycling_case_id == case_id)
                .order_by(RecyclingAuditAttempt.attempt_no.asc())
            )
        )

    unclear_payload = next(event for event in unclear_events if event.get("type") == "stage_payload")
    passed_payload = next(event for event in passed_events if event.get("type") == "stage_payload")

    assert unclear_payload["data"]["audit_result"]["audit_result"] == "unclear"
    assert unclear_events[-1] == {"type": "done", "stream_stage": "audit"}
    assert passed_payload["data"]["audit_result"]["audit_result"] == "passed"
    assert passed_payload["data"]["audit_result"]["audit_reason"].startswith("The photo clearly shows a power bank")
    assert passed_events[-1] == {"type": "done", "stream_stage": "finalized"}
    assert [attempt.audit_result for attempt in attempts] == ["unclear", "passed"]
    assert refreshed_case.status == "audit_passed"


def test_stream_routed_chat_message_replays_text_seed_without_stage_start(app, monkeypatch):
    from app.services.ai import ai_decision_engine

    monkeypatch.setattr(
        ai_decision_engine,
        "decide_message",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("demo replay should not call AI routing")),
    )

    with app.app_context():
        monkeypatch.setitem(app.config, "AI_DEMO_REPLAY_ENABLED", True)
        user = _make_user()

        events = list(
            ai_conversation_service.stream_routed_chat_message(
                user_id=user.id,
                message="Hello",
                image_data_url=None,
            )
        )

        meta = events[0]
        messages = _messages_for_conversation(meta["conversation_id"])

    assert not any(event.get("type") == "stage_start" for event in events)
    assert "".join(str(event.get("content", "")) for event in events if event.get("type") == "delta") == (
        "Hello! How can I assist you today?"
    )
    assert [message.message_type for message in messages] == ["text", "text"]
    assert json.loads(messages[0].content_json)["demo_seed_message_key"] == "memory-preference-chat-message-01"
    assert json.loads(messages[1].content_json)["demo_seed_message_key"] == "memory-preference-chat-message-02"


def test_stream_routed_chat_message_emits_seed_memory_updates_in_meta(app, monkeypatch):
    from app.services.ai import ai_decision_engine

    monkeypatch.setattr(
        ai_decision_engine,
        "decide_message",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("demo replay should not call AI routing")),
    )

    with app.app_context():
        monkeypatch.setitem(app.config, "AI_DEMO_REPLAY_ENABLED", True)
        user = _make_user()

        events = list(
            ai_conversation_service.stream_routed_chat_message(
                user_id=user.id,
                message="From now on, I prefer nearby drop-off suggestions first.",
                image_data_url=None,
            )
        )
        messages = _messages_for_conversation(events[0]["conversation_id"])
        memory_items = list(
            db.session.scalars(
                select(UserMemoryItem)
                .where(UserMemoryItem.user_id == user.id)
                .order_by(UserMemoryItem.id.asc())
            )
        )

    assert len(events[0]["memory_updates"]) == 1
    assert events[0]["memory_updates"][0]["memory_type"] == "recycling_preference"
    assert events[0]["memory_updates"][0]["memory_key"] == "prefer_nearby_options"
    assert json.loads(messages[1].content_json)["memory_updates"] == events[0]["memory_updates"]
    assert "prioritize nearby drop-off suggestions" in "".join(
        str(event.get("content", "")) for event in events if event.get("type") == "delta"
    )
    assert len(memory_items) == 1
    assert memory_items[0].memory_type == "recycling_preference"
    assert memory_items[0].memory_key == "prefer_nearby_options"
    assert json.loads(memory_items[0].value_json) == {"value": True}
    assert memory_items[0].source_type == "explicit_chat"


def test_stream_routed_chat_message_replays_nearby_follow_up_without_extra_stage(app, monkeypatch):
    from app.services.ai import ai_decision_engine

    monkeypatch.setattr(
        ai_decision_engine,
        "decide_message",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("demo replay should not call AI routing")),
    )

    with app.app_context():
        monkeypatch.setitem(app.config, "AI_DEMO_REPLAY_ENABLED", True)
        user = _make_user()

        events = list(
            ai_conversation_service.stream_routed_chat_message(
                user_id=user.id,
                message="Where can I recycle it near me?",
                image_data_url=None,
            )
        )

    nearby_event = next(event for event in events if event.get("type") == "nearby_results")
    replayed_text = "".join(str(event.get("content", "")) for event in events if event.get("type") == "delta")

    assert not any(event.get("type") == "stage_start" for event in events)
    assert nearby_event["data"]["suppress_completion_audit"] is True
    assert nearby_event["data"]["nearby_locations"][0]["name"] == "Xiaowuji Large Solid Waste Transfer Station"
    assert "Nearby Disposal Locations Found" in replayed_text
    assert events[-1] == {"type": "done", "stream_stage": "completed"}


def test_stream_routed_chat_message_replays_clarification_options(app, monkeypatch):
    from app.services.ai import ai_decision_engine

    monkeypatch.setattr(
        ai_decision_engine,
        "decide_message",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("demo replay should not call AI routing")),
    )

    with app.app_context():
        monkeypatch.setitem(app.config, "AI_DEMO_REPLAY_ENABLED", True)
        user = _make_user()

        events = list(
            ai_conversation_service.stream_routed_chat_message(
                user_id=user.id,
                message="What should I do with this one now?",
                image_data_url=None,
            )
        )
        messages = _messages_for_conversation(events[0]["conversation_id"])

    clarification_event = next(event for event in events if event.get("type") == "clarification")

    assert not any(event.get("type") == "delta" for event in events)
    assert clarification_event["data"]["question"] == (
        "I found two recycling items in this chat. Are you asking about the plastic bottle or the power bank?"
    )
    assert clarification_event["data"]["options"] == [
        {"label": "Plastic bottle", "reply_text": "I mean the plastic bottle."},
        {"label": "Power bank", "reply_text": "I mean the power bank."},
    ]
    assert messages[-1].message_type == "tool_result"
    assert events[-1] == {"type": "done", "stream_stage": "clarification"}


def test_stream_routed_chat_message_falls_through_when_demo_disabled(app, monkeypatch):
    image_data_url = _seed_image_data_url("dual-case-recycling-chat-message-01-image_url.jpg")
    calls = {"count": 0}

    def fake_decision_engine(**kwargs):
        calls["count"] += 1
        return {
            "intent": "general_chat",
            "needs_clarification": False,
            "prompt_memory": {},
            "memory_candidates": [],
            "should_retrieve_forum": False,
            "context": {},
        }

    from app.services.ai import ai_decision_engine

    monkeypatch.setattr(ai_decision_engine, "decide_message", fake_decision_engine)
    monkeypatch.setattr(
        ai_conversation_service,
        "stream_chat_with_openrouter",
        lambda **kwargs: iter(
            [
                {"type": "meta", "model": "test-model"},
                {"type": "delta", "content": "live reply"},
                {"type": "done"},
            ]
        ),
    )

    with app.app_context():
        monkeypatch.setitem(app.config, "AI_DEMO_REPLAY_ENABLED", False)
        events = list(
            ai_conversation_service.stream_routed_chat_message(
                user_id=None,
                message="How should I recycle this one",
                image_data_url=image_data_url,
            )
        )

    assert calls["count"] == 1
    assert any(event.get("content") == "live reply" for event in events)
