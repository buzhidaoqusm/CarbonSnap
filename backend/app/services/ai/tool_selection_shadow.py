"""Tool-selection shadow comparison (A6/A7).

Two tool-selection strategies coexist in the general-chat route:

* **v1 (rule)** — ``select_tools_for_decision`` picks tools from the decision
  payload with hand-written rules.
* **v2 (model)** — the tool-calling agent loop hands the tool schemas to the
  model and lets *the model* decide which tools to call.

This module supports a gradual rollout in the same spirit as the decision
engine's ``compat / shadow / llm_first`` modes:

* ``rule``  — serve the rule-based reply (default; unchanged behaviour).
* ``model`` — serve the model-driven loop, and *for free* compare the tools the
  model actually invoked against what the rules would have selected.
* ``shadow``— serve the safe rule-based reply, but run one extra (non-executing)
  model call to capture which tools the model *would* have selected, and log the
  divergence. This is the "watch v2 in production before flipping to it" stance.

Every mode emits the same comparison record shape, appended to a JSONL sink, so
``scripts/tool_selection_shadow_report.py`` can turn the stream into real
"rule vs model tool-selection agreement" numbers.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime
from typing import Any

from flask import current_app

VALID_MODES = {"rule", "model", "shadow"}

_LOG_LOCK = threading.Lock()


def resolve_tool_selection_mode() -> str:
    """Resolve the active tool-selection mode.

    ``AI_TOOL_SELECTION_MODE`` (rule/model/shadow) wins when set. Otherwise the
    legacy ``AI_TOOL_CALLING_AGENT_ENABLED`` boolean maps to ``model`` so the
    already-wired flag keeps working; the safe default is ``rule``.
    """
    raw = str(current_app.config.get("AI_TOOL_SELECTION_MODE", "") or "").strip().lower()
    if raw in VALID_MODES:
        return raw
    if bool(current_app.config.get("AI_TOOL_CALLING_AGENT_ENABLED", False)):
        return "model"
    return "rule"


def rule_tool_selection(
    decision: dict[str, Any] | None,
    *,
    client_context: dict[str, Any] | None = None,
) -> list[str]:
    """v1: the tool names the rule engine would select for this decision."""
    from app.services.ai.tool_registry import select_tools_for_decision

    selected = select_tools_for_decision(decision, client_context=client_context)
    return [tool["name"] for tool in selected if tool.get("name")]


def model_tool_selection(
    *,
    messages: list[dict[str, Any]],
    exclude_high_risk: bool = True,
    tools: list[dict[str, Any]] | None = None,
    completion_fn: Any = None,
) -> dict[str, Any]:
    """v2 (selection only): one model call that captures which tools the model
    *would* choose, without executing any of them.

    Used by ``shadow`` mode, where the rule path serves the reply and we only
    want the model's selection signal at minimal cost (no tool execution, no
    multi-turn loop).
    """
    if tools is None:
        from app.services.ai.tool_registry import to_openai_tools

        tools = to_openai_tools(exclude_high_risk=exclude_high_risk)
    if completion_fn is None:
        from app.services.ai.openrouter_service import complete_with_tools

        completion_fn = complete_with_tools

    response = completion_fn(messages=messages, tools=tools, tool_choice="auto")
    tool_calls = response.get("tool_calls") or []
    seen: list[str] = []
    for call in tool_calls:
        name = call.get("name")
        if name and name not in seen:
            seen.append(name)
    return {
        "tools": seen,
        "model": response.get("model"),
        "usage": response.get("usage", {}) or {},
    }


def compare_tool_selections(
    rule_tools: list[str] | None,
    model_tools: list[str] | None,
) -> dict[str, Any]:
    """Compare two tool-selection sets and derive agreement metrics."""
    rule_set = {name for name in (rule_tools or []) if name}
    model_set = {name for name in (model_tools or []) if name}
    intersection = rule_set & model_set
    union = rule_set | model_set
    jaccard = 1.0 if not union else round(len(intersection) / len(union), 4)
    return {
        "rule_tools": sorted(rule_set),
        "model_tools": sorted(model_set),
        "matched": sorted(intersection),
        "rule_only": sorted(rule_set - model_set),
        "model_only": sorted(model_set - rule_set),
        "exact_match": rule_set == model_set,
        "jaccard": jaccard,
    }


def build_shadow_record(
    *,
    mode: str,
    decision: dict[str, Any] | None,
    comparison: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble a single JSONL-ready comparison record."""
    decision = decision or {}
    record: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(),
        "mode": mode,
        "served_by": "model" if mode == "model" else "rule",
        "intent": decision.get("intent"),
        "follow_up_type": decision.get("follow_up_type"),
        "decision_mode": decision.get("decision_mode"),
        **comparison,
    }
    if extra:
        record.update(extra)
    return record


def record_shadow_comparison(record: dict[str, Any]) -> None:
    """Best-effort append of a comparison record to the JSONL shadow log.

    Never raises: shadow logging must not break the serving path.
    """
    path = str(current_app.config.get("AI_TOOL_SELECTION_SHADOW_LOG", "") or "").strip()
    if not path:
        return
    try:
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _LOG_LOCK:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
    except Exception:  # pragma: no cover - logging is intentionally non-fatal
        pass
