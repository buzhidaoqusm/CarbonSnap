"""Integration tests for persisted AI conversation APIs."""

from __future__ import annotations

import json

from sqlalchemy import select

from app.extensions.db import db
from app.models.ai import AIConversation, AIMessage, RecyclingCase
from app.models.ledger import Transaction
from app.models.memory import UserMemoryItem
from app.services.ai import ai_conversation_service, ai_decision_engine, recycling_analysis_service

_VALID_IMAGE_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0vcAAAAASUVORK5CYII="
)


def _fake_general_chat_decision(*, conversation_id=None, **kwargs):
    return {
        "engine_version": "decision-engine-test",
        "pipeline_label": "test",
        "intent": "general_chat",
        "follow_up_type": None,
        "confidence": 0.9,
        "needs_clarification": False,
        "should_retrieve_forum": False,
        "forum_retrieval_reason": "not_triggered",
        "forum_citation_policy": "mixed_strict_for_facts",
        "memory_candidates": [],
        "prompt_memory": {},
        "context": {},
        "trace": {
            "schema_version": "graph-agent-trace-v1",
            "user_id": kwargs.get("user_id"),
            "conversation_id": conversation_id,
            "message_id": None,
            "router": {"intent": "general_chat"},
            "retrieval": {"forum": {"enabled": False}, "neo4j": {"enabled": False}},
            "prompt_versions": {"router": "decision-engine-test"},
        },
    }


def _post_json(client, url, data, headers=None, buffered=False):
    return client.post(
        url,
        data=json.dumps(data),
        content_type="application/json",
        headers=headers,
        buffered=buffered,
    )


def _extract_sse_payloads(response) -> list[dict]:
    body = response.get_data(as_text=True)
    data_lines = [line for line in body.splitlines() if line.startswith("data: ")]
    return [json.loads(line.removeprefix("data: ")) for line in data_lines]


class TestChatPersistenceApi:
    def test_authenticated_chat_persists_conversation_and_messages(
        self, client, make_auth_headers, monkeypatch, app
    ):
        app.config["AI_DEMO_REPLAY_ENABLED"] = False
        _, headers = make_auth_headers()

        def fake_chat_with_openrouter(**kwargs):
            return {
                "reply": "Persisted reply",
                "model": "test-model",
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 2,
                    "total_tokens": 3,
                },
            }

        monkeypatch.setattr(ai_decision_engine, "decide_message", _fake_general_chat_decision)
        monkeypatch.setattr(
            ai_conversation_service, "chat_with_openrouter", fake_chat_with_openrouter
        )

        response = _post_json(client, "/api/ai/chat", {"message": "Hello"}, headers)

        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["reply"] == "Persisted reply"
        assert isinstance(data["conversation_id"], int)
        assert isinstance(data["user_message_id"], int)
        assert isinstance(data["assistant_message_id"], int)
        assert data["trace"]["schema_version"] == "graph-agent-trace-v1"
        assert data["trace"]["conversation_id"] == data["conversation_id"]
        assert data["trace"]["prompt_versions"]["general_chat_answer"] == "general-chat-answer-v1"

        history_response = client.get(
            f"/api/ai/conversations/{data['conversation_id']}/messages",
            headers=headers,
        )
        assert history_response.status_code == 200
        history = history_response.get_json()["data"]
        assert history["conversation"]["id"] == data["conversation_id"]
        assert [item["role"] for item in history["items"]] == ["user", "assistant"]
        assert history["items"][0]["content_text"] == "Hello"
        assert history["items"][1]["content_text"] == "Persisted reply"
        assert history["items"][1]["trace"]["schema_version"] == "graph-agent-trace-v1"
        assert history["items"][1]["trace"]["conversation_id"] == data["conversation_id"]
        assert (
            history["items"][1]["trace"]["prompt_versions"]["general_chat_answer"]
            == "general-chat-answer-v1"
        )

    def test_authenticated_chat_history_exposes_uploaded_image_url(
        self, client, make_auth_headers, monkeypatch
    ):
        _, headers = make_auth_headers()

        monkeypatch.setattr(
            ai_conversation_service,
            "chat_with_openrouter",
            lambda **kwargs: {"reply": "Image persisted", "model": "test-model", "usage": {}},
        )

        response = _post_json(
            client,
            "/api/ai/chat",
            {
                "message": "Look at this image",
                "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0vcAAAAASUVORK5CYII=",
            },
            headers,
        )
        conversation_id = response.get_json()["data"]["conversation_id"]

        history_response = client.get(
            f"/api/ai/conversations/{conversation_id}/messages",
            headers=headers,
        )
        history = history_response.get_json()["data"]
        image_url = history["items"][0]["image_url"]

        assert image_url.startswith("/api/uploads/chat/")
        image_response = client.get(image_url)
        assert image_response.status_code == 200

    def test_authenticated_chat_accepts_image_without_text(
        self, client, make_auth_headers, monkeypatch
    ):
        _, headers = make_auth_headers()
        captured_request = {}

        def fake_chat_with_openrouter(**kwargs):
            captured_request.update(kwargs)
            return {"reply": "Image-only reply", "model": "test-model", "usage": {}}

        monkeypatch.setattr(ai_decision_engine, "decide_message", _fake_general_chat_decision)
        monkeypatch.setattr(
            ai_conversation_service, "chat_with_openrouter", fake_chat_with_openrouter
        )

        response = _post_json(
            client,
            "/api/ai/chat",
            {
                "image": _VALID_IMAGE_DATA_URL,
            },
            headers,
        )

        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["reply"] == "Image-only reply"
        assert captured_request["user_message"] == ""
        assert captured_request["image_data_url"] == _VALID_IMAGE_DATA_URL

        history_response = client.get(
            f"/api/ai/conversations/{data['conversation_id']}/messages",
            headers=headers,
        )
        history = history_response.get_json()["data"]

        assert history["conversation"]["title"] == "Image discussion"
        assert history["items"][0]["message_type"] == "image"
        assert history["items"][0]["content_text"] == ""
        assert history["items"][0]["image_url"].startswith("/api/uploads/chat/")

    def test_unauthenticated_chat_requires_login(self, client, monkeypatch):
        def fake_chat_with_openrouter(**kwargs):
            return {"reply": "Anonymous reply", "model": "test-model", "usage": {}}

        monkeypatch.setattr(
            ai_conversation_service, "chat_with_openrouter", fake_chat_with_openrouter
        )

        response = _post_json(client, "/api/ai/chat", {"message": "Hi"})

        assert response.status_code == 401

    def test_unauthenticated_stream_chat_requires_login(self, client, monkeypatch):
        def fake_stream_chat_with_openrouter(**kwargs):
            yield {"type": "delta", "content": "Anonymous stream"}

        monkeypatch.setattr(
            ai_conversation_service,
            "stream_chat_with_openrouter",
            fake_stream_chat_with_openrouter,
        )

        response = _post_json(client, "/api/ai/chat/stream", {"message": "Hi"}, buffered=True)

        assert response.status_code == 401

    def test_stream_chat_persists_after_completion(
        self, client, make_auth_headers, monkeypatch, app
    ):
        app.config["AI_DEMO_REPLAY_ENABLED"] = False
        _, headers = make_auth_headers()

        def fake_stream_chat_with_openrouter(**kwargs):
            yield {"type": "meta", "model": "test-model"}
            yield {"type": "delta", "content": "Streamed"}
            yield {"type": "delta", "content": " reply"}
            yield {"type": "done", "finish_reason": "stop"}

        monkeypatch.setattr(
            ai_conversation_service,
            "stream_chat_with_openrouter",
            fake_stream_chat_with_openrouter,
        )
        monkeypatch.setattr(ai_decision_engine, "decide_message", _fake_general_chat_decision)

        response = _post_json(
            client, "/api/ai/chat/stream", {"message": "Hello"}, headers, buffered=True
        )

        assert response.status_code == 200
        payloads = _extract_sse_payloads(response)
        assert payloads

        conversation_id = None
        done_payload = None
        for payload in payloads:
            if payload.get("type") == "done":
                conversation_id = payload["conversation_id"]
                done_payload = payload
                break

        assert conversation_id is not None
        assert done_payload["trace"]["schema_version"] == "graph-agent-trace-v1"
        assert done_payload["trace"]["conversation_id"] == conversation_id
        assert (
            done_payload["trace"]["prompt_versions"]["general_chat_answer"]
            == "general-chat-answer-v1"
        )

        history_response = client.get(
            f"/api/ai/conversations/{conversation_id}/messages",
            headers=headers,
        )
        assert history_response.status_code == 200
        history = history_response.get_json()["data"]
        assert [item["role"] for item in history["items"]] == ["user", "assistant"]
        assert history["items"][1]["content_text"] == "Streamed reply"
        assert history["items"][1]["trace"]["schema_version"] == "graph-agent-trace-v1"


class TestConversationListingApi:
    def test_conversations_are_listed_latest_first_and_user_scoped(
        self,
        client,
        make_auth_headers,
        monkeypatch,
    ):
        _, user1_headers = make_auth_headers()
        _, user2_headers = make_auth_headers()

        def fake_chat_with_openrouter(**kwargs):
            return {"reply": f"reply:{kwargs['user_message']}", "model": "test-model", "usage": {}}

        monkeypatch.setattr(
            ai_conversation_service, "chat_with_openrouter", fake_chat_with_openrouter
        )

        first_response = _post_json(client, "/api/ai/chat", {"message": "First"}, user1_headers)
        second_response = _post_json(client, "/api/ai/chat", {"message": "Second"}, user1_headers)
        _post_json(client, "/api/ai/chat", {"message": "Other user"}, user2_headers)

        list_response = client.get(
            "/api/ai/conversations?page=1&per_page=20", headers=user1_headers
        )
        assert list_response.status_code == 200
        payload = list_response.get_json()["data"]

        assert payload["total"] == 2
        assert len(payload["items"]) == 2
        assert payload["items"][0]["id"] == second_response.get_json()["data"]["conversation_id"]
        assert payload["items"][1]["id"] == first_response.get_json()["data"]["conversation_id"]

        other_list_response = client.get("/api/ai/conversations", headers=user2_headers)
        other_payload = other_list_response.get_json()["data"]
        assert other_payload["total"] == 1

    def test_message_history_endpoint_requires_authentication(self, client):
        response = client.get("/api/ai/conversations/1/messages")
        assert response.status_code == 401

    def test_delete_conversation_removes_history_and_unlinks_memory(
        self, client, make_auth_headers, monkeypatch
    ):
        _, headers = make_auth_headers()

        monkeypatch.setattr(
            ai_conversation_service,
            "chat_with_openrouter",
            lambda **kwargs: {"reply": "Delete me", "model": "test-model", "usage": {}},
        )

        create_response = _post_json(
            client, "/api/ai/chat", {"message": "Delete this chat"}, headers
        )
        conversation_id = create_response.get_json()["data"]["conversation_id"]
        conversation = db.session.get(AIConversation, conversation_id)

        first_message = db.session.scalar(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation_id)
            .order_by(AIMessage.id.asc())
        )
        memory_item = UserMemoryItem(
            user_id=conversation.user_id,
            memory_type="response_style",
            memory_key="response_style",
            value_json=json.dumps({"value": "concise"}),
            source_type="explicit_chat",
            source_message_id=first_message.id,
            conversation_id=conversation_id,
        )
        db.session.add(memory_item)
        db.session.commit()

        delete_response = client.delete(f"/api/ai/conversations/{conversation_id}", headers=headers)

        assert delete_response.status_code == 200
        assert delete_response.get_json()["data"]["deleted_conversation_id"] == conversation_id

        list_response = client.get("/api/ai/conversations?page=1&per_page=20", headers=headers)
        assert list_response.status_code == 200
        assert list_response.get_json()["data"]["total"] == 0

        history_response = client.get(
            f"/api/ai/conversations/{conversation_id}/messages",
            headers=headers,
        )
        assert history_response.status_code == 404

        refreshed_memory = db.session.get(UserMemoryItem, memory_item.id)
        assert refreshed_memory is not None
        assert refreshed_memory.conversation_id is None
        assert refreshed_memory.source_message_id is None


class TestRecyclingPersistenceApi:
    def test_authenticated_recycling_analysis_creates_pending_case_without_transaction(
        self,
        client,
        make_auth_headers,
        monkeypatch,
    ):
        _, headers = make_auth_headers()

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
            yield {"type": "delta", "content": "Stage 1 persisted summary"}
            yield {"type": "done", "finish_reason": "stop"}

        monkeypatch.setattr(recycling_analysis_service, "stream_text", fake_stream_text)

        response = _post_json(
            client,
            "/api/ai/analyze-image",
            {
                "message": "Please analyze this bottle",
                "image": _VALID_IMAGE_DATA_URL,
            },
            headers,
            buffered=True,
        )

        assert response.status_code == 200
        payloads = _extract_sse_payloads(response)
        stage_payloads = [payload for payload in payloads if payload.get("type") == "stage_payload"]
        assert len(stage_payloads) == 2

        persisted_payload = stage_payloads[-1]["data"]
        assert isinstance(persisted_payload["conversation_id"], int)
        assert isinstance(persisted_payload["recycling_case_id"], int)

        conversation = db.session.get(AIConversation, persisted_payload["conversation_id"])
        case = db.session.get(RecyclingCase, persisted_payload["recycling_case_id"])
        transaction_count = db.session.scalar(select(db.func.count(Transaction.id))) or 0

        assert conversation is not None
        assert conversation.status == "awaiting_location"
        assert case is not None
        assert case.status == "pending_audit"
        assert transaction_count == 0

    def test_skip_resume_persists_followup_and_keeps_transactions_empty(
        self,
        client,
        make_auth_headers,
        monkeypatch,
    ):
        _, headers = make_auth_headers()

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
                yield {"type": "delta", "content": "Stage 1 persisted summary"}
            else:
                yield {"type": "delta", "content": "Nearby search skipped follow-up"}
            yield {"type": "done", "finish_reason": "stop"}

        monkeypatch.setattr(recycling_analysis_service, "stream_text", fake_stream_text)

        analyze_response = _post_json(
            client,
            "/api/ai/analyze-image",
            {
                "message": "Please analyze this glass bottle",
                "image": _VALID_IMAGE_DATA_URL,
                "session_id": "integration-skip-session",
            },
            headers,
            buffered=True,
        )
        analyze_payloads = _extract_sse_payloads(analyze_response)
        persisted_payload = [
            payload for payload in analyze_payloads if payload.get("type") == "stage_payload"
        ][-1]["data"]
        conversation_id = persisted_payload["conversation_id"]

        location_response = _post_json(
            client,
            "/api/ai/location-context",
            {
                "session_id": "integration-skip-session",
                "skip_nearby_search": True,
                "permission_state": "denied",
            },
            headers,
        )
        assert location_response.status_code == 200

        resume_response = _post_json(
            client,
            "/api/ai/chat/resume",
            {"session_id": "integration-skip-session"},
            headers,
            buffered=True,
        )
        assert resume_response.status_code == 200
        resume_payloads = _extract_sse_payloads(resume_response)
        assert any(
            payload.get("type") == "delta"
            and payload.get("content") == "Nearby search skipped follow-up"
            for payload in resume_payloads
        )

        history_response = client.get(
            f"/api/ai/conversations/{conversation_id}/messages",
            headers=headers,
        )
        history = history_response.get_json()["data"]
        assert [item["message_type"] for item in history["items"]] == [
            "image",
            "analysis_result",
            "tool_result",
        ]
        assert history["items"][-1]["content_text"] == "Nearby search skipped follow-up"
        assert history["pending_recycling_case"]["id"] == persisted_payload["recycling_case_id"]
        assert history["pending_recycling_case"]["status"] == "pending_audit"
        assert history["items"][1]["recycling_case"]["id"] == persisted_payload["recycling_case_id"]
        assert history["items"][0]["image_url"].startswith("/api/uploads/recycling-analysis/")

        conversation = db.session.get(AIConversation, conversation_id)
        transaction_count = db.session.scalar(select(db.func.count(Transaction.id))) or 0
        assert conversation.status == "completed"
        assert transaction_count == 0
