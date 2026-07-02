from __future__ import annotations

from app.services.ai import eval_suite


def test_load_eval_cases_normalizes_fixture():
    cases = eval_suite.load_eval_cases()

    assert len(cases) >= 8
    assert cases[0]["id"] == "normal-battery-recycling"
    assert cases[0]["expected_intent"] == "recycling_analysis"
    assert cases[0]["required_citation"] is True
    assert {case["category"] for case in cases} >= {
        "normal_recycling_question",
        "open_forum_graph_question",
        "malicious_user_prompt",
        "neo4j_unavailable_fallback",
        "tool_failure_fallback",
    }


def test_mock_eval_suite_summarizes_metrics_without_external_api():
    summary = eval_suite.run_eval_suite()

    assert summary["case_count"] >= 8
    assert summary["metrics"]["intent_accuracy"] == 1.0
    assert summary["metrics"]["citation_coverage"] == 1.0
    assert summary["metrics"]["guardrail_hit_rate"] == 1.0
    assert summary["metrics"]["graph_path_coverage"] == 1.0
    assert summary["metrics"]["open_claim_coverage"] == 1.0
    assert summary["metrics"]["fallback_rate"] > 0
    assert summary["metrics"]["all_passed"] is True


def test_eval_case_detects_missing_required_citation():
    case = {
        "id": "citation-required",
        "category": "normal_recycling_question",
        "message": "Can I recycle batteries?",
        "expected_intent": "recycling_analysis",
        "expected_guardrail": False,
        "expected_fallback": False,
        "required_citation": True,
        "required_graph_path": False,
    }
    output = {
        "decision": {"intent": "recycling_analysis"},
        "trace": eval_suite.build_trace_shell(
            user_id=None,
            conversation_id=None,
            intent="recycling_analysis",
        ),
    }

    result = eval_suite.evaluate_case(case, output)

    assert result["passed"]["intent"] is True
    assert result["passed"]["citation"] is False


def test_custom_runner_can_be_injected_for_live_or_mock_smoke():
    cases = eval_suite.load_eval_cases()[:1]

    def runner(case):
        return eval_suite.run_mock_case(case)

    summary = eval_suite.run_eval_suite(cases, runner=runner)

    assert summary["case_count"] == 1
    assert summary["metrics"]["all_passed"] is True
