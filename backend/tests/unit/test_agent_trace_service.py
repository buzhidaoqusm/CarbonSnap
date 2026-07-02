from __future__ import annotations

from app.services.ai.agent_trace_service import (
    attach_graph_context_to_trace,
    build_trace_shell,
    normalize_trace_for_storage,
)


def test_build_trace_shell_contains_stable_sections():
    trace = build_trace_shell(
        user_id=1,
        conversation_id=2,
        message_id=3,
        intent="recycling_analysis",
    )

    assert trace["schema_version"] == "graph-agent-trace-v1"
    assert trace["user_id"] == 1
    assert trace["conversation_id"] == 2
    assert trace["message_id"] == 3
    assert trace["router"]["intent"] == "recycling_analysis"
    assert trace["memory"]["used"] is False
    assert trace["retrieval"]["forum"]["enabled"] is False
    assert trace["retrieval"]["neo4j"]["enabled"] is False
    assert trace["guardrails"]["fallback_applied"] is False
    assert trace["prompt_versions"] == {}
    assert trace["tool_calls"] == []


def test_normalize_trace_for_storage_overrides_conversation_and_message_ids():
    trace = build_trace_shell(
        user_id=1,
        conversation_id=None,
        message_id=None,
        intent="general_chat",
    )

    normalized = normalize_trace_for_storage(
        trace,
        conversation_id=22,
        message_id=33,
    )

    assert normalized["schema_version"] == "graph-agent-trace-v1"
    assert normalized["conversation_id"] == 22
    assert normalized["message_id"] == 33
    assert normalized["router"]["intent"] == "general_chat"


def test_attach_graph_context_to_trace_records_paths_and_fallback():
    trace = build_trace_shell(
        user_id=1,
        conversation_id=None,
        intent="general_chat",
    )

    updated = attach_graph_context_to_trace(
        trace,
        {
            "enabled": True,
            "entities": {
                "items": ["battery"],
                "materials": [],
                "matches": [{"canonical": "battery", "matched": ["batteries"]}],
            },
            "paths": [{"from": "battery", "relation": "HAS_RISK", "to": "fire hazard"}],
            "rules": [{"id": "rule-battery-dropoff", "title": "Use battery drop-off"}],
            "risks": [{"name": "fire hazard"}],
            "facility_types": ["household hazardous waste facility"],
            "knowledge_chunks": [{"id": "chunk-battery-001"}],
            "open_claims": [{"id": "claim-1", "raw_predicate": "upcycle into"}],
            "relation_facts": [
                {
                    "id": "fact-1",
                    "relation_key": "can_be_reused_as",
                    "support_count": 2,
                    "source_count": 1,
                }
            ],
            "forum_citations": [{"post_id": 12, "title": "Bottle lantern", "url": "/forum/posts/12"}],
            "confidence": "medium",
        },
    )

    assert updated["entity_extraction"]["items"] == ["battery"]
    assert updated["retrieval"]["neo4j"]["enabled"] is True
    assert updated["retrieval"]["neo4j"]["path_count"] == 1
    assert updated["retrieval"]["neo4j"]["rule_count"] == 1
    assert updated["retrieval"]["neo4j"]["risk_count"] == 1
    assert updated["retrieval"]["neo4j"]["open_claim_count"] == 1
    assert updated["retrieval"]["neo4j"]["relation_fact_count"] == 1
    assert updated["retrieval"]["neo4j"]["source_count"] == 1
    assert updated["retrieval"]["neo4j"]["evidence_count"] == 4
    assert updated["retrieval"]["neo4j"]["fallback_reason"] is None
