from __future__ import annotations

from collections.abc import Generator
from typing import Any, Literal, TypedDict

GraphRoute = Literal["clarification", "recycling", "general"]


class GraphAgentState(TypedDict, total=False):
    user_id: int | None
    message: str
    history: list[dict[str, Any]] | None
    image_data_url: str | None
    conversation_id: int | None
    client_context: dict[str, Any] | None
    decision: dict[str, Any]
    route: GraphRoute
    available_tools: list[dict[str, Any]]
    selected_tools: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    result: dict[str, Any]
    graph_nodes: list[str]
    errors: list[str]


def is_langgraph_available() -> bool:
    try:
        from langgraph.graph import END, START, StateGraph  # noqa: F401
    except Exception:
        return False
    return True


def complete_graph_agent_message(
    *,
    user_id: int | None,
    message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    conversation_id: int | None = None,
    client_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    graph = build_graph_agent()
    final_state = graph.invoke(
        {
            "user_id": user_id,
            "message": message,
            "history": history,
            "image_data_url": image_data_url,
            "conversation_id": conversation_id,
            "client_context": client_context,
            "graph_nodes": [],
            "errors": [],
        }
    )
    result = dict(final_state.get("result") or {})
    return _attach_graph_metadata(result, final_state)


def stream_graph_agent_message(
    *,
    user_id: int | None,
    message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    conversation_id: int | None = None,
    client_context: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    route_state = _run_routing_graph(
        user_id=user_id,
        message=message,
        history=history,
        image_data_url=image_data_url,
        conversation_id=conversation_id,
        client_context=client_context,
    )
    decision = route_state["decision"]
    serialized_decision = {
        key: value for key, value in decision.items() if key not in {"context", "prompt_memory"}
    }

    if route_state["route"] == "clarification":
        result = _execute_clarification_node(route_state)["result"]
        yield {
            "type": "meta",
            "conversation_id": result.get("conversation_id"),
            "conversation_title": result.get("conversation_title"),
            "user_message_id": result.get("user_message_id"),
            "assistant_message_id": result.get("assistant_message_id"),
            "decision": serialized_decision,
            "graph_agent": _graph_metadata(route_state),
        }
        yield {
            "type": "clarification",
            "data": {
                "question": result.get("reply"),
                "options": result.get("clarification_options", []),
            },
        }
        yield {"type": "done", "stream_stage": "clarification"}
        return

    if route_state["route"] == "recycling":
        from app.services.ai.recycling_analysis_service import stream_recycling_analysis

        for event in stream_recycling_analysis(
            message=message,
            image_data_url=image_data_url,
            session_id=None,
            conversation_id=conversation_id,
            user_id=user_id,
            decision=decision,
            client_context=client_context,
        ):
            if event.get("type") == "meta":
                yield {
                    **event,
                    "decision": serialized_decision,
                    "graph_agent": _graph_metadata(route_state),
                }
                continue
            yield event
        return

    from app.services.ai.ai_conversation_service import stream_chat_message

    for event in stream_chat_message(
        user_id=user_id,
        message=message,
        history=history,
        image_data_url=image_data_url,
        conversation_id=conversation_id,
        prompt_memory=decision["prompt_memory"],
        memory_candidates=decision["memory_candidates"],
        decision=decision,
        client_context=client_context,
    ):
        if event.get("type") == "meta":
            yield {
                **event,
                "decision": serialized_decision,
                "graph_agent": _graph_metadata(route_state),
            }
            continue
        yield event


def build_graph_agent():
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(GraphAgentState)
    graph.add_node("route_intent", _route_intent_node)
    graph.add_node("select_tools", _select_tools_node)
    graph.add_node("clarify", _execute_clarification_node)
    graph.add_node("answer_general", _execute_general_chat_node)
    graph.add_node("handle_recycling", _execute_recycling_node)
    graph.add_edge(START, "route_intent")
    graph.add_conditional_edges(
        "select_tools",
        _route_from_decision,
        {
            "clarification": "clarify",
            "recycling": "handle_recycling",
            "general": "answer_general",
        },
    )
    graph.add_edge("route_intent", "select_tools")
    graph.add_edge("clarify", END)
    graph.add_edge("answer_general", END)
    graph.add_edge("handle_recycling", END)
    return graph.compile()


def _run_routing_graph(
    *,
    user_id: int | None,
    message: str,
    history: list[dict[str, Any]] | None,
    image_data_url: str | None,
    conversation_id: int | None,
    client_context: dict[str, Any] | None,
) -> GraphAgentState:
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(GraphAgentState)
    graph.add_node("route_intent", _route_intent_node)
    graph.add_node("select_tools", _select_tools_node)
    graph.add_edge(START, "route_intent")
    graph.add_edge("route_intent", "select_tools")
    graph.add_edge("select_tools", END)
    return graph.compile().invoke(
        {
            "user_id": user_id,
            "message": message,
            "history": history,
            "image_data_url": image_data_url,
            "conversation_id": conversation_id,
            "client_context": client_context,
            "graph_nodes": [],
            "errors": [],
        }
    )


def _route_intent_node(state: GraphAgentState) -> GraphAgentState:
    from app.services.ai.ai_decision_engine import decide_message

    decision = decide_message(
        user_id=state.get("user_id"),
        conversation_id=state.get("conversation_id"),
        message=state["message"],
        image_data_url=state.get("image_data_url"),
        supplied_history=state.get("history"),
    )
    route = _route_from_decision({"decision": decision})
    return {
        **state,
        "decision": decision,
        "route": route,
        "graph_nodes": [*state.get("graph_nodes", []), "route_intent"],
    }


def _select_tools_node(state: GraphAgentState) -> GraphAgentState:
    from app.services.ai.tool_registry import (
        build_tool_trace_entries,
        list_tool_definitions,
        select_tools_for_decision,
    )

    selected_tools = select_tools_for_decision(
        state.get("decision"),
        client_context=state.get("client_context"),
    )
    return {
        **state,
        "available_tools": list_tool_definitions(),
        "selected_tools": selected_tools,
        "tool_results": build_tool_trace_entries(selected_tools),
        "graph_nodes": [*state.get("graph_nodes", []), "select_tools"],
    }


def _route_from_decision(state: GraphAgentState) -> GraphRoute:
    decision = state["decision"]
    if decision.get("needs_clarification"):
        return "clarification"
    if decision.get("intent") in {"recycling_analysis", "recycling_follow_up"}:
        return "recycling"
    return "general"


def _execute_clarification_node(state: GraphAgentState) -> GraphAgentState:
    from app.services.ai.ai_conversation_service import _persist_clarification_request

    decision = state["decision"]
    persisted = _persist_clarification_request(
        user_id=state.get("user_id"),
        message=state["message"],
        image_data_url=state.get("image_data_url"),
        conversation_id=state.get("conversation_id"),
        decision=decision,
    )
    conversation = persisted["conversation"]
    user_message = persisted["user_message"]
    assistant_message = persisted.get("assistant_message")
    result = {
        "reply": decision.get("clarification_question")
        or "Could you clarify which recycling task you mean?",
        "model": None,
        "usage": {},
        "conversation_id": conversation.id
        if conversation is not None
        else state.get("conversation_id"),
        "conversation_title": conversation.title if conversation is not None else None,
        "user_message_id": user_message.id if user_message is not None else None,
        "assistant_message_id": assistant_message.id if assistant_message is not None else None,
        "memory_updates": [],
        "decision": {
            key: value for key, value in decision.items() if key not in {"context", "prompt_memory"}
        },
        "clarification_options": decision.get("clarification_options", []),
    }
    return {
        **state,
        "result": result,
        "graph_nodes": [*state.get("graph_nodes", []), "clarify"],
    }


def _execute_general_chat_node(state: GraphAgentState) -> GraphAgentState:
    from app.services.ai.ai_conversation_service import complete_general_chat_with_mode

    decision = state["decision"]
    result = complete_general_chat_with_mode(
        user_id=state.get("user_id"),
        message=state["message"],
        history=state.get("history"),
        image_data_url=state.get("image_data_url"),
        conversation_id=state.get("conversation_id"),
        prompt_memory=decision["prompt_memory"],
        memory_candidates=decision["memory_candidates"],
        decision=decision,
        client_context=state.get("client_context"),
    )
    result["decision"] = {
        key: value for key, value in decision.items() if key not in {"context", "prompt_memory"}
    }
    return {
        **state,
        "result": result,
        "graph_nodes": [*state.get("graph_nodes", []), "answer_general"],
    }


def _execute_recycling_node(state: GraphAgentState) -> GraphAgentState:
    from app.services.ai.recycling_analysis_service import complete_recycling_analysis

    result = complete_recycling_analysis(
        user_id=state.get("user_id"),
        message=state["message"],
        image_data_url=state.get("image_data_url"),
        conversation_id=state.get("conversation_id"),
        decision=state["decision"],
        client_context=state.get("client_context"),
    )
    return {
        **state,
        "result": result,
        "graph_nodes": [*state.get("graph_nodes", []), "handle_recycling"],
    }


def _attach_graph_metadata(result: dict[str, Any], state: GraphAgentState) -> dict[str, Any]:
    metadata = _graph_metadata(state)
    result["graph_agent"] = metadata

    trace = result.get("trace")
    if isinstance(trace, dict):
        tool_calls = list(trace.get("tool_calls") or [])
        tool_calls.append(
            {
                "name": "langgraph_orchestrator",
                "route": state.get("route"),
                "nodes": metadata["nodes"],
            }
        )
        tool_calls.extend(state.get("tool_results", []))
        trace["tool_calls"] = tool_calls
        trace["graph_agent"] = metadata
        result["trace"] = trace
    return result


def _graph_metadata(state: GraphAgentState) -> dict[str, Any]:
    return {
        "enabled": True,
        "framework": "langgraph",
        "route": state.get("route"),
        "nodes": state.get("graph_nodes", []),
        "errors": state.get("errors", []),
        "available_tools": [
            {
                "name": tool.get("name"),
                "risk_level": tool.get("risk_level"),
                "auto_execute": tool.get("auto_execute"),
            }
            for tool in state.get("available_tools", [])
        ],
        "selected_tools": state.get("selected_tools", []),
    }
