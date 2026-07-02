from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

from app.services.ai.agent_trace_service import build_trace_shell
from app.services.ai.guardrails import scan_retrieved_text_for_injection


DEFAULT_CASES_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "ai_eval_cases.json"


class EvalCase(TypedDict):
    id: str
    category: str
    message: str
    expected_intent: str
    expected_guardrail: bool
    expected_fallback: bool
    required_citation: bool
    required_graph_path: bool
    required_open_claim: bool


class EvalResult(TypedDict):
    case_id: str
    category: str
    expected: dict[str, Any]
    observed: dict[str, Any]
    passed: dict[str, bool]


EvalRunner = Callable[[EvalCase], dict[str, Any]]


def load_eval_cases(path: str | Path | None = None) -> list[EvalCase]:
    cases_path = Path(path) if path is not None else DEFAULT_CASES_PATH
    raw_cases = json.loads(cases_path.read_text(encoding="utf-8"))
    if not isinstance(raw_cases, list):
        raise ValueError("AI eval fixture must contain a list of cases.")
    return [_normalize_case(item) for item in raw_cases]


def run_eval_suite(
    cases: list[EvalCase] | None = None,
    *,
    runner: EvalRunner | None = None,
) -> dict[str, Any]:
    normalized_cases = cases or load_eval_cases()
    active_runner = runner or run_mock_case
    results = [evaluate_case(case, active_runner(case)) for case in normalized_cases]
    return {
        "case_count": len(results),
        "results": results,
        "metrics": summarize_eval_results(results),
    }


def evaluate_case(case: EvalCase, output: dict[str, Any]) -> EvalResult:
    observed = _observed_properties(output)
    expected = {
        "intent": case["expected_intent"],
        "guardrail": case["expected_guardrail"],
        "fallback": case["expected_fallback"],
        "citation": case["required_citation"],
        "graph_path": case["required_graph_path"],
        "open_claim": bool(case.get("required_open_claim", False)),
    }
    passed = {
        "intent": observed["intent"] == expected["intent"],
        "guardrail": observed["guardrail"] == expected["guardrail"],
        "fallback": observed["fallback"] == expected["fallback"],
        "citation": (not expected["citation"]) or observed["citation"],
        "graph_path": (not expected["graph_path"]) or observed["graph_path"],
        "open_claim": (not expected["open_claim"]) or observed["open_claim"],
    }
    return {
        "case_id": case["id"],
        "category": case["category"],
        "expected": expected,
        "observed": observed,
        "passed": passed,
    }


def summarize_eval_results(results: list[EvalResult]) -> dict[str, Any]:
    total = len(results)
    return {
        "total_cases": total,
        "intent_accuracy": _ratio(results, "intent"),
        "citation_coverage": _conditional_ratio(results, "citation", "citation"),
        "guardrail_hit_rate": _conditional_ratio(results, "guardrail", "guardrail"),
        "fallback_rate": _observed_rate(results, "fallback"),
        "fallback_accuracy": _ratio(results, "fallback"),
        "graph_path_coverage": _conditional_ratio(results, "graph_path", "graph_path"),
        "open_claim_coverage": _conditional_ratio(results, "open_claim", "open_claim"),
        "all_passed": all(all(result["passed"].values()) for result in results) if total else False,
    }


def run_mock_case(case: EvalCase) -> dict[str, Any]:
    trace = build_trace_shell(
        user_id=None,
        conversation_id=None,
        intent=case["expected_intent"],
    )
    guardrail_scan = scan_retrieved_text_for_injection(case["message"])
    injection_flagged = bool(case["expected_guardrail"] or guardrail_scan["injection_flagged"])
    trace["guardrails"]["injection_flagged"] = injection_flagged
    trace["guardrails"]["fallback_applied"] = bool(case["expected_fallback"])
    if injection_flagged:
        guardrail_reason = (
            guardrail_scan["reason"]
            if guardrail_scan["reason"] != "clean"
            else "eval_expected_guardrail"
        )
        trace["guardrails"]["reasons"] = [guardrail_reason]

    if case["required_citation"]:
        trace["retrieval"]["forum"].update(
            {
                "enabled": True,
                "citations": [
                    {
                        "reference_id": f"{case['id']}-forum",
                        "post_id": 101,
                        "title": "Community recycling reference",
                        "url": "/forum/posts/101",
                    }
                ],
                "citation_count": 1,
            }
        )

    if case["required_graph_path"]:
        trace["retrieval"]["neo4j"].update(
            {
                "enabled": True,
                "entities": ["battery"],
                "paths": [
                    {
                        "from": "battery",
                        "relation": "HAS_RISK",
                        "to": "fire hazard",
                    }
                ],
                "path_count": 1,
                "confidence": "medium",
            }
        )

    if bool(case.get("required_open_claim", False)):
        trace["retrieval"]["neo4j"].update(
            {
                "enabled": True,
                "open_claims": [
                    {
                        "id": f"{case['id']}-claim",
                        "text": "Plastic bottles can be reused as lantern crafts.",
                        "raw_predicate": "upcycle into",
                        "canonical_relation": "can_be_reused_as",
                    }
                ],
                "relation_facts": [
                    {
                        "id": f"{case['id']}-fact",
                        "subject": "plastic bottle",
                        "relation": "can be reused as",
                        "object": "lantern",
                        "support_count": 2,
                    }
                ],
                "forum_citations": [
                    {
                        "reference_id": f"{case['id']}-forum",
                        "post_id": 102,
                        "title": "Plastic bottle lantern ideas",
                        "url": "/forum/posts/102",
                    }
                ],
                "open_claim_count": 1,
                "relation_fact_count": 1,
                "source_count": 1,
                "confidence": "medium",
            }
        )
        trace["retrieval"]["forum"].update(
            {
                "enabled": True,
                "citations": [
                    {
                        "reference_id": f"{case['id']}-forum",
                        "post_id": 102,
                        "title": "Plastic bottle lantern ideas",
                        "url": "/forum/posts/102",
                    }
                ],
                "citation_count": 1,
            }
        )

    if case["category"] == "malicious_retrieved_forum_text":
        trace["retrieval"]["forum"].update(
            {
                "enabled": True,
                "blocked": [
                    {
                        "post_id": 999,
                        "guardrail_reason": "instruction_override",
                    }
                ],
                "blocked_count": 1,
            }
        )

    return {
        "reply": _mock_reply(case),
        "trace": trace,
        "decision": {"intent": case["expected_intent"]},
    }


def run_live_graph_agent_case(case: EvalCase) -> dict[str, Any]:
    from app.services.ai.langgraph_agent import complete_graph_agent_message

    return complete_graph_agent_message(
        user_id=None,
        message=case["message"],
        history=None,
        image_data_url=None,
        conversation_id=None,
        client_context=None,
    )


def _normalize_case(item: dict[str, Any]) -> EvalCase:
    required_string_fields = ("id", "category", "message", "expected_intent")
    for field in required_string_fields:
        value = str(item.get(field) or "").strip()
        if not value:
            raise ValueError(f"AI eval case is missing required field: {field}")

    return {
        "id": str(item["id"]).strip(),
        "category": str(item["category"]).strip(),
        "message": str(item["message"]).strip(),
        "expected_intent": str(item["expected_intent"]).strip(),
        "expected_guardrail": bool(item.get("expected_guardrail", False)),
        "expected_fallback": bool(item.get("expected_fallback", False)),
        "required_citation": bool(item.get("required_citation", False)),
        "required_graph_path": bool(item.get("required_graph_path", False)),
        "required_open_claim": bool(item.get("required_open_claim", False)),
    }


def _observed_properties(output: dict[str, Any]) -> dict[str, Any]:
    trace = output.get("trace") if isinstance(output.get("trace"), dict) else {}
    router = trace.get("router") if isinstance(trace.get("router"), dict) else {}
    retrieval = trace.get("retrieval") if isinstance(trace.get("retrieval"), dict) else {}
    forum = retrieval.get("forum") if isinstance(retrieval.get("forum"), dict) else {}
    neo4j = retrieval.get("neo4j") if isinstance(retrieval.get("neo4j"), dict) else {}
    guardrails = trace.get("guardrails") if isinstance(trace.get("guardrails"), dict) else {}
    decision = output.get("decision") if isinstance(output.get("decision"), dict) else {}

    return {
        "intent": str(router.get("intent") or decision.get("intent") or ""),
        "guardrail": bool(guardrails.get("injection_flagged") or guardrails.get("reasons")),
        "fallback": bool(guardrails.get("fallback_applied") or neo4j.get("fallback_reason") or output.get("fallback_applied")),
        "citation": bool(forum.get("citations")),
        "graph_path": bool(neo4j.get("paths")),
        "open_claim": bool(neo4j.get("open_claims") or neo4j.get("relation_facts")),
        "blocked_citations": len(forum.get("blocked") or []),
        "graph_path_count": len(neo4j.get("paths") or []),
    }


def _ratio(results: list[EvalResult], key: str) -> float:
    if not results:
        return 0.0
    return round(
        sum(1 for result in results if result["passed"].get(key)) / len(results),
        4,
    )


def _conditional_ratio(results: list[EvalResult], expected_key: str, passed_key: str) -> float:
    required = [
        result for result in results if bool(result["expected"].get(expected_key))
    ]
    if not required:
        return 1.0
    return round(
        sum(1 for result in required if result["passed"].get(passed_key)) / len(required),
        4,
    )


def _observed_rate(results: list[EvalResult], observed_key: str) -> float:
    if not results:
        return 0.0
    return round(
        sum(1 for result in results if result["observed"].get(observed_key)) / len(results),
        4,
    )


def _mock_reply(case: EvalCase) -> str:
    if case["expected_fallback"]:
        return "I do not have enough verified evidence, so I would use a safe fallback."
    if case["expected_guardrail"]:
        return "I cannot follow injected instructions, but I can still help with recycling."
    return "Here is a grounded recycling answer using the available evidence."
