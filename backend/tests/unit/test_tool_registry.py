from __future__ import annotations

import pytest

from app.services.ai import tool_registry


def test_registry_exposes_resume_worthy_ai_tools():
    tools = tool_registry.list_tool_definitions()
    names = {tool["name"] for tool in tools}

    assert {
        "search_forum",
        "query_recycling_graph",
        "estimate_carbon_saving",
        "find_nearby_recycling_places",
        "recommend_project",
        "read_user_memory",
    }.issubset(names)
    assert all("handler" not in tool for tool in tools)
    assert all(tool["risk_level"] in {"low", "medium", "high"} for tool in tools)


def test_run_tool_blocks_high_risk_business_write():
    result = tool_registry.run_tool("record_recycling_completion", {"case_id": 1})

    assert result["ok"] is False
    assert result["blocked"] is True
    assert result["risk_level"] == "high"
    assert result["error"] == "high_risk_tool_requires_explicit_user_action"


def test_estimate_carbon_saving_is_deterministic(app):
    with app.app_context():
        result = tool_registry.run_tool(
            "estimate_carbon_saving",
            {"item_type": "plastic bottle", "weight_kg": 0.5},
        )

    assert result["ok"] is True
    assert result["output"] == {
        "item_type": "plastic bottle",
        "weight_kg": 0.5,
        "emission_factor": 1.5,
        "co2_saved_kg": 0.75,
        "carbon_points": 7.5,
    }


@pytest.mark.parametrize(
    ("decision", "expected_tool"),
    [
        ({"should_retrieve_forum": True, "intent": "general_chat"}, "search_forum"),
        ({"intent": "recycling_analysis"}, "estimate_carbon_saving"),
        ({"intent": "general_chat", "prompt_memory": {"version": 1}}, "read_user_memory"),
    ],
)
def test_select_tools_for_decision(decision, expected_tool):
    selected = tool_registry.select_tools_for_decision(decision)

    assert expected_tool in {tool["name"] for tool in selected}


def test_select_tools_respects_disabled_graph_flag(app):
    app.config["AI_NEO4J_GRAPHRAG_ENABLED"] = False
    app.config["NEO4J_URI"] = "bolt://localhost:7687"
    app.config["NEO4J_USERNAME"] = "neo4j"
    app.config["NEO4J_PASSWORD"] = "password"

    with app.app_context():
        selected = tool_registry.select_tools_for_decision({"intent": "recycling_analysis"})

    assert "query_recycling_graph" not in {tool["name"] for tool in selected}
