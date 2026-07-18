from __future__ import annotations

from app.services.ai import tool_registry


def test_to_openai_tools_matches_tool_definitions():
    definitions = tool_registry.list_tool_definitions()
    openai_tools = tool_registry.to_openai_tools()

    assert {tool["function"]["name"] for tool in openai_tools} == {
        tool["name"] for tool in definitions
    }

    definitions_by_name = {tool["name"]: tool for tool in definitions}
    for openai_tool in openai_tools:
        assert openai_tool["type"] == "function"
        function = openai_tool["function"]
        definition = definitions_by_name[function["name"]]
        assert function["description"] == definition["description"]
        assert function["parameters"] == definition["input_schema"]


def test_to_openai_tools_exclude_high_risk():
    openai_tools = tool_registry.to_openai_tools(exclude_high_risk=True)
    names = {tool["function"]["name"] for tool in openai_tools}

    assert "record_recycling_completion" not in names
    assert "search_forum" in names


def test_execute_tool_call_injects_user_id_for_read_user_memory(monkeypatch):
    captured = {}

    def fake_run_tool(name, payload=None, *, allow_high_risk=False):
        captured["name"] = name
        captured["payload"] = payload
        captured["allow_high_risk"] = allow_high_risk
        return {
            "tool_name": name,
            "ok": True,
            "blocked": False,
            "risk_level": "low",
            "output": {},
        }

    monkeypatch.setattr(tool_registry, "run_tool", fake_run_tool)

    result = tool_registry.execute_tool_call(
        "read_user_memory", {}, context={"user_id": 7}
    )

    assert captured["payload"]["user_id"] == 7
    assert result["arguments"]["user_id"] == 7


def test_execute_tool_call_does_not_overwrite_provided_user_id(monkeypatch):
    captured = {}

    def fake_run_tool(name, payload=None, *, allow_high_risk=False):
        captured["payload"] = payload
        return {
            "tool_name": name,
            "ok": True,
            "blocked": False,
            "risk_level": "low",
            "output": {},
        }

    monkeypatch.setattr(tool_registry, "run_tool", fake_run_tool)

    result = tool_registry.execute_tool_call(
        "recommend_project", {"user_id": 99}, context={"user_id": 7}
    )

    assert captured["payload"]["user_id"] == 99
    assert result["arguments"]["user_id"] == 99


def test_execute_tool_call_injects_nearby_coordinates(monkeypatch):
    captured = {}

    def fake_run_tool(name, payload=None, *, allow_high_risk=False):
        captured["payload"] = payload
        return {
            "tool_name": name,
            "ok": True,
            "blocked": False,
            "risk_level": "medium",
            "output": {},
        }

    monkeypatch.setattr(tool_registry, "run_tool", fake_run_tool)

    result = tool_registry.execute_tool_call(
        "find_nearby_recycling_places",
        {},
        context={
            "client_context": {
                "location_state": {"coordinates": {"lat": 53.3, "lng": -6.2}}
            }
        },
    )

    assert captured["payload"]["lat"] == 53.3
    assert captured["payload"]["lng"] == -6.2
    assert result["arguments"]["lat"] == 53.3
    assert result["arguments"]["lng"] == -6.2


def test_execute_tool_call_blocks_high_risk_without_allow_flag():
    result = tool_registry.execute_tool_call(
        "record_recycling_completion", {"case_id": 1}
    )

    assert result["blocked"] is True
    assert result["ok"] is False
    assert result["arguments"] == {"case_id": 1}


def test_execute_tool_call_handles_none_context(monkeypatch):
    captured = {}

    def fake_run_tool(name, payload=None, *, allow_high_risk=False):
        captured["payload"] = payload
        return {
            "tool_name": name,
            "ok": True,
            "blocked": False,
            "risk_level": "low",
            "output": {},
        }

    monkeypatch.setattr(tool_registry, "run_tool", fake_run_tool)

    result = tool_registry.execute_tool_call("search_forum", {"query": "plastic"}, context=None)

    assert captured["payload"] == {"query": "plastic"}
    assert result["arguments"] == {"query": "plastic"}
