"""End-to-end composition of the model-driven agent loop.

These tests exercise the REAL provider primitive (`complete_with_tools`), the
REAL tool registry executor (`execute_tool_call`), and the REAL LangGraph loop
(`run_tool_calling_agent`) together. Only the lowest-level OpenAI client is
faked, so the test proves A1 (tools given to model) + A2 (agent<->tools cycle)
+ A3 (tools actually executed and fed back) compose against production code.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from app.services.ai import openrouter_service, tool_calling_agent


class _FakeToolCall:
    def __init__(self, call_id: str, name: str, arguments: str):
        self.id = call_id
        self.type = "function"
        self.function = SimpleNamespace(name=name, arguments=arguments)


def _fake_completion(*, content, tool_calls, finish_reason):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    usage = SimpleNamespace(prompt_tokens=11, completion_tokens=7, total_tokens=18)
    return SimpleNamespace(choices=[choice], model="fake/model", usage=usage)


class _ScriptedClient:
    """Fake OpenAI client: first call requests a tool, second call answers."""

    def __init__(self):
        self.captured_kwargs: list[dict[str, Any]] = []
        self._turn = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.captured_kwargs.append(kwargs)
        self._turn += 1
        if self._turn == 1:
            return _fake_completion(
                content=None,
                tool_calls=[
                    _FakeToolCall(
                        "call_1",
                        "estimate_carbon_saving",
                        json.dumps({"item_type": "plastic bottle", "weight_kg": 0.5}),
                    )
                ],
                finish_reason="tool_calls",
            )
        return _fake_completion(
            content="Recycling that bottle saves CO2. Nice work!",
            tool_calls=None,
            finish_reason="stop",
        )


def test_agent_loop_composes_real_provider_registry_and_graph(app, monkeypatch):
    client = _ScriptedClient()
    monkeypatch.setattr(openrouter_service, "_get_client", lambda: client)

    with app.app_context():
        result = tool_calling_agent.run_tool_calling_agent(
            messages=[
                {"role": "system", "content": "You are a recycling assistant."},
                {"role": "user", "content": "How much CO2 do I save recycling a plastic bottle?"},
            ],
            context={"user_id": 1, "client_context": None},
        )

    # Final natural-language answer produced after the tool round-trip.
    assert result["content"] == "Recycling that bottle saves CO2. Nice work!"
    assert result["stopped_reason"] == "answered"

    # A genuine agent -> tools -> agent cycle ran through the compiled LangGraph.
    assert result["nodes"] == ["agent", "tools", "agent"]

    # The REAL estimate_carbon_saving tool executed and returned real numbers.
    assert len(result["tool_trace"]) == 1
    step = result["tool_trace"][0]
    assert step["name"] == "estimate_carbon_saving"
    assert step["ok"] is True
    assert step["output"]["co2_saved_kg"] > 0
    assert "carbon_points" in step["output"]

    # Both turns (under the iteration cap) were offered the real tool schema;
    # the model chose a tool on turn 1 and a final answer on turn 2.
    first_call, second_call = client.captured_kwargs[0], client.captured_kwargs[1]
    tool_names = {t["function"]["name"] for t in first_call["tools"]}
    assert "estimate_carbon_saving" in tool_names
    assert "query_recycling_graph" in tool_names  # full registry schema surfaced
    assert "tools" in second_call
    # Turn 2 also carried the tool result back to the model (fed-back execution).
    assert any(m.get("role") == "tool" for m in second_call["messages"])

    # Token usage aggregated across both provider calls.
    assert result["usage_total"]["total_tokens"] == 36


def test_high_risk_tool_is_blocked_through_real_executor(app, monkeypatch):
    class _HighRiskClient(_ScriptedClient):
        def _create(self, **kwargs):
            self.captured_kwargs.append(kwargs)
            self._turn += 1
            if self._turn == 1:
                return _fake_completion(
                    content=None,
                    tool_calls=[
                        _FakeToolCall(
                            "call_x", "record_recycling_completion", json.dumps({"case_id": 1})
                        )
                    ],
                    finish_reason="tool_calls",
                )
            return _fake_completion(
                content="Please confirm to finalize.", tool_calls=None, finish_reason="stop"
            )

    client = _HighRiskClient()
    monkeypatch.setattr(openrouter_service, "_get_client", lambda: client)

    with app.app_context():
        result = tool_calling_agent.run_tool_calling_agent(
            messages=[{"role": "user", "content": "mark it done"}],
            context={"user_id": 1},
            exclude_high_risk=False,  # even if surfaced, execution must be gated
        )

    step = result["tool_trace"][0]
    assert step["name"] == "record_recycling_completion"
    assert step["blocked"] is True
    assert step["ok"] is False


def _general_decision():
    from app.services.ai.agent_trace_service import build_trace_shell

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


def test_graph_agent_general_route_runs_tool_calling_agent_with_persistence(
    app, monkeypatch, make_auth_headers
):
    """Full product path: Graph Agent general route -> tool-calling loop ->
    real tool execution -> persisted assistant message + trace."""
    from app.services.ai import ai_conversation_service, ai_decision_engine
    from app.services.ai.langgraph_agent import complete_graph_agent_message

    app.config.update(
        AI_GRAPH_AGENT_ENABLED=True,
        AI_TOOL_CALLING_AGENT_ENABLED=True,
        AI_DEMO_REPLAY_ENABLED=False,
    )
    monkeypatch.setattr(ai_decision_engine, "decide_message", lambda **kwargs: _general_decision())
    # New-conversation title generation makes its own LLM call; pin it so the
    # scripted provider turns map cleanly onto the agent loop.
    monkeypatch.setattr(
        ai_conversation_service, "generate_conversation_title", lambda **kwargs: "CO2 savings chat"
    )

    client = _ScriptedClient()
    monkeypatch.setattr(openrouter_service, "_get_client", lambda: client)

    user_id, _headers = make_auth_headers()

    with app.app_context():
        result = complete_graph_agent_message(
            user_id=user_id,
            message="How much CO2 do I save recycling a plastic bottle?",
        )

    # The reply came from the model-driven loop, not the pre-injection path.
    assert result["reply"] == "Recycling that bottle saves CO2. Nice work!"
    assert result["graph_agent"]["route"] == "general"

    # The assistant message was persisted.
    assert result["assistant_message_id"] is not None
    assert result["conversation_id"] is not None

    # The executed tool call is surfaced in the stored trace for the Agent Trace panel.
    tool_call_names = {entry.get("name") for entry in result["trace"]["tool_calls"]}
    assert "estimate_carbon_saving" in tool_call_names
    assert result["trace"]["agent_loop"]["engine"] == "tool_calling_agent"
    assert result["trace"]["agent_loop"]["framework"] == "langgraph"
    assert result["trace"]["agent_loop"]["tool_call_count"] == 1
