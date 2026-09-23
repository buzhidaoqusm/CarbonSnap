"""Unit tests for persisted AI conversation service behavior."""

from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.ai import AIConversation, AIMessage, RecyclingAuditAttempt, RecyclingCase
from app.models.ledger import Transaction
from app.models.memory import UserMemoryItem
from app.models.user import User
from app.services.ai import ai_conversation_service, recycling_analysis_service
from app.services.ai.agent_trace_service import build_trace_shell

_VALID_IMAGE_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0vcAAAAASUVORK5CYII="
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


def _messages_for_conversation(conversation_id: int) -> list[AIMessage]:
    return list(
        db.session.scalars(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation_id)
            .order_by(AIMessage.sequence_no.asc(), AIMessage.id.asc())
        )
    )


class TestCompleteChatMessage:
    def test_persists_authenticated_conversation_and_messages(self, monkeypatch):
        user = _make_user()

        def fake_chat_with_openrouter(**kwargs):
            assert kwargs["user_message"] == "Hello"
            assert kwargs["history"] == []
            return {
                "reply": "Hi there!",
                "model": "test-model",
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 2,
                    "total_tokens": 3,
                },
            }

        monkeypatch.setattr(
            ai_conversation_service, "chat_with_openrouter", fake_chat_with_openrouter
        )

        result = ai_conversation_service.complete_chat_message(
            user_id=user.id,
            message="Hello",
            history=[],
        )

        conversation = db.session.get(AIConversation, result["conversation_id"])
        messages = _messages_for_conversation(conversation.id)

        assert conversation is not None
        assert conversation.user_id == user.id
        assert result["reply"] == "Hi there!"
        assert result["user_message_id"] == messages[0].id
        assert result["assistant_message_id"] == messages[1].id
        assert [message.role for message in messages] == ["user", "assistant"]
        assert messages[0].content_text == "Hello"
        assert messages[1].content_text == "Hi there!"
        assert json.loads(messages[0].content_json) == {"has_image": False}

    def test_persists_image_metadata_for_user_messages(self, monkeypatch):
        user = _make_user("imageuser", "imageuser@example.com")

        def fake_chat_with_openrouter(**kwargs):
            return {"reply": "Image reply", "model": "test-model", "usage": {}}

        monkeypatch.setattr(
            ai_conversation_service, "chat_with_openrouter", fake_chat_with_openrouter
        )

        image_data_url = _VALID_IMAGE_DATA_URL
        result = ai_conversation_service.complete_chat_message(
            user_id=user.id,
            message="Please inspect this image",
            history=[],
            image_data_url=image_data_url,
        )

        messages = _messages_for_conversation(result["conversation_id"])
        assert messages[0].message_type == "image"
        payload = json.loads(messages[0].content_json)
        assert payload["has_image"] is True
        assert payload["image_url"].startswith("/api/uploads/chat/")

    def test_complete_chat_message_persists_used_forum_references(self, monkeypatch):
        user = _make_user("forumrefs", "forumrefs@example.com")

        monkeypatch.setattr(
            ai_conversation_service,
            "chat_with_openrouter",
            lambda **kwargs: {
                "reply": "Community advice suggests rinsing first. [Bottle Sorting Guide](/forum/posts/7)",
                "model": "test-model",
                "usage": {},
            },
        )
        monkeypatch.setattr(
            ai_conversation_service,
            "retrieve_forum_references",
            lambda **kwargs: {
                "candidates": [
                    {
                        "reference_id": "forum-post-7",
                        "post_id": 7,
                        "title": "Bottle Sorting Guide",
                        "url": "/forum/posts/7",
                        "excerpt": "Rinse first.",
                        "retrieval_reason": "keyword+vector",
                    }
                ]
            },
        )

        result = ai_conversation_service.complete_chat_message(
            user_id=user.id,
            message="How should I recycle a bottle?",
            history=[],
            decision={
                "intent": "general_chat",
                "should_retrieve_forum": True,
                "target_case_id": None,
                "context": {},
                "trace": build_trace_shell(
                    user_id=user.id,
                    conversation_id=None,
                    intent="general_chat",
                ),
            },
        )

        messages = _messages_for_conversation(result["conversation_id"])
        assistant_payload = json.loads(messages[1].content_json)

        assert result["forum_references"] == [
            {
                "reference_id": "forum-post-7",
                "post_id": 7,
                "title": "Bottle Sorting Guide",
                "url": "/forum/posts/7",
            }
        ]
        assert assistant_payload["forum_references"] == result["forum_references"]
        assert result["trace"]["retrieval"]["forum"]["citation_count"] == 1
        assert result["trace"]["retrieval"]["forum"]["citations"] == result["forum_references"]
        assert (
            assistant_payload["trace"]["retrieval"]["forum"]["citations"]
            == result["forum_references"]
        )

    def test_complete_chat_message_fuses_graph_and_forum_context_into_trace(self, monkeypatch):
        user = _make_user("graphfuse", "graphfuse@example.com")
        captured_request = {}

        monkeypatch.setattr(
            ai_conversation_service,
            "retrieve_forum_references",
            lambda **kwargs: {
                "candidates": [
                    {
                        "reference_id": "forum-post-17",
                        "post_id": 17,
                        "title": "Battery drawer reset",
                        "url": "/forum/posts/17",
                        "excerpt": "Drop-off day helped.",
                        "retrieval_reason": "keyword",
                    }
                ]
            },
        )
        monkeypatch.setattr(
            ai_conversation_service,
            "_retrieve_graph_context",
            lambda message, decision: {
                "enabled": True,
                "entities": {
                    "items": ["battery"],
                    "materials": [],
                    "matches": [{"canonical": "battery", "matched": ["batteries"]}],
                },
                "paths": [
                    {"from": "battery", "relation": "HAS_RISK", "to": "fire hazard"},
                    {"from": "battery", "relation": "DISPOSE_AS", "to": "hazardous drop-off"},
                ],
                "rules": [
                    {
                        "id": "rule-battery-dropoff",
                        "title": "Use battery drop-off",
                        "description": "Use a battery collection point.",
                    }
                ],
                "risks": [{"name": "fire hazard", "severity": "high"}],
                "facility_types": ["household hazardous waste facility"],
                "knowledge_chunks": [],
                "confidence": "medium",
            },
        )

        def fake_chat_with_openrouter(**kwargs):
            captured_request.update(kwargs)
            return {
                "reply": "Use a battery collection point, and see [Battery drawer reset](/forum/posts/17).",
                "model": "test-model",
                "usage": {},
            }

        monkeypatch.setattr(
            ai_conversation_service, "chat_with_openrouter", fake_chat_with_openrouter
        )

        result = ai_conversation_service.complete_chat_message(
            user_id=user.id,
            message="Where do I drop off batteries?",
            history=[],
            decision={
                "intent": "general_chat",
                "should_retrieve_forum": True,
                "target_case_id": None,
                "context": {},
                "trace": build_trace_shell(
                    user_id=user.id,
                    conversation_id=None,
                    intent="general_chat",
                ),
            },
        )

        assert "Forum post references available" in captured_request["system_prompt"]
        assert "Neo4j recycling graph evidence" in captured_request["system_prompt"]
        assert "battery --HAS_RISK--> fire hazard" in captured_request["system_prompt"]
        assert result["trace"]["retrieval"]["forum"]["citation_count"] == 1
        assert result["trace"]["retrieval"]["neo4j"]["enabled"] is True
        assert result["trace"]["retrieval"]["neo4j"]["path_count"] == 2
        assert result["trace"]["retrieval"]["neo4j"]["rules"][0]["id"] == "rule-battery-dropoff"
        assert result["trace"]["entity_extraction"]["items"] == ["battery"]

    def test_complete_chat_message_attaches_open_graph_forum_sources(self, monkeypatch):
        user = _make_user("opengraph", "opengraph@example.com")

        monkeypatch.setattr(
            ai_conversation_service,
            "retrieve_forum_references",
            lambda **kwargs: {"candidates": []},
        )
        monkeypatch.setattr(
            ai_conversation_service,
            "_retrieve_graph_context",
            lambda message, decision: {
                "enabled": True,
                "entities": {"items": ["plastic bottle"], "materials": [], "matches": []},
                "paths": [],
                "rules": [],
                "risks": [],
                "facility_types": [],
                "knowledge_chunks": [],
                "open_claims": [{"id": "claim-1", "raw_predicate": "upcycle into"}],
                "relation_facts": [
                    {
                        "id": "fact-1",
                        "subject": "plastic bottle",
                        "relation": "can be reused as",
                        "object": "lantern",
                        "support_count": 2,
                    }
                ],
                "forum_citations": [
                    {
                        "reference_id": "forum-post-12",
                        "post_id": 12,
                        "title": "Bottle lantern ideas",
                        "url": "/forum/posts/12",
                    }
                ],
                "source_evidence": [{"id": "evidence-1"}],
                "confidence": "medium",
            },
        )
        monkeypatch.setattr(
            ai_conversation_service,
            "chat_with_openrouter",
            lambda **kwargs: {
                "reply": "You can reuse plastic bottles as lantern crafts.",
                "model": "test-model",
                "usage": {},
            },
        )

        result = ai_conversation_service.complete_chat_message(
            user_id=user.id,
            message="plastic bottle lantern ideas",
            history=[],
            decision={
                "intent": "general_chat",
                "should_retrieve_forum": True,
                "target_case_id": None,
                "context": {},
                "trace": build_trace_shell(
                    user_id=user.id,
                    conversation_id=None,
                    intent="general_chat",
                ),
            },
        )

        assert result["forum_references"] == [
            {
                "reference_id": "forum-post-12",
                "post_id": 12,
                "title": "Bottle lantern ideas",
                "url": "/forum/posts/12",
            }
        ]
        assert result["trace"]["retrieval"]["neo4j"]["relation_fact_count"] == 1
        assert result["trace"]["retrieval"]["neo4j"]["source_count"] == 1

    def test_complete_chat_message_records_graph_fallback_when_feature_disabled(
        self, monkeypatch, app
    ):
        app.config["AI_NEO4J_GRAPHRAG_ENABLED"] = False
        user = _make_user("graphoff", "graphoff@example.com")
        captured_request = {}

        def fake_chat_with_openrouter(**kwargs):
            captured_request.update(kwargs)
            return {
                "reply": "Check your local rules for batteries.",
                "model": "test-model",
                "usage": {},
            }

        monkeypatch.setattr(
            ai_conversation_service, "chat_with_openrouter", fake_chat_with_openrouter
        )

        result = ai_conversation_service.complete_chat_message(
            user_id=user.id,
            message="Where do I drop off batteries?",
            history=[],
            decision={
                "intent": "general_chat",
                "should_retrieve_forum": False,
                "target_case_id": None,
                "context": {},
                "trace": build_trace_shell(
                    user_id=user.id,
                    conversation_id=None,
                    intent="general_chat",
                ),
            },
        )

        assert "Neo4j recycling graph evidence" not in captured_request["system_prompt"]
        assert "External evidence note" in captured_request["system_prompt"]
        assert result["trace"]["retrieval"]["neo4j"]["enabled"] is False
        assert result["trace"]["retrieval"]["neo4j"]["fallback_reason"] == "feature_disabled"
        assert result["trace"]["entity_extraction"]["items"] == ["battery"]

    def test_complete_chat_message_persists_memory_updates_on_assistant_message(self, monkeypatch):
        user = _make_user("memorypersist", "memorypersist@example.com")

        monkeypatch.setattr(
            ai_conversation_service,
            "chat_with_openrouter",
            lambda **kwargs: {
                "reply": "Understood. I will prioritize nearby drop-off suggestions.",
                "model": "test-model",
                "usage": {},
            },
        )
        monkeypatch.setattr(
            ai_conversation_service,
            "_persist_explicit_memory_candidates",
            lambda **kwargs: [
                {
                    "id": 41,
                    "memory_type": "recycling_preference",
                    "memory_key": "prefer_nearby_options",
                    "value": {"value": True},
                }
            ],
        )

        result = ai_conversation_service.complete_chat_message(
            user_id=user.id,
            message="From now on, I prefer nearby drop-off suggestions first.",
            history=[],
            memory_candidates=[
                {
                    "memory_type": "recycling_preference",
                    "memory_key": "prefer_nearby_options",
                    "value": {"value": True},
                }
            ],
        )

        messages = _messages_for_conversation(result["conversation_id"])
        assistant_payload = json.loads(messages[1].content_json)

        assert result["memory_updates"] == [
            {
                "id": 41,
                "memory_type": "recycling_preference",
                "memory_key": "prefer_nearby_options",
                "value": {"value": True},
            }
        ]
        assert assistant_payload["memory_updates"] == result["memory_updates"]

    def test_reuses_persisted_history_when_conversation_exists(self, monkeypatch):
        user = _make_user("brenda", "brenda@example.com")

        first_reply_calls = []
        second_reply_calls = []

        def fake_chat_with_openrouter(**kwargs):
            history = kwargs["history"]
            if not first_reply_calls:
                first_reply_calls.append(history)
                return {"reply": "First reply", "model": "test-model", "usage": {}}

            second_reply_calls.append(history)
            return {"reply": "Second reply", "model": "test-model", "usage": {}}

        monkeypatch.setattr(
            ai_conversation_service, "chat_with_openrouter", fake_chat_with_openrouter
        )

        first = ai_conversation_service.complete_chat_message(
            user_id=user.id,
            message="First question",
            history=[],
        )
        second = ai_conversation_service.complete_chat_message(
            user_id=user.id,
            message="Second question",
            history=[{"role": "user", "content": "Should be ignored"}],
            conversation_id=first["conversation_id"],
        )

        assert first_reply_calls == [[]]
        assert second_reply_calls[0] == [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First reply"},
        ]
        assert second["conversation_id"] == first["conversation_id"]

    def test_generates_title_from_first_message_once(self, monkeypatch):
        user = _make_user("titles", "titles@example.com")
        generated_titles = []

        monkeypatch.setattr(
            ai_conversation_service,
            "generate_conversation_title",
            lambda **kwargs: (
                generated_titles.append(kwargs["user_message"]) or "Bottle recycling help"
            ),
        )
        monkeypatch.setattr(
            ai_conversation_service,
            "chat_with_openrouter",
            lambda **kwargs: {"reply": "ok", "model": "test-model", "usage": {}},
        )

        first = ai_conversation_service.complete_chat_message(
            user_id=user.id,
            message="How should I recycle this bottle?",
            history=[],
        )
        second = ai_conversation_service.complete_chat_message(
            user_id=user.id,
            message="And what about the cap?",
            history=[],
            conversation_id=first["conversation_id"],
        )

        conversation = db.session.get(AIConversation, first["conversation_id"])

        assert first["conversation_title"] == "Bottle recycling help"
        assert second["conversation_title"] == "Bottle recycling help"
        assert conversation.title == "Bottle recycling help"
        assert generated_titles == ["How should I recycle this bottle?"]

    def test_uses_recent_ten_turns_for_short_term_memory_prompt(self, monkeypatch):
        user = _make_user("turns", "turns@example.com")
        captured_request = {}

        def fake_chat_with_openrouter(**kwargs):
            if kwargs["user_message"] == "What was my previous message?":
                captured_request.update(kwargs)
                return {
                    "reply": "Your previous message was question 11.",
                    "model": "test-model",
                    "usage": {},
                }
            return {"reply": f"reply:{kwargs['user_message']}", "model": "test-model", "usage": {}}

        monkeypatch.setattr(
            ai_conversation_service, "chat_with_openrouter", fake_chat_with_openrouter
        )

        conversation_id = None
        for index in range(12):
            result = ai_conversation_service.complete_chat_message(
                user_id=user.id,
                message=f"question {index}",
                history=[],
                conversation_id=conversation_id,
            )
            conversation_id = result["conversation_id"]

        ai_conversation_service.complete_chat_message(
            user_id=user.id,
            message="What was my previous message?",
            history=[],
            conversation_id=conversation_id,
        )

        assert len(captured_request["history"]) == 20
        assert captured_request["history"][0]["content"] == "question 2"
        assert captured_request["history"][-2]["content"] == "question 11"
        assert "current chat session" in captured_request["system_prompt"]
        assert (
            'Latest user message before this request: "question 11"'
            in captured_request["system_prompt"]
        )


class TestStreamChatMessage:
    def test_persists_after_stream_completion(self, monkeypatch):
        user = _make_user("cora", "cora@example.com")

        def fake_stream_chat_with_openrouter(**kwargs):
            assert kwargs["user_message"] == "Stream this"
            assert kwargs["history"] == []
            yield {"type": "meta", "model": "test-model"}
            yield {"type": "delta", "content": "Hello"}
            yield {"type": "delta", "content": " world"}
            yield {"type": "done", "finish_reason": "stop"}

        monkeypatch.setattr(
            ai_conversation_service,
            "stream_chat_with_openrouter",
            fake_stream_chat_with_openrouter,
        )

        events = list(
            ai_conversation_service.stream_chat_message(
                user_id=user.id,
                message="Stream this",
                history=[],
            )
        )

        conversation_id = events[0]["conversation_id"]
        messages = _messages_for_conversation(conversation_id)

        assert [event["type"] for event in events] == ["meta", "delta", "delta", "done"]
        assert events[0]["user_message_id"] == messages[0].id
        assert events[-1]["assistant_message_id"] == messages[1].id
        assert messages[0].content_text == "Stream this"
        assert messages[1].content_text == "Hello world"

    def test_stream_chat_uses_short_term_memory_prompt(self, monkeypatch):
        user = _make_user("streammem", "streammem@example.com")
        captured_request = {}

        monkeypatch.setattr(
            ai_conversation_service,
            "chat_with_openrouter",
            lambda **kwargs: {"reply": "stored", "model": "test-model", "usage": {}},
        )

        def fake_stream_chat_with_openrouter(**kwargs):
            captured_request.update(kwargs)
            yield {"type": "meta", "model": "test-model"}
            yield {"type": "delta", "content": "Remembered"}
            yield {"type": "done", "finish_reason": "stop"}

        monkeypatch.setattr(
            ai_conversation_service,
            "stream_chat_with_openrouter",
            fake_stream_chat_with_openrouter,
        )

        first = ai_conversation_service.complete_chat_message(
            user_id=user.id,
            message="Please remember this",
            history=[],
        )
        list(
            ai_conversation_service.stream_chat_message(
                user_id=user.id,
                message="What did I just say?",
                history=[],
                conversation_id=first["conversation_id"],
            )
        )

        assert captured_request["history"][-2]["content"] == "Please remember this"
        assert "current chat session" in captured_request["system_prompt"]

    def test_stream_chat_message_emits_and_persists_forum_references(self, monkeypatch):
        user = _make_user("streamrefs", "streamrefs@example.com")

        def fake_stream_chat_with_openrouter(**kwargs):
            yield {"type": "meta", "model": "test-model"}
            yield {"type": "delta", "content": "Follow "}
            yield {"type": "delta", "content": "[Bottle Sorting Guide](/forum/posts/9)"}
            yield {"type": "done", "finish_reason": "stop"}

        monkeypatch.setattr(
            ai_conversation_service,
            "stream_chat_with_openrouter",
            fake_stream_chat_with_openrouter,
        )
        monkeypatch.setattr(
            ai_conversation_service,
            "retrieve_forum_references",
            lambda **kwargs: {
                "candidates": [
                    {
                        "reference_id": "forum-post-9",
                        "post_id": 9,
                        "title": "Bottle Sorting Guide",
                        "url": "/forum/posts/9",
                        "excerpt": "Separate caps.",
                        "retrieval_reason": "keyword+vector",
                    }
                ]
            },
        )

        events = list(
            ai_conversation_service.stream_chat_message(
                user_id=user.id,
                message="Need bottle advice",
                history=[],
                decision={
                    "intent": "general_chat",
                    "should_retrieve_forum": True,
                    "target_case_id": None,
                    "context": {},
                    "trace": build_trace_shell(
                        user_id=user.id,
                        conversation_id=None,
                        intent="general_chat",
                    ),
                },
            )
        )

        messages = _messages_for_conversation(events[0]["conversation_id"])
        assistant_payload = json.loads(messages[1].content_json)

        assert events[-1]["forum_references"] == [
            {
                "reference_id": "forum-post-9",
                "post_id": 9,
                "title": "Bottle Sorting Guide",
                "url": "/forum/posts/9",
            }
        ]
        assert assistant_payload["forum_references"] == events[-1]["forum_references"]
        assert events[-1]["trace"]["retrieval"]["forum"]["citation_count"] == 1
        assert (
            events[-1]["trace"]["retrieval"]["forum"]["citations"] == events[-1]["forum_references"]
        )
        assert (
            assistant_payload["trace"]["retrieval"]["forum"]["citations"]
            == events[-1]["forum_references"]
        )


class TestConversationListing:
    def test_list_user_conversations_returns_latest_first(self, monkeypatch):
        user = _make_user("dylan", "dylan@example.com")

        def fake_chat_with_openrouter(**kwargs):
            return {"reply": kwargs["user_message"].upper(), "model": "test-model", "usage": {}}

        monkeypatch.setattr(
            ai_conversation_service, "chat_with_openrouter", fake_chat_with_openrouter
        )

        first = ai_conversation_service.complete_chat_message(user_id=user.id, message="one")
        second = ai_conversation_service.complete_chat_message(user_id=user.id, message="two")

        result = ai_conversation_service.list_user_conversations(
            user_id=user.id, page=1, per_page=10
        )

        assert result["total"] == 2
        assert [item["id"] for item in result["items"]] == [
            second["conversation_id"],
            first["conversation_id"],
        ]

    def test_get_conversation_messages_serializes_ordered_history(self, monkeypatch):
        user = _make_user("erin", "erin@example.com")

        def fake_chat_with_openrouter(**kwargs):
            return {
                "reply": f"reply to {kwargs['user_message']}",
                "model": "test-model",
                "usage": {},
            }

        monkeypatch.setattr(
            ai_conversation_service, "chat_with_openrouter", fake_chat_with_openrouter
        )

        created = ai_conversation_service.complete_chat_message(user_id=user.id, message="hello")
        payload = ai_conversation_service.get_conversation_messages(
            user_id=user.id,
            conversation_id=created["conversation_id"],
        )

        assert payload["conversation"]["id"] == created["conversation_id"]
        assert payload["total"] == 2
        assert [item["role"] for item in payload["items"]] == ["user", "assistant"]
        assert [item["sequence_no"] for item in payload["items"]] == [1, 2]

    def test_get_conversation_messages_includes_case_audit_attempts(self, monkeypatch):
        user = _make_user("gina", "gina@example.com")

        monkeypatch.setattr(
            ai_conversation_service,
            "chat_with_openrouter",
            lambda **kwargs: {"reply": "reply to hello", "model": "test-model", "usage": {}},
        )

        created = ai_conversation_service.complete_chat_message(user_id=user.id, message="hello")
        conversation = db.session.get(AIConversation, created["conversation_id"])
        user_message = _messages_for_conversation(created["conversation_id"])[0]

        recycling_case = RecyclingCase(
            user_id=user.id,
            conversation_id=conversation.id,
            origin_message_id=user_message.id,
            waste_type_predicted="portable power bank",
            confidence=0.94,
            estimated_weight_kg=0.45,
            expected_co2_saved_kg=0.4,
            expected_carbon_points=4.5,
            status="audit_failed",
            latest_audit_attempt_no=2,
        )
        db.session.add(recycling_case)
        db.session.flush()

        first_attempt = RecyclingAuditAttempt(
            recycling_case_id=recycling_case.id,
            user_id=user.id,
            conversation_id=conversation.id,
            audit_image_url="/api/uploads/recycling-audit/attempt-1.png",
            attempt_no=1,
            audit_result="unclear",
            auditor_confidence=0.4,
            audit_reason="The bin type is not clear enough.",
            audit_response_json=json.dumps({"audit_result": "unclear"}),
        )
        second_attempt = RecyclingAuditAttempt(
            recycling_case_id=recycling_case.id,
            user_id=user.id,
            conversation_id=conversation.id,
            audit_image_url="/api/uploads/recycling-audit/attempt-2.png",
            attempt_no=2,
            audit_result="failed",
            auditor_confidence=0.6,
            audit_reason="The item does not appear to be in the correct drop-off path.",
            audit_response_json=json.dumps({"audit_result": "failed"}),
        )
        db.session.add_all([first_attempt, second_attempt])
        db.session.commit()

        payload = ai_conversation_service.get_conversation_messages(
            user_id=user.id,
            conversation_id=created["conversation_id"],
        )

        case_payload = payload["items"][0]["recycling_case"]
        assert case_payload is not None
        assert case_payload["id"] == recycling_case.id
        assert [attempt["attempt_no"] for attempt in case_payload["audit_attempts"]] == [1, 2]
        assert case_payload["audit_attempts"][0]["audit_result"] == "unclear"
        assert case_payload["audit_attempts"][1]["audit_reason"] == (
            "The item does not appear to be in the correct drop-off path."
        )

    def test_delete_user_conversation_removes_conversation_and_unlinks_memory(self, monkeypatch):
        user = _make_user("frank", "frank@example.com")

        monkeypatch.setattr(
            ai_conversation_service,
            "chat_with_openrouter",
            lambda **kwargs: {"reply": "removable", "model": "test-model", "usage": {}},
        )

        created = ai_conversation_service.complete_chat_message(
            user_id=user.id,
            message="temporary chat",
            history=[],
        )
        messages = _messages_for_conversation(created["conversation_id"])
        memory_item = UserMemoryItem(
            user_id=user.id,
            memory_type="response_style",
            memory_key="response_style",
            value_json=json.dumps({"value": "brief"}),
            source_type="explicit_chat",
            source_message_id=messages[0].id,
            conversation_id=created["conversation_id"],
        )
        db.session.add(memory_item)
        db.session.commit()

        result = ai_conversation_service.delete_user_conversation(
            user_id=user.id,
            conversation_id=created["conversation_id"],
        )

        assert result == {"deleted_conversation_id": created["conversation_id"]}
        assert db.session.get(AIConversation, created["conversation_id"]) is None
        assert _messages_for_conversation(created["conversation_id"]) == []

        refreshed_memory = db.session.get(UserMemoryItem, memory_item.id)
        assert refreshed_memory is not None
        assert refreshed_memory.conversation_id is None
        assert refreshed_memory.source_message_id is None


class TestRecyclingAnalysisPersistence:
    def test_authenticated_recycling_analysis_creates_pending_case_without_transaction(
        self,
        monkeypatch,
    ):
        user = _make_user("recycler", "recycler@example.com")

        monkeypatch.setattr(
            recycling_analysis_service, "_get_authenticated_user_id", lambda: user.id
        )
        monkeypatch.setattr(
            recycling_analysis_service,
            "_analyze_stage1",
            lambda **kwargs: {
                "waste_type": "plastic bottle",
                "confidence": 0.91,
                "estimated_weight_kg": 0.2,
                "co2_saved_kg": 0.3,
                "carbon_points": 3.0,
                "recycle_suggestions": ["Rinse it"],
                "forum_references": [],
                "requires_location_decision": True,
            },
        )

        def fake_stream_text(**kwargs):
            yield {"type": "meta", "model": "test-model"}
            yield {"type": "delta", "content": "Stage 1 summary"}
            yield {"type": "done", "finish_reason": "stop"}

        monkeypatch.setattr(recycling_analysis_service, "stream_text", fake_stream_text)

        events = list(
            recycling_analysis_service.stream_recycling_analysis(
                message="Analyze this bottle",
                image_data_url=_VALID_IMAGE_DATA_URL,
                session_id="session-pending-case",
            )
        )

        conversation = db.session.scalar(
            select(AIConversation).where(AIConversation.user_id == user.id)
        )
        messages = _messages_for_conversation(conversation.id)
        case = db.session.scalar(
            select(RecyclingCase).where(RecyclingCase.conversation_id == conversation.id)
        )
        transaction_count = db.session.scalar(select(db.func.count(Transaction.id))) or 0

        assert [event["type"] for event in events] == [
            "meta",
            "stage_start",
            "stage_payload",
            "delta",
            "stage_payload",
            "awaiting_location",
            "done",
        ]
        assert conversation is not None
        assert conversation.status == "awaiting_location"
        assert conversation.current_pending_action == "location_permission"
        assert conversation.session_context_json is not None
        assert [message.message_type for message in messages] == ["image", "analysis_result"]
        assert case is not None
        assert case.status == "pending_audit"
        assert case.waste_type_predicted == "plastic bottle"
        assert transaction_count == 0

    def test_skip_resume_persists_followup_without_transaction(self, monkeypatch):
        user = _make_user("resume", "resume@example.com")

        monkeypatch.setattr(
            recycling_analysis_service, "_get_authenticated_user_id", lambda: user.id
        )
        monkeypatch.setattr(
            recycling_analysis_service,
            "_analyze_stage1",
            lambda **kwargs: {
                "waste_type": "glass bottle",
                "confidence": 0.89,
                "estimated_weight_kg": 0.25,
                "co2_saved_kg": 0.4,
                "carbon_points": 4.0,
                "recycle_suggestions": ["Separate the cap"],
                "forum_references": [],
                "requires_location_decision": True,
            },
        )

        call_counter = {"n": 0}

        def fake_stream_text(**kwargs):
            call_counter["n"] += 1
            yield {"type": "meta", "model": "test-model"}
            if call_counter["n"] == 1:
                yield {"type": "delta", "content": "Stage 1 summary"}
            else:
                yield {"type": "delta", "content": "Nearby search skipped summary"}
            yield {"type": "done", "finish_reason": "stop"}

        monkeypatch.setattr(recycling_analysis_service, "stream_text", fake_stream_text)

        list(
            recycling_analysis_service.stream_recycling_analysis(
                message="Analyze this glass bottle",
                image_data_url=_VALID_IMAGE_DATA_URL,
                session_id="session-skip-flow",
            )
        )
        recycling_analysis_service.store_location_context(
            {
                "session_id": "session-skip-flow",
                "skip_nearby_search": True,
                "permission_state": "denied",
            }
        )
        list(recycling_analysis_service.stream_recycling_resume("session-skip-flow"))

        conversation = db.session.scalar(
            select(AIConversation).where(AIConversation.user_id == user.id)
        )
        messages = _messages_for_conversation(conversation.id)
        transaction_count = db.session.scalar(select(db.func.count(Transaction.id))) or 0

        assert conversation.status == "completed"
        assert conversation.current_pending_action == "none"
        assert [message.message_type for message in messages] == [
            "image",
            "analysis_result",
            "tool_result",
        ]
        assert messages[-1].content_text == "Nearby search skipped summary"
        assert transaction_count == 0
