"""Tests for the tool-selection shadow comparison (A6/A7)."""

from __future__ import annotations

import json

import pytest

from app.services.ai import ai_conversation_service, tool_selection_shadow

# ---------------------------------------------------------------------------
# Mode resolution
# ---------------------------------------------------------------------------


def test_resolve_mode_defaults_to_rule(app, monkeypatch):
    monkeypatch.setitem(app.config, "AI_TOOL_SELECTION_MODE", "")
    monkeypatch.setitem(app.config, "AI_TOOL_CALLING_AGENT_ENABLED", False)
    assert tool_selection_shadow.resolve_tool_selection_mode() == "rule"


def test_resolve_mode_legacy_flag_maps_to_model(app, monkeypatch):
    monkeypatch.setitem(app.config, "AI_TOOL_SELECTION_MODE", "")
    monkeypatch.setitem(app.config, "AI_TOOL_CALLING_AGENT_ENABLED", True)
    assert tool_selection_shadow.resolve_tool_selection_mode() == "model"


def test_resolve_mode_explicit_overrides_legacy(app, monkeypatch):
    monkeypatch.setitem(app.config, "AI_TOOL_SELECTION_MODE", "shadow")
    monkeypatch.setitem(app.config, "AI_TOOL_CALLING_AGENT_ENABLED", True)
    assert tool_selection_shadow.resolve_tool_selection_mode() == "shadow"


def test_resolve_mode_ignores_garbage(app, monkeypatch):
    monkeypatch.setitem(app.config, "AI_TOOL_SELECTION_MODE", "banana")
    monkeypatch.setitem(app.config, "AI_TOOL_CALLING_AGENT_ENABLED", False)
    assert tool_selection_shadow.resolve_tool_selection_mode() == "rule"


# ---------------------------------------------------------------------------
# Comparison metrics
# ---------------------------------------------------------------------------


def test_compare_exact_match():
    result = tool_selection_shadow.compare_tool_selections(
        ["search_forum", "estimate_carbon_saving"],
        ["estimate_carbon_saving", "search_forum"],
    )
    assert result["exact_match"] is True
    assert result["jaccard"] == 1.0
    assert result["rule_only"] == []
    assert result["model_only"] == []
    assert result["matched"] == ["estimate_carbon_saving", "search_forum"]


def test_compare_partial_overlap():
    result = tool_selection_shadow.compare_tool_selections(
        ["search_forum", "read_user_memory"],
        ["search_forum", "find_nearby_recycling_places"],
    )
    assert result["exact_match"] is False
    assert result["matched"] == ["search_forum"]
    assert result["rule_only"] == ["read_user_memory"]
    assert result["model_only"] == ["find_nearby_recycling_places"]
    assert result["jaccard"] == pytest.approx(1 / 3, abs=1e-4)


def test_compare_both_empty_is_full_agreement():
    result = tool_selection_shadow.compare_tool_selections([], [])
    assert result["exact_match"] is True
    assert result["jaccard"] == 1.0


# ---------------------------------------------------------------------------
# Selection strategies
# ---------------------------------------------------------------------------


def test_rule_tool_selection_reads_decision(app):
    tools = tool_selection_shadow.rule_tool_selection({"should_retrieve_forum": True})
    assert tools == ["search_forum"]


def test_model_tool_selection_extracts_and_dedups(app):
    def fake_completion(*, messages, tools, tool_choice):
        assert tool_choice == "auto"
        return {
            "tool_calls": [
                {"name": "search_forum", "arguments": {}},
                {"name": "search_forum", "arguments": {}},
                {"name": "estimate_carbon_saving", "arguments": {}},
            ],
            "model": "fake-model",
            "usage": {"total_tokens": 12},
        }

    result = tool_selection_shadow.model_tool_selection(
        messages=[{"role": "user", "content": "hi"}],
        tools=[{"type": "function", "function": {"name": "search_forum"}}],
        completion_fn=fake_completion,
    )
    assert result["tools"] == ["search_forum", "estimate_carbon_saving"]
    assert result["model"] == "fake-model"


# ---------------------------------------------------------------------------
# JSONL logging
# ---------------------------------------------------------------------------


def test_record_shadow_comparison_writes_jsonl(app, monkeypatch, tmp_path):
    log_path = tmp_path / "shadow.jsonl"
    monkeypatch.setitem(app.config, "AI_TOOL_SELECTION_SHADOW_LOG", str(log_path))
    tool_selection_shadow.record_shadow_comparison({"mode": "shadow", "jaccard": 0.5})
    tool_selection_shadow.record_shadow_comparison({"mode": "shadow", "jaccard": 1.0})

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["jaccard"] == 0.5


def test_record_shadow_comparison_noop_when_unconfigured(app, monkeypatch, tmp_path):
    monkeypatch.setitem(app.config, "AI_TOOL_SELECTION_SHADOW_LOG", "")
    # Should not raise and should not create anything.
    tool_selection_shadow.record_shadow_comparison({"mode": "shadow"})
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Orchestrator dispatch
# ---------------------------------------------------------------------------


def _decision():
    return {"should_retrieve_forum": True, "prompt_memory": {}, "memory_candidates": []}


def test_mode_rule_serves_rule_reply_without_shadow(app, monkeypatch):
    monkeypatch.setitem(app.config, "AI_TOOL_SELECTION_MODE", "rule")
    called = {}

    def fake_chat(**kwargs):
        called["chat"] = True
        return {"reply": "rule-reply", "trace": {}}

    def boom(**kwargs):  # must not be called
        raise AssertionError("model path should not run in rule mode")

    monkeypatch.setattr(ai_conversation_service, "complete_chat_message", fake_chat)
    monkeypatch.setattr(ai_conversation_service, "complete_tool_calling_agent_message", boom)

    result = ai_conversation_service.complete_general_chat_with_mode(
        user_id=1, message="hi", decision=_decision()
    )
    assert result["reply"] == "rule-reply"
    assert "tool_selection_shadow" not in result
    assert called.get("chat") is True


def test_mode_model_serves_loop_and_attaches_free_comparison(app, monkeypatch):
    monkeypatch.setitem(app.config, "AI_TOOL_SELECTION_MODE", "model")
    monkeypatch.setitem(app.config, "AI_TOOL_SELECTION_SHADOW_LOG", "")

    def fake_loop(**kwargs):
        return {
            "reply": "model-reply",
            "trace": {},
            "tool_trace": [{"name": "search_forum"}],
        }

    monkeypatch.setattr(ai_conversation_service, "complete_tool_calling_agent_message", fake_loop)

    result = ai_conversation_service.complete_general_chat_with_mode(
        user_id=1, message="hi", decision=_decision()
    )
    assert result["reply"] == "model-reply"
    shadow = result["tool_selection_shadow"]
    assert shadow["served_by"] == "model"
    assert shadow["exact_match"] is True  # rule and model both picked search_forum
    assert result["trace"]["tool_selection_shadow"]["exact_match"] is True


def test_mode_shadow_serves_rule_reply_and_logs_model_selection(app, monkeypatch, tmp_path):
    monkeypatch.setitem(app.config, "AI_TOOL_SELECTION_MODE", "shadow")
    log_path = tmp_path / "shadow.jsonl"
    monkeypatch.setitem(app.config, "AI_TOOL_SELECTION_SHADOW_LOG", str(log_path))

    def fake_chat(**kwargs):
        return {"reply": "rule-reply", "trace": {}}

    def fake_model_selection(**kwargs):
        # Model diverges: it also wants find_nearby_recycling_places.
        return {
            "tools": ["search_forum", "find_nearby_recycling_places"],
            "model": "fake-model",
            "usage": {},
        }

    monkeypatch.setattr(ai_conversation_service, "complete_chat_message", fake_chat)
    monkeypatch.setattr(tool_selection_shadow, "model_tool_selection", fake_model_selection)

    result = ai_conversation_service.complete_general_chat_with_mode(
        user_id=1, message="where can I recycle?", decision=_decision()
    )
    assert result["reply"] == "rule-reply"  # served by the safe rule path
    shadow = result["tool_selection_shadow"]
    assert shadow["served_by"] == "rule"
    assert shadow["exact_match"] is False
    assert shadow["model_only"] == ["find_nearby_recycling_places"]

    logged = json.loads(log_path.read_text(encoding="utf-8").strip().splitlines()[0])
    assert logged["mode"] == "shadow"
    assert logged["shadow_model"] == "fake-model"
