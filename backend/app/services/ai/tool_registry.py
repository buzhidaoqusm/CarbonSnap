from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypedDict

from flask import current_app


RiskLevel = Literal["low", "medium", "high"]


class ToolDefinition(TypedDict):
    name: str
    description: str
    input_schema: dict[str, Any]
    risk_level: RiskLevel
    auto_execute: bool
    handler: Callable[[dict[str, Any]], dict[str, Any]]


def list_tool_definitions(*, include_handlers: bool = False) -> list[dict[str, Any]]:
    definitions: list[dict[str, Any]] = []
    for tool in _tool_definitions():
        payload = dict(tool)
        if not include_handlers:
            payload.pop("handler", None)
        definitions.append(payload)
    return definitions


def get_tool_definition(name: str) -> dict[str, Any] | None:
    normalized_name = str(name or "").strip()
    for tool in list_tool_definitions(include_handlers=True):
        if tool["name"] == normalized_name:
            return tool
    return None


def run_tool(
    name: str,
    payload: dict[str, Any] | None = None,
    *,
    allow_high_risk: bool = False,
) -> dict[str, Any]:
    tool = get_tool_definition(name)
    if tool is None:
        return {
            "tool_name": str(name or "").strip(),
            "ok": False,
            "blocked": True,
            "risk_level": "unknown",
            "error": "unknown_tool",
            "output": {},
        }

    risk_level = str(tool["risk_level"])
    if risk_level == "high" and not allow_high_risk:
        return {
            "tool_name": tool["name"],
            "ok": False,
            "blocked": True,
            "risk_level": risk_level,
            "error": "high_risk_tool_requires_explicit_user_action",
            "output": {},
        }

    try:
        output = tool["handler"](dict(payload or {}))
    except Exception as exc:
        return {
            "tool_name": tool["name"],
            "ok": False,
            "blocked": False,
            "risk_level": risk_level,
            "error": str(exc)[:240],
            "output": {},
        }

    return {
        "tool_name": tool["name"],
        "ok": True,
        "blocked": False,
        "risk_level": risk_level,
        "output": output if isinstance(output, dict) else {"value": output},
    }


def select_tools_for_decision(
    decision: dict[str, Any] | None,
    *,
    client_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    decision = decision or {}
    selected: list[dict[str, Any]] = []
    intent = str(decision.get("intent") or "").strip()
    follow_up_type = str(decision.get("follow_up_type") or "").strip()

    if decision.get("prompt_memory") or decision.get("memory_candidates"):
        _append_selected(selected, "read_user_memory", reason="memory_context_available")

    if decision.get("should_retrieve_forum"):
        _append_selected(selected, "search_forum", reason="decision_requested_forum_rag")

    if intent in {"recycling_analysis", "recycling_follow_up"}:
        _append_selected(selected, "estimate_carbon_saving", reason="recycling_intent")
        if _is_graph_retrieval_enabled():
            _append_selected(selected, "query_recycling_graph", reason="neo4j_graphrag_enabled")

    location_state = (client_context or {}).get("location_state") or {}
    if follow_up_type == "nearby_search" or location_state.get("coordinates"):
        _append_selected(selected, "find_nearby_recycling_places", reason="nearby_recycling_request")

    return selected


def build_tool_trace_entries(
    selected_tools: list[dict[str, Any]],
    *,
    execution_mode: str = "planned_for_downstream_nodes",
) -> list[dict[str, Any]]:
    definitions = {tool["name"]: tool for tool in list_tool_definitions()}
    entries = []
    for selected in selected_tools:
        name = selected["name"]
        definition = definitions.get(name, {})
        entries.append(
            {
                "name": name,
                "risk_level": definition.get("risk_level", "unknown"),
                "auto_execute": bool(definition.get("auto_execute", False)),
                "execution_mode": execution_mode,
                "reason": selected.get("reason"),
                "output": selected.get("output", {}),
            }
        )
    return entries


def _tool_definitions() -> list[ToolDefinition]:
    return [
        {
            "name": "search_forum",
            "description": "Retrieve guarded forum post references with hybrid keyword/vector recall.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 8},
                },
                "required": ["query"],
            },
            "risk_level": "low",
            "auto_execute": True,
            "handler": _search_forum,
        },
        {
            "name": "query_recycling_graph",
            "description": "Query Neo4j GraphRAG recycling rules, risks, and item relationships.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "entities": {"type": "object"},
                },
                "required": ["query"],
            },
            "risk_level": "low",
            "auto_execute": True,
            "handler": _query_recycling_graph,
        },
        {
            "name": "estimate_carbon_saving",
            "description": "Estimate CO2 savings and points from item type and weight using configured factors.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "item_type": {"type": "string"},
                    "weight_kg": {"type": "number", "minimum": 0},
                },
                "required": ["item_type"],
            },
            "risk_level": "low",
            "auto_execute": True,
            "handler": _estimate_carbon_saving,
        },
        {
            "name": "find_nearby_recycling_places",
            "description": "Search OpenStreetMap recycling points near explicit coordinates or a manual area.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number"},
                    "lng": {"type": "number"},
                    "area": {"type": "string"},
                },
            },
            "risk_level": "medium",
            "auto_execute": False,
            "handler": _find_nearby_recycling_places,
        },
        {
            "name": "recommend_project",
            "description": "Read personalized community project recommendations for the current user.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                "required": ["user_id"],
            },
            "risk_level": "low",
            "auto_execute": True,
            "handler": _recommend_project,
        },
        {
            "name": "read_user_memory",
            "description": "Read the user's recycling preference summary for prompt grounding.",
            "input_schema": {
                "type": "object",
                "properties": {"user_id": {"type": "integer"}},
                "required": ["user_id"],
            },
            "risk_level": "low",
            "auto_execute": True,
            "handler": _read_user_memory,
        },
        {
            "name": "record_recycling_completion",
            "description": "Finalize a recycling completion and award points. Requires explicit user action.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "integer"},
                    "audit_image_url": {"type": "string"},
                },
                "required": ["case_id"],
            },
            "risk_level": "high",
            "auto_execute": False,
            "handler": _blocked_business_write,
        },
    ]


def _search_forum(payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.ai.forum_retrieval_service import retrieve_forum_references

    return retrieve_forum_references(
        query=str(payload.get("query") or "").strip(),
        limit=_optional_positive_int(payload.get("limit")),
    )


def _query_recycling_graph(payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.ai.neo4j_graph_retrieval_service import query_graph_context

    return query_graph_context(
        str(payload.get("query") or "").strip(),
        entities=payload.get("entities") if isinstance(payload.get("entities"), dict) else None,
    )


def _estimate_carbon_saving(payload: dict[str, Any]) -> dict[str, Any]:
    item_type = str(payload.get("item_type") or payload.get("waste_type") or "default").strip()
    weight_kg = _clamp_float(payload.get("weight_kg", 0.25), minimum=0.01, maximum=100.0)
    emission_factor = _resolve_emission_factor(item_type)
    co2_saved_kg = round(weight_kg * emission_factor, 2)
    return {
        "item_type": item_type,
        "weight_kg": round(weight_kg, 3),
        "emission_factor": emission_factor,
        "co2_saved_kg": co2_saved_kg,
        "carbon_points": round(co2_saved_kg * 10, 2),
    }


def _find_nearby_recycling_places(payload: dict[str, Any]) -> dict[str, Any]:
    from app.ai.tools.map.osm_public_provider import MapProviderError, OSMPublicMapProvider

    provider = OSMPublicMapProvider()
    area_label = str(payload.get("area") or payload.get("area_label") or "").strip() or None
    coordinates = payload.get("coordinates") if isinstance(payload.get("coordinates"), dict) else {}
    lat = payload.get("lat", coordinates.get("lat"))
    lng = payload.get("lng", coordinates.get("lng"))
    if (lat is None or lng is None) and area_label:
        geocoded = provider.geocode_area(area_label)
        lat = geocoded["lat"]
        lng = geocoded["lng"]
        area_label = geocoded.get("normalized_area") or area_label
    if lat is None or lng is None:
        raise MapProviderError("Coordinates or manual area are required.")

    locations = provider.search_nearby_recycling_points(
        lat=float(lat),
        lng=float(lng),
        area_label=area_label,
    )
    return {"locations": locations, "area_label": area_label}


def _recommend_project(payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.project import project_service

    user_id = int(payload["user_id"])
    limit = min(max(int(payload.get("limit") or 5), 1), 20)
    result = project_service.list_projects(page=1, per_page=limit, viewer_user_id=user_id)
    return {
        "items": result.get("items", []),
        "total": result.get("total", 0),
        "summary": result.get("summary", {}),
    }


def _read_user_memory(payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.ai.memory_service import get_prompt_memory_summary

    return {"summary": get_prompt_memory_summary(int(payload["user_id"]))}


def _blocked_business_write(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": "business_write_requires_explicit_user_action",
        "requested_payload_keys": sorted(str(key) for key in payload.keys()),
    }


def _append_selected(selected: list[dict[str, Any]], name: str, *, reason: str) -> None:
    if any(item["name"] == name for item in selected):
        return
    selected.append({"name": name, "reason": reason, "output": {}})


def _is_graph_retrieval_enabled() -> bool:
    try:
        from app.services.ai.neo4j_graph_retrieval_service import is_configured

        return is_configured()
    except Exception:
        return False


def _resolve_emission_factor(item_type: str) -> float:
    emission_factors = current_app.config.get("AI_EMISSION_FACTORS") or {"default": 1.0}
    normalized = str(item_type or "").strip().lower()
    for key, value in emission_factors.items():
        if key != "default" and str(key).lower() in normalized:
            return float(value)
    return float(emission_factors.get("default", 1.0))


def _optional_positive_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return None


def _clamp_float(value: Any, *, minimum: float, maximum: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = minimum
    return max(minimum, min(maximum, numeric))
