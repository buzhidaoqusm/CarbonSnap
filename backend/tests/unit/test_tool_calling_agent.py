from __future__ import annotations

from typing import Any

from app.services.ai import tool_calling_agent


def _assistant_tool_call(
    name: str, arguments_json: str, *, call_id: str = "call_1"
) -> dict[str, Any]:
    """Provider response shell that requests one tool call."""
    return {
        "content": None,
        "tool_calls": [{"id": call_id, "name": name, "arguments": _loads(arguments_json)}],
        "finish_reason": "tool_calls",
        "model": "test-model",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        "raw_message": {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": arguments_json},
                }
            ],
        },
    }


def _assistant_text(text: str) -> dict[str, Any]:
    return {
        "content": text,
        "tool_calls": [],
        "finish_reason": "stop",
        "model": "test-model",
        "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
        "raw_message": {"role": "assistant", "content": text},
    }


def _loads(value: str) -> dict[str, Any]:
    import json

    return json.loads(value)


class _ScriptedCompletion:
    """Returns a pre-scripted sequence of provider responses, one per call."""

    def __init__(self, responses: list[dict[str, Any]]):
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *, messages, tools, tool_choice):
        self.calls.append({"messages": list(messages), "tools": tools, "tool_choice": tool_choice})
        index = min(len(self.calls) - 1, len(self._responses) - 1)
        return self._responses[index]


def _fake_execute(name, arguments, *, context, allow_high_risk):
    return {
        "tool_name": name,
        "ok": True,
        "blocked": False,
        "risk_level": "low",
        "output": {"echo": arguments, "context_user": (context or {}).get("user_id")},
        "arguments": arguments,
    }


def test_agent_loop_executes_model_selected_tool_then_answers():
    completion = _ScriptedCompletion(
        [
            _assistant_tool_call("search_forum", '{"query": "battery recycling"}'),
            _assistant_text("Batteries go to e-waste drop-off. [Sources]"),
        ]
    )

    result = tool_calling_agent.run_tool_calling_agent(
        messages=[{"role": "user", "content": "How do I recycle a battery?"}],
        context={"user_id": 42},
        tools=[{"type": "function", "function": {"name": "search_forum"}}],
        completion_fn=completion,
        execute_fn=_fake_execute,
    )

    # The model drove tool selection; the loop executed it and produced a final answer.
    assert result["content"] == "Batteries go to e-waste drop-off. [Sources]"
    assert result["stopped_reason"] == "answered"
    assert result["iterations"] == 2
    assert len(result["tool_trace"]) == 1
    assert result["tool_trace"][0]["name"] == "search_forum"
    assert result["tool_trace"][0]["arguments"] == {"query": "battery recycling"}
    assert result["tool_trace"][0]["ok"] is True

    # A genuine agent -> tools -> agent cycle ran.
    assert result["nodes"] == ["agent", "tools", "agent"]

    # First turn offered tools; the tool result was appended as a tool-role message.
    assert completion.calls[0]["tools"] is not None
    tool_messages = [m for m in result["messages"] if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "call_1"

    # Usage aggregated across both turns.
    assert result["usage_total"]["total_tokens"] == 27


def test_agent_loop_forces_final_answer_at_iteration_cap():
    # Model keeps requesting tools forever; the cap must force a text answer.
    completion = _ScriptedCompletion(
        [
            _assistant_tool_call("search_forum", '{"query": "loop"}'),
            _assistant_tool_call("search_forum", '{"query": "loop"}'),
            _assistant_text("Final grounded answer."),
        ]
    )

    result = tool_calling_agent.run_tool_calling_agent(
        messages=[{"role": "user", "content": "tell me"}],
        tools=[{"type": "function", "function": {"name": "search_forum"}}],
        max_iterations=2,
        completion_fn=completion,
        execute_fn=_fake_execute,
    )

    assert result["stopped_reason"] == "max_iterations"
    # 2 tool-using turns + 1 forced final turn.
    assert result["iterations"] == 3
    assert len(result["tool_trace"]) == 2
    assert result["content"] == "Final grounded answer."
    # The forced final turn must be called WITHOUT tools.
    assert completion.calls[-1]["tools"] is None
    assert completion.calls[-1]["tool_choice"] == "none"


def test_agent_loop_answers_without_tools_when_model_declines():
    completion = _ScriptedCompletion([_assistant_text("No tools needed here.")])

    result = tool_calling_agent.run_tool_calling_agent(
        messages=[{"role": "user", "content": "hi"}],
        tools=[{"type": "function", "function": {"name": "search_forum"}}],
        completion_fn=completion,
        execute_fn=_fake_execute,
    )

    assert result["content"] == "No tools needed here."
    assert result["iterations"] == 1
    assert result["tool_trace"] == []
    assert result["nodes"] == ["agent"]


def test_agent_loop_runs_multiple_tools_across_turns():
    completion = _ScriptedCompletion(
        [
            _assistant_tool_call("search_forum", '{"query": "glass jar"}', call_id="c1"),
            _assistant_tool_call("estimate_carbon_saving", '{"item_type": "glass"}', call_id="c2"),
            _assistant_text("Here is the combined guidance."),
        ]
    )

    result = tool_calling_agent.run_tool_calling_agent(
        messages=[{"role": "user", "content": "recycle a glass jar and estimate savings"}],
        tools=[{"type": "function", "function": {"name": "x"}}],
        completion_fn=completion,
        execute_fn=_fake_execute,
    )

    assert [entry["name"] for entry in result["tool_trace"]] == [
        "search_forum",
        "estimate_carbon_saving",
    ]
    assert result["tool_trace"][0]["step"] == 1
    assert result["tool_trace"][1]["step"] == 2
    assert result["nodes"] == ["agent", "tools", "agent", "tools", "agent"]
