from __future__ import annotations

import json

from app.services.ai import ai_conversation_service
from app.services.ai.agent_trace_service import build_trace_shell


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


def _general_decision():
    return {
        "engine_version": "decision-engine-v2",
        "intent": "general_chat",
        "follow_up_type": None,
        "confidence": 0.93,
        "needs_clarification": False,
        "clarification_question": None,
        "clarification_options": [],
        "target_case_id": None,
        "resolution_confidence": None,
        "should_create_new_case": False,
        "should_retrieve_forum": False,
        "memory_candidates": [],
        "context": {},
        "prompt_memory": {},
        "trace": build_trace_shell(user_id=None, conversation_id=None, intent="general_chat"),
    }


def test_ai_chat_uses_langgraph_when_feature_flag_enabled(
    client, app, make_auth_headers, monkeypatch
):
    app.config.update(
        AI_GRAPH_AGENT_ENABLED=True,
        AI_DEMO_REPLAY_ENABLED=False,
    )
    monkeypatch.setattr(
        "app.services.ai.ai_decision_engine.decide_message",
        lambda **kwargs: _general_decision(),
    )
    monkeypatch.setattr(
        ai_conversation_service,
        "complete_chat_message",
        lambda **kwargs: {
            "reply": "Graph API answer",
            "model": "test-model",
            "usage": {},
            "trace": kwargs["decision"]["trace"],
        },
    )

    _, headers = make_auth_headers()
    response = _post_json(client, "/api/ai/chat", {"message": "hello"}, headers)

    data = response.get_json()["data"]
    assert response.status_code == 200
    assert data["reply"] == "Graph API answer"
    assert data["graph_agent"]["enabled"] is True
    assert data["graph_agent"]["route"] == "general"
    assert data["trace"]["graph_agent"]["framework"] == "langgraph"


def test_ai_chat_stream_uses_langgraph_when_feature_flag_enabled(
    client, app, make_auth_headers, monkeypatch
):
    app.config.update(
        AI_GRAPH_AGENT_ENABLED=True,
        AI_DEMO_REPLAY_ENABLED=False,
    )
    monkeypatch.setattr(
        "app.services.ai.ai_decision_engine.decide_message",
        lambda **kwargs: _general_decision(),
    )

    def fake_stream_chat_message(**kwargs):
        yield {"type": "meta", "conversation_id": 10}
        yield {"type": "delta", "content": "Graph stream"}
        yield {"type": "done", "stream_stage": "completed"}

    monkeypatch.setattr(ai_conversation_service, "stream_chat_message", fake_stream_chat_message)

    _, headers = make_auth_headers()
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
    assert payloads[0]["graph_agent"]["enabled"] is True
    assert payloads[0]["graph_agent"]["route"] == "general"


def test_ai_chat_keeps_existing_route_when_graph_agent_disabled(
    client, app, make_auth_headers, monkeypatch
):
    app.config.update(
        AI_GRAPH_AGENT_ENABLED=False,
        AI_DEMO_REPLAY_ENABLED=False,
    )
    monkeypatch.setattr(
        "app.services.ai.ai_decision_engine.decide_message",
        lambda **kwargs: _general_decision(),
    )
    monkeypatch.setattr(
        ai_conversation_service,
        "complete_chat_message",
        lambda **kwargs: {
            "reply": "Classic answer",
            "model": "test-model",
            "usage": {},
            "trace": kwargs["decision"]["trace"],
        },
    )

    _, headers = make_auth_headers()
    response = _post_json(client, "/api/ai/chat", {"message": "hello"}, headers)

    data = response.get_json()["data"]
    assert response.status_code == 200
    assert data["reply"] == "Classic answer"
    assert "graph_agent" not in data
