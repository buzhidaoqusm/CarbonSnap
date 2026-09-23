from __future__ import annotations

import json
from typing import Any

TRACE_SCHEMA_VERSION = "graph-agent-trace-v1"


def build_trace_shell(
    *,
    user_id: int | None,
    conversation_id: int | None,
    message_id: int | None = None,
    intent: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "message_id": message_id,
        "router": {"intent": intent, "follow_up_type": None, "confidence": None},
        "memory": {"used": False, "items": [], "summary": None},
        "entity_extraction": {"entities": []},
        "retrieval": {
            "forum": {"enabled": False, "reason": None, "citations": [], "blocked": []},
            "neo4j": {"enabled": False, "entities": [], "paths": [], "rules": []},
        },
        "guardrails": {
            "injection_flagged": False,
            "fallback_applied": False,
            "reasons": [],
        },
        "tool_calls": [],
        "prompt_versions": {},
        "model": {"provider": None, "name": None},
        "timing": {},
        "eval": {},
        "errors": [],
    }


def normalize_trace_for_storage(
    trace: dict[str, Any] | None,
    *,
    conversation_id: int | None = None,
    message_id: int | None = None,
) -> dict[str, Any] | None:
    if not trace:
        return None

    normalized = json.loads(json.dumps(trace, ensure_ascii=False, default=str))
    normalized.setdefault("schema_version", TRACE_SCHEMA_VERSION)
    if conversation_id is not None:
        normalized["conversation_id"] = conversation_id
    if message_id is not None:
        normalized["message_id"] = message_id
    return normalized


def attach_forum_citations_to_trace(
    trace: dict[str, Any] | None,
    forum_references: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    if not trace:
        return None

    normalized = json.loads(json.dumps(trace, ensure_ascii=False, default=str))
    retrieval = dict(normalized.get("retrieval") or {})
    forum = dict(retrieval.get("forum") or {})
    citations: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for reference in forum_references or []:
        if not isinstance(reference, dict):
            continue
        url = str(reference.get("url") or "").strip()
        title = str(reference.get("title") or "").strip()
        if not url or url in seen_urls:
            continue
        citations.append(
            {
                "reference_id": reference.get("reference_id"),
                "post_id": reference.get("post_id"),
                "title": title,
                "url": url,
            }
        )
        seen_urls.add(url)

    forum["citations"] = citations
    forum["citation_count"] = len(citations)
    if citations:
        forum["enabled"] = True
    retrieval["forum"] = forum
    normalized["retrieval"] = retrieval
    return normalized


def attach_graph_context_to_trace(
    trace: dict[str, Any] | None,
    graph_context: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not trace:
        return None

    normalized = json.loads(json.dumps(trace, ensure_ascii=False, default=str))
    graph_context = graph_context or {}
    retrieval = dict(normalized.get("retrieval") or {})
    neo4j = dict(retrieval.get("neo4j") or {})
    entities = graph_context.get("entities") or {}

    normalized["entity_extraction"] = {
        "entities": entities.get("matches") or [],
        "items": entities.get("items") or [],
        "materials": entities.get("materials") or [],
    }
    path_count = len(graph_context.get("paths") or [])
    rule_count = len(graph_context.get("rules") or [])
    risk_count = len(graph_context.get("risks") or [])
    relation_fact_count = len(graph_context.get("relation_facts") or [])
    neo4j.update(
        {
            "enabled": bool(graph_context.get("enabled")),
            "entities": entities.get("items") or [],
            "paths": graph_context.get("paths") or [],
            "rules": graph_context.get("rules") or [],
            "risks": graph_context.get("risks") or [],
            "facility_types": graph_context.get("facility_types") or [],
            "knowledge_chunks": graph_context.get("knowledge_chunks") or [],
            "open_claims": graph_context.get("open_claims") or [],
            "relation_facts": graph_context.get("relation_facts") or [],
            "forum_citations": graph_context.get("forum_citations") or [],
            "source_evidence": graph_context.get("source_evidence") or [],
            "confidence": graph_context.get("confidence"),
            "fallback_reason": graph_context.get("fallback_reason"),
            "path_count": path_count,
            "rule_count": rule_count,
            "risk_count": risk_count,
            "open_claim_count": len(graph_context.get("open_claims") or []),
            "relation_fact_count": relation_fact_count,
            "source_count": len(graph_context.get("forum_citations") or []),
            "evidence_count": path_count + rule_count + risk_count + relation_fact_count,
        }
    )
    retrieval["neo4j"] = neo4j
    normalized["retrieval"] = retrieval
    return normalized
