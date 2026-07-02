from __future__ import annotations

from app.services.ai.agent_trace_service import build_trace_shell
from app.services.ai.langgraph_agent import (
    complete_graph_agent_message,
    is_langgraph_available,
    stream_graph_agent_message,
)


def _decision(
    *,
    intent: str = "general_chat",
    needs_clarification: bool = False,
    should_retrieve_forum: bool = False,
):
    return {
        "engine_version": "decision-engine-v2",
        "intent": intent,
        "follow_up_type": None,
        "confidence": 0.91,
        "needs_clarification": needs_clarification,
        "clarification_question": "Which recycling task do you mean?" if needs_clarification else None,
        "clarification_options": [{"label": "Battery", "reply_text": "The battery one."}]
        if needs_clarification
        else [],
        "target_case_id": None,
        "resolution_confidence": None,
        "should_create_new_case": intent == "recycling_analysis",
        "should_retrieve_forum": should_retrieve_forum,
        "memory_candidates": [],
        "context": {},
        "prompt_memory": {},
        "trace": build_trace_shell(user_id=1, conversation_id=None, intent=intent),
    }


def test_is_langgraph_available():
    assert is_langgraph_available() is True


def test_complete_graph_agent_routes_general_chat(monkeypatch):
    monkeypatch.setattr(
        "app.services.ai.ai_decision_engine.decide_message",
        lambda **kwargs: _decision(intent="general_chat", should_retrieve_forum=True),
    )
    monkeypatch.setattr(
        "app.services.ai.ai_conversation_service.complete_chat_message",
        lambda **kwargs: {
            "reply": "Graph answer",
            "model": "test-model",
            "usage": {},
            "trace": kwargs["decision"]["trace"],
        },
    )

    result = complete_graph_agent_message(user_id=1, message="hello")

    assert result["reply"] == "Graph answer"
    assert result["graph_agent"]["enabled"] is True
    assert result["graph_agent"]["route"] == "general"
    assert result["graph_agent"]["nodes"] == ["route_intent", "select_tools", "answer_general"]
    assert result["trace"]["tool_calls"][0]["name"] == "langgraph_orchestrator"
    assert result["trace"]["tool_calls"][1]["name"] == "search_forum"
    assert result["trace"]["tool_calls"][1]["execution_mode"] == "planned_for_downstream_nodes"
    assert result["graph_agent"]["available_tools"]


def test_complete_graph_agent_routes_recycling(monkeypatch):
    monkeypatch.setattr(
        "app.services.ai.ai_decision_engine.decide_message",
        lambda **kwargs: _decision(intent="recycling_analysis"),
    )
    monkeypatch.setattr(
        "app.services.ai.recycling_analysis_service.complete_recycling_analysis",
        lambda **kwargs: {
            "reply": "Recycling result",
            "model": None,
            "usage": {},
            "decision": kwargs["decision"],
        },
    )

    result = complete_graph_agent_message(user_id=1, message="How do I recycle batteries?")

    assert result["reply"] == "Recycling result"
    assert result["graph_agent"]["route"] == "recycling"
    assert result["graph_agent"]["nodes"] == ["route_intent", "select_tools", "handle_recycling"]
    selected_tool_names = [tool["name"] for tool in result["graph_agent"]["selected_tools"]]
    assert "estimate_carbon_saving" in selected_tool_names


def test_stream_graph_agent_keeps_general_chat_streaming(monkeypatch):
    monkeypatch.setattr(
        "app.services.ai.ai_decision_engine.decide_message",
        lambda **kwargs: _decision(intent="general_chat"),
    )

    def fake_stream_chat_message(**kwargs):
        yield {"type": "meta", "conversation_id": 1}
        yield {"type": "delta", "content": "hello"}
        yield {"type": "done", "stream_stage": "completed"}

    monkeypatch.setattr(
        "app.services.ai.ai_conversation_service.stream_chat_message",
        fake_stream_chat_message,
    )

    events = list(stream_graph_agent_message(user_id=1, message="hello"))

    assert [event["type"] for event in events] == ["meta", "delta", "done"]
    assert events[0]["graph_agent"]["framework"] == "langgraph"
    assert events[0]["graph_agent"]["route"] == "general"
    assert events[0]["graph_agent"]["nodes"] == ["route_intent", "select_tools"]
