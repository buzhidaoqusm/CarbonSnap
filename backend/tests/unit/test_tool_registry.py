from __future__ import annotations

import pytest

from app.services.ai import tool_registry
from tests.support.database import db


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
    result = tool_registry.run_tool(db.session, "record_recycling_completion", {"case_id": 1})

    assert result["ok"] is False
    assert result["blocked"] is True
    assert result["risk_level"] == "high"
    assert result["error"] == "high_risk_tool_requires_explicit_user_action"


def test_estimate_carbon_saving_is_deterministic():
    result = tool_registry.run_tool(
        db.session,
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


def test_select_tools_respects_disabled_graph_flag(override_settings):
    # Credentials alone do not turn the graph tool on.
    override_settings(
        ai_neo4j_graphrag_enabled=False,
        neo4j_uri="bolt://localhost:7687",
        neo4j_username="neo4j",
        neo4j_password="password",
    )

    selected = tool_registry.select_tools_for_decision({"intent": "recycling_analysis"})

    assert "query_recycling_graph" not in {tool["name"] for tool in selected}
