from __future__ import annotations

import json

from sqlalchemy import select

from app.extensions.db import db
from app.models.ai import AIMessageDecision
from app.services.ai import ai_conversation_service, recycling_analysis_service


def _post_json(client, url, data, headers=None, buffered=False):
    return client.post(
        url,
        data=json.dumps(data),
        content_type="application/json",
        headers=headers,
        buffered=buffered,
    )


def _extract_sse_payloads(response, *, include_heartbeat: bool = False) -> list[dict]:
    body = response.get_data(as_text=True)
    data_lines = [line for line in body.splitlines() if line.startswith("data: ")]
    payloads = [json.loads(line.removeprefix("data: ")) for line in data_lines]
    if include_heartbeat:
        return payloads
    # The stream opens with a heartbeat frame so proxies flush early; tests
    # assert on the semantic events that follow it.
    return [payload for payload in payloads if payload.get("type") != "heartbeat"]


class TestAiDecisionRoutingApi:
    def test_chat_stream_routes_general_chat_through_generic_stream(
        self,
        client,
        make_auth_headers,
        monkeypatch,
    ):
        _, headers = make_auth_headers()

        monkeypatch.setattr(
            "app.services.ai.ai_decision_engine.decide_message",
            lambda **kwargs: {
                "engine_version": "decision-engine-v1",
                "intent": "general_chat",
                "follow_up_type": None,
                "confidence": 0.9,
                "needs_clarification": False,
                "clarification_question": None,
                "clarification_options": [],
                "target_case_id": None,
                "resolution_confidence": None,
                "should_create_new_case": False,
                "memory_candidates": [],
                "context": {},
                "prompt_memory": {},
            },
        )

        def fake_generic_stream(**kwargs):
            yield {"type": "meta", "conversation_id": 1, "conversation_title": "Hello Greeting"}
            yield {"type": "delta", "content": "Hello there"}
            yield {"type": "done", "stream_stage": "completed"}

        monkeypatch.setattr(ai_conversation_service, "stream_chat_message", fake_generic_stream)

        response = _post_json(
            client,
            "/api/ai/chat/stream",
            {"message": "hello"},
            headers,
            buffered=True,
        )

        payloads = _extract_sse_payloads(response)
        assert response.status_code == 200
        assert [payload["type"] for payload in payloads] == ["meta", "delta", "done"]
        raw_payloads = _extract_sse_payloads(response, include_heartbeat=True)
        assert raw_payloads[0]["type"] == "heartbeat"

    def test_chat_stream_routes_recycling_requests_through_recycling_stream(
        self,
        client,
        make_auth_headers,
        monkeypatch,
    ):
        _, headers = make_auth_headers()

        monkeypatch.setattr(
            "app.services.ai.ai_decision_engine.decide_message",
            lambda **kwargs: {
                "engine_version": "decision-engine-v1",
                "intent": "recycling_analysis",
                "follow_up_type": None,
                "confidence": 0.92,
                "needs_clarification": False,
                "clarification_question": None,
                "clarification_options": [],
                "target_case_id": None,
                "resolution_confidence": None,
                "should_create_new_case": True,
                "memory_candidates": [],
                "context": {},
                "prompt_memory": {},
            },
        )

        def fake_recycling_stream(**kwargs):
            yield {"type": "meta", "conversation_id": 2, "conversation_title": "Bottle Recycling"}
            yield {"type": "stage_start", "stage": "analysis"}
            yield {"type": "delta", "content": "Bottle analysis"}
            yield {"type": "done", "stream_stage": "completed"}

        monkeypatch.setattr(
            recycling_analysis_service, "stream_recycling_analysis", fake_recycling_stream
        )

        response = _post_json(
            client,
            "/api/ai/chat/stream",
            {"message": "How do I recycle this plastic bottle?"},
            headers,
            buffered=True,
        )

        payloads = _extract_sse_payloads(response)
        assert response.status_code == 200
        assert payloads[1]["type"] == "stage_start"
        assert payloads[1]["stage"] == "analysis"

    def test_chat_stream_persists_clarification_decision_and_history(
        self,
        client,
        make_auth_headers,
        monkeypatch,
    ):
        _, headers = make_auth_headers()

        monkeypatch.setattr(
            "app.services.ai.ai_decision_engine.decide_message",
            lambda **kwargs: {
                "engine_version": "decision-engine-v1",
                "intent": "recycling_follow_up",
                "follow_up_type": "nearby_search",
                "confidence": 0.78,
                "needs_clarification": True,
                "clarification_question": "Which recycling case do you mean?",
                "clarification_options": [
                    {"label": "Bottle", "reply_text": "I mean the bottle case."},
                    {"label": "Battery", "reply_text": "I mean the battery case."},
                ],
                "target_case_id": None,
                "resolution_confidence": 0.42,
                "should_create_new_case": False,
                "memory_candidates": [],
                "context": {},
                "prompt_memory": {},
            },
        )

        response = _post_json(
            client,
            "/api/ai/chat/stream",
            {"message": "Continue that recycling task"},
            headers,
            buffered=True,
        )

        payloads = _extract_sse_payloads(response)
        assert response.status_code == 200
        assert payloads[0]["type"] == "meta"
        assert payloads[1]["type"] == "clarification"

        conversation_id = payloads[0]["conversation_id"]
        history_response = client.get(
            f"/api/ai/conversations/{conversation_id}/messages",
            headers=headers,
        )
        history = history_response.get_json()["data"]
        assert history["items"][0]["role"] == "user"
        assert history["items"][1]["message_type"] == "tool_result"
        assert history["items"][1]["content_json"]["stream_stage"] == "clarification"
        assert history["items"][1]["content_json"]["clarification_options"][0]["label"] == "Bottle"

        decision_count = db.session.scalar(
            select(db.func.count(AIMessageDecision.id)).where(
                AIMessageDecision.conversation_id == conversation_id
            )
        )
        assert decision_count == 1
