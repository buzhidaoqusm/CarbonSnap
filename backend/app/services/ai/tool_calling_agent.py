"""Model-driven tool-calling agent loop.

Unlike the rule-based ``select_tools_for_decision`` path, this engine hands the
tool schemas to the model and lets *the model* decide which tools to call. It
runs a real ReAct-style cycle (agent -> tools -> agent) until the model returns
a final answer or a hard iteration cap is reached.

The cycle is expressed as a LangGraph ``StateGraph`` with a genuine loop edge
(``tools -> agent``). When LangGraph is unavailable the same semantics run
through an equivalent plain-Python loop, so behaviour and tests do not depend on
the framework being installed.

All external dependencies (``completion_fn``, ``execute_fn``, ``tools``) are
injectable, which lets the whole loop be unit-tested with fakes and no provider
or network access.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, TypedDict

from flask import current_app


DEFAULT_MAX_ITERATIONS = 4

CompletionFn = Callable[..., dict[str, Any]]
ExecuteFn = Callable[..., dict[str, Any]]


class AgentLoopState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    context: dict[str, Any]
    tools_schema: list[dict[str, Any]]
    completion_fn: CompletionFn
    execute_fn: ExecuteFn
    allow_high_risk: bool
    max_iterations: int
    iterations: int
    pending_tool_calls: list[dict[str, Any]]
    tool_trace: list[dict[str, Any]]
    final_content: str | None
    stopped_reason: str
    last_model: str | None
    usage_total: dict[str, int]
    graph_nodes: list[str]


def run_tool_calling_agent(
    *,
    messages: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
    exclude_high_risk: bool = True,
    allow_high_risk: bool = False,
    max_iterations: int | None = None,
    completion_fn: CompletionFn | None = None,
    execute_fn: ExecuteFn | None = None,
) -> dict[str, Any]:
    """Run the model-driven tool-calling loop and return the final result.

    Args:
        messages: OpenAI-style message list to seed the conversation.
        context: Runtime context (``user_id``, ``client_context``) forwarded to
            tool execution so contextual params can be injected server-side.
        tools: Pre-built OpenAI ``tools`` schema. Defaults to the tool registry
            (``to_openai_tools``) when omitted.
        exclude_high_risk: Hide high-risk tools from the model when building the
            default schema (they still cannot auto-execute regardless).
        allow_high_risk: Permit high-risk tool execution (human-approved path).
        max_iterations: Hard cap on agent turns before forcing a final answer.
        completion_fn: Override for the provider call (testing/injection).
        execute_fn: Override for tool execution (testing/injection).

    Returns:
        dict with ``content``, ``messages`` (full transcript), ``tool_trace``,
        ``iterations``, ``stopped_reason``, ``model``, ``usage_total`` and the
        ordered list of graph ``nodes`` that ran.
    """
    resolved_completion = completion_fn or _default_completion_fn
    resolved_execute = execute_fn or _default_execute_fn
    resolved_tools = tools if tools is not None else _default_tools_schema(exclude_high_risk=exclude_high_risk)
    resolved_max = int(max_iterations if max_iterations is not None else _configured_max_iterations())
    resolved_max = max(1, resolved_max)

    initial_state: AgentLoopState = {
        "messages": list(messages),
        "context": dict(context or {}),
        "tools_schema": resolved_tools,
        "completion_fn": resolved_completion,
        "execute_fn": resolved_execute,
        "allow_high_risk": bool(allow_high_risk),
        "max_iterations": resolved_max,
        "iterations": 0,
        "pending_tool_calls": [],
        "tool_trace": [],
        "final_content": None,
        "stopped_reason": "",
        "last_model": None,
        "usage_total": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "graph_nodes": [],
    }

    final_state = _run(initial_state)
    return _serialize_result(final_state)


# ---------------------------------------------------------------------------
# Graph nodes (shared by the LangGraph path and the plain-loop fallback)
# ---------------------------------------------------------------------------


def _agent_node(state: AgentLoopState) -> AgentLoopState:
    """Call the model. Use tools while under the cap; force a final answer once
    the cap is reached so the loop always terminates with text."""
    iterations = int(state.get("iterations", 0))
    max_iterations = int(state.get("max_iterations", DEFAULT_MAX_ITERATIONS))
    use_tools = iterations < max_iterations

    completion_fn = state["completion_fn"]
    response = completion_fn(
        messages=state["messages"],
        tools=state["tools_schema"] if use_tools else None,
        tool_choice="auto" if use_tools else "none",
    )

    messages = [*state["messages"], response.get("raw_message") or _assistant_message(response)]
    usage_total = _accumulate_usage(state.get("usage_total"), response.get("usage"))
    tool_calls = list(response.get("tool_calls") or [])

    updated: AgentLoopState = {
        **state,
        "messages": messages,
        "iterations": iterations + 1,
        "last_model": response.get("model") or state.get("last_model"),
        "usage_total": usage_total,
        "graph_nodes": [*state.get("graph_nodes", []), "agent"],
    }

    if use_tools and tool_calls:
        updated["pending_tool_calls"] = tool_calls
        updated["final_content"] = None
        return updated

    updated["pending_tool_calls"] = []
    updated["final_content"] = str(response.get("content") or "")
    updated["stopped_reason"] = "answered" if use_tools else "max_iterations"
    return updated


def _tools_node(state: AgentLoopState) -> AgentLoopState:
    """Execute every pending tool call and append tool-role result messages."""
    execute_fn = state["execute_fn"]
    context = state.get("context") or {}
    allow_high_risk = bool(state.get("allow_high_risk", False))

    messages = list(state["messages"])
    tool_trace = list(state.get("tool_trace", []))
    step_base = len(tool_trace)

    for offset, call in enumerate(state.get("pending_tool_calls", [])):
        name = str(call.get("name") or "")
        arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
        result = execute_fn(
            name,
            arguments,
            context=context,
            allow_high_risk=allow_high_risk,
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.get("id"),
                "name": name,
                "content": _json_dumps(result.get("output", result.get("error", {}))),
            }
        )
        tool_trace.append(
            {
                "step": step_base + offset + 1,
                "name": name,
                "arguments": result.get("arguments", arguments),
                "ok": bool(result.get("ok")),
                "blocked": bool(result.get("blocked")),
                "risk_level": result.get("risk_level"),
                "output": result.get("output", {}),
                "error": result.get("error"),
            }
        )

    return {
        **state,
        "messages": messages,
        "tool_trace": tool_trace,
        "pending_tool_calls": [],
        "graph_nodes": [*state.get("graph_nodes", []), "tools"],
    }


def _route_after_agent(state: AgentLoopState) -> str:
    """Continue to tools when the model requested tool calls, else stop."""
    return "tools" if state.get("final_content") is None else "end"


# ---------------------------------------------------------------------------
# Execution: LangGraph cycle with an equivalent plain-loop fallback
# ---------------------------------------------------------------------------


def _run(state: AgentLoopState) -> AgentLoopState:
    graph = _build_graph()
    if graph is not None:
        # Allow enough supersteps for the worst case: (agent + tools) per
        # iteration, the forced-final agent turn, plus routing overhead.
        recursion_limit = 2 * int(state.get("max_iterations", DEFAULT_MAX_ITERATIONS)) + 5
        return graph.invoke(state, config={"recursion_limit": recursion_limit})
    return _run_plain_loop(state)


def _build_graph():
    try:
        from langgraph.graph import END, START, StateGraph
    except Exception:
        return None

    graph = StateGraph(AgentLoopState)
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", _tools_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", _route_after_agent, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")  # the loop
    return graph.compile()


def _run_plain_loop(state: AgentLoopState) -> AgentLoopState:
    """Framework-free equivalent of the compiled graph, same semantics."""
    current = state
    # Upper bound mirrors the graph recursion limit; the agent node's own cap
    # guarantees termination well before this.
    for _ in range(2 * int(state.get("max_iterations", DEFAULT_MAX_ITERATIONS)) + 5):
        current = _agent_node(current)
        if _route_after_agent(current) == "end":
            return current
        current = _tools_node(current)
    return current


# ---------------------------------------------------------------------------
# Defaults wired to the real provider / registry (lazy so tests stay isolated)
# ---------------------------------------------------------------------------


def _default_completion_fn(
    *,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    tool_choice: str,
) -> dict[str, Any]:
    from app.services.ai.openrouter_service import complete_with_tools

    return complete_with_tools(messages=messages, tools=tools, tool_choice=tool_choice)


def _default_execute_fn(
    name: str,
    arguments: dict[str, Any],
    *,
    context: dict[str, Any] | None,
    allow_high_risk: bool,
) -> dict[str, Any]:
    from app.services.ai.tool_registry import execute_tool_call

    return execute_tool_call(name, arguments, context=context, allow_high_risk=allow_high_risk)


def _default_tools_schema(*, exclude_high_risk: bool) -> list[dict[str, Any]]:
    from app.services.ai.tool_registry import to_openai_tools

    return to_openai_tools(exclude_high_risk=exclude_high_risk)


def _configured_max_iterations() -> int:
    try:
        return int(current_app.config.get("AI_AGENT_MAX_ITERATIONS", DEFAULT_MAX_ITERATIONS) or DEFAULT_MAX_ITERATIONS)
    except Exception:
        return DEFAULT_MAX_ITERATIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assistant_message(response: dict[str, Any]) -> dict[str, Any]:
    """Fallback assistant message when the provider did not supply raw_message."""
    message: dict[str, Any] = {"role": "assistant", "content": response.get("content")}
    tool_calls = response.get("tool_calls") or []
    if tool_calls:
        message["tool_calls"] = [
            {
                "id": call.get("id"),
                "type": "function",
                "function": {
                    "name": call.get("name"),
                    "arguments": _json_dumps(call.get("arguments", {})),
                },
            }
            for call in tool_calls
        ]
    return message


def _accumulate_usage(
    running: dict[str, int] | None,
    usage: dict[str, Any] | None,
) -> dict[str, int]:
    totals = dict(running or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    if not isinstance(usage, dict):
        return totals
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, (int, float)):
            totals[key] = int(totals.get(key, 0)) + int(value)
    return totals


def _serialize_result(state: AgentLoopState) -> dict[str, Any]:
    stopped_reason = state.get("stopped_reason") or "answered"
    return {
        "content": state.get("final_content") or "",
        "messages": state.get("messages", []),
        "tool_trace": state.get("tool_trace", []),
        "iterations": int(state.get("iterations", 0)),
        "stopped_reason": stopped_reason,
        "model": state.get("last_model"),
        "usage_total": state.get("usage_total", {}),
        "nodes": state.get("graph_nodes", []),
    }


def _json_dumps(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(value)
