from __future__ import annotations

import json

from flask_jwt_extended import create_access_token

from app.services.ai import ai_conversation_service, recycling_analysis_service


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


class TestAiMemoryApi:
    def test_get_memory_returns_empty_payload_when_jwt_user_is_missing(
        self,
        client,
        app,
    ):
        with app.app_context():
            token = create_access_token(identity="1")

        response = client.get("/api/ai/memory", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        payload = response.get_json()["data"]
        assert payload["items"] == []
        assert payload["summary"]["action_preferences"]["response_style"] is None

    def test_generic_chat_with_explicit_preference_creates_memory_item(
        self,
        client,
        make_auth_headers,
        monkeypatch,
    ):
        _, headers = make_auth_headers()

        captured_prompt_memory = {}

        def fake_chat_with_openrouter(**kwargs):
            captured_prompt_memory.update(kwargs.get("prompt_memory") or {})
            return {"reply": "Sure, I will keep it concise.", "model": "test-model", "usage": {}}

        monkeypatch.setattr(
            ai_conversation_service, "chat_with_openrouter", fake_chat_with_openrouter
        )
        monkeypatch.setattr(
            "app.services.ai.memory_extractor.complete_json_diagnostic",
            lambda **kwargs: {
                "payload": {
                    "is_explicit_preference": True,
                    "memory_candidates": [
                        {
                            "memory_type": "response_style",
                            "memory_key": "response_style",
                            "value": {"value": "concise"},
                        }
                    ],
                },
                "raw_reply": '{"is_explicit_preference":true}',
                "error": None,
            },
        )

        response = _post_json(
            client,
            "/api/ai/chat",
            {"message": "Please answer more concisely from now on."},
            headers,
        )

        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["memory_updates"][0]["memory_type"] == "response_style"
        assert captured_prompt_memory["action_preferences"]["response_style"] == "concise"

        memory_response = client.get("/api/ai/memory", headers=headers)
        assert memory_response.status_code == 200
        payload = memory_response.get_json()["data"]
        assert payload["summary"]["action_preferences"]["response_style"] == "concise"
        assert payload["items"][0]["memory_key"] == "response_style"

    def test_generic_chat_without_explicit_preference_creates_no_memory_item(
        self,
        client,
        make_auth_headers,
        monkeypatch,
    ):
        _, headers = make_auth_headers()

        monkeypatch.setattr(
            ai_conversation_service,
            "chat_with_openrouter",
            lambda **kwargs: {"reply": "Hello!", "model": "test-model", "usage": {}},
        )

        response = _post_json(client, "/api/ai/chat", {"message": "hello"}, headers)

        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["memory_updates"] == []

        memory_response = client.get("/api/ai/memory", headers=headers)
        payload = memory_response.get_json()["data"]
        assert payload["items"] == []

    def test_delete_ai_memory_soft_deletes_item_and_rebuilds_summary(
        self,
        client,
        make_auth_headers,
    ):
        _, headers = make_auth_headers()

        create_response = _post_json(
            client,
            "/api/ai/memory",
            {
                "memory_type": "response_style",
                "memory_key": "response_style",
                "value": {"value": "concise"},
            },
            headers,
        )
        assert create_response.status_code == 200
        item_id = create_response.get_json()["data"]["item"]["id"]

        delete_response = client.delete(f"/api/ai/memory/{item_id}", headers=headers)
        assert delete_response.status_code == 200

        payload = delete_response.get_json()["data"]
        assert payload["item"]["status"] == "deleted"
        assert payload["summary"]["action_preferences"]["response_style"] is None

    def test_recycling_flow_uses_stored_memory_summary(
        self,
        client,
        make_auth_headers,
        monkeypatch,
    ):
        _, headers = make_auth_headers()

        _post_json(
            client,
            "/api/ai/memory",
            {
                "memory_type": "recycling_preference",
                "memory_key": "prefer_nearby_options",
                "value": {"value": False},
            },
            headers,
        )

        captured_prompt_memory = {}

        def fake_analyze_stage1(**kwargs):
            captured_prompt_memory.update(kwargs.get("prompt_memory") or {})
            return {
                "waste_type": "battery",
                "confidence": 0.88,
                "estimated_weight_kg": 0.2,
                "co2_saved_kg": 0.4,
                "carbon_points": 4.0,
                "recycle_suggestions": ["Use a verified drop-off point."],
                "forum_references": [],
                "requires_location_decision": False,
            }

        def fake_stream_text(**kwargs):
            yield {"type": "meta", "model": "test-model"}
            yield {"type": "delta", "content": "Battery recycling guidance"}
            yield {"type": "done", "finish_reason": "stop"}

        monkeypatch.setattr(recycling_analysis_service, "_analyze_stage1", fake_analyze_stage1)
        monkeypatch.setattr(recycling_analysis_service, "stream_text", fake_stream_text)

        response = _post_json(
            client,
            "/api/ai/analyze-image",
            {"message": "Analyze this battery", "session_id": "memory-recycling-test"},
            headers,
            buffered=True,
        )

        assert response.status_code == 200
        payloads = _extract_sse_payloads(response)
        assert any(payload.get("type") == "done" for payload in payloads)
        assert captured_prompt_memory["action_preferences"]["prefer_nearby_options"] is False

        memory_response = client.get("/api/ai/memory", headers=headers)
        memory_payload = memory_response.get_json()["data"]
        assert any(
            topic["topic_id"] == "battery-recycling"
            for topic in memory_payload["summary"]["content_interest_preferences"]["topics"]
        )
