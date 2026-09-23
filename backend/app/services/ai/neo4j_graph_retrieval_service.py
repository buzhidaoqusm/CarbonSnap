from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

from flask import current_app, has_app_context

from app.services.ai.entity_extraction_service import extract_recycling_entities

GRAPH_CONTEXT_CYPHER = """
MATCH (item:Item)
WHERE toLower(item.name) IN $items
   OR any(alias IN coalesce(item.aliases, []) WHERE toLower(alias) IN $items)
OPTIONAL MATCH (item)-[:MADE_OF]->(material:Material)
OPTIONAL MATCH (item)-[:DISPOSE_AS]->(method:DisposalMethod)
OPTIONAL MATCH (method)-[:ACCEPTED_AT]->(facility:FacilityType)
OPTIONAL MATCH (item)-[:HAS_RULE]->(rule:Rule)
OPTIONAL MATCH (item)-[:HAS_RISK]->(risk:Risk)
OPTIONAL MATCH (chunk:KnowledgeChunk)-[:DESCRIBES]->(item)
RETURN
  item.name AS item_name,
  material.name AS material_name,
  method.name AS disposal_method,
  facility.name AS facility_type,
  collect(DISTINCT {
    id: rule.id,
    title: rule.title,
    description: rule.description,
    locality: rule.locality
  }) AS rules,
  collect(DISTINCT {
    name: risk.name,
    description: risk.description,
    severity: risk.severity
  }) AS risks,
  collect(DISTINCT {
    id: chunk.id,
    title: chunk.title,
    text: chunk.text,
    source: chunk.source
  }) AS knowledge_chunks
ORDER BY item.name
"""

OPEN_GRAPH_CONTEXT_CYPHER = """
MATCH (fact:RelationFact)
OPTIONAL MATCH (fact)-[:SUBJECT]->(subject:Entity)
OPTIONAL MATCH (fact)-[:OBJECT]->(object:Entity)
OPTIONAL MATCH (fact)-[:USES_RELATION]->(relation:RelationType)
OPTIONAL MATCH (fact)-[:HAS_EVIDENCE]->(matchedEvidence:Evidence)
OPTIONAL MATCH (matchedClaim:Claim)-[:SUPPORTS]->(fact)
WITH fact, subject, object, relation, matchedEvidence, matchedClaim,
  [term IN $terms WHERE
    subject.normalized_name = term
    OR object.normalized_name = term
    OR toLower(coalesce(subject.display_name, '')) = term
    OR toLower(coalesce(object.display_name, '')) = term
  ] AS exactEntityTerms,
  [term IN $terms WHERE
    subject.normalized_name CONTAINS term
    OR term CONTAINS subject.normalized_name
    OR object.normalized_name CONTAINS term
    OR term CONTAINS object.normalized_name
    OR toLower(coalesce(subject.display_name, '')) CONTAINS term
    OR toLower(coalesce(object.display_name, '')) CONTAINS term
  ] AS relatedEntityTerms,
  [term IN $terms WHERE
    toLower(coalesce(relation.label, '')) CONTAINS term
    OR toLower(coalesce(matchedEvidence.title, '')) CONTAINS term
    OR toLower(coalesce(matchedEvidence.excerpt, '')) CONTAINS term
    OR toLower(coalesce(matchedClaim.text, '')) CONTAINS term
  ] AS textTerms
WHERE any(term IN $terms WHERE
    subject.normalized_name CONTAINS term
    OR term CONTAINS subject.normalized_name
    OR object.normalized_name CONTAINS term
    OR term CONTAINS object.normalized_name
    OR toLower(coalesce(subject.display_name, '')) CONTAINS term
    OR toLower(coalesce(object.display_name, '')) CONTAINS term
    OR toLower(coalesce(relation.label, '')) CONTAINS term
    OR toLower(coalesce(matchedEvidence.title, '')) CONTAINS term
    OR toLower(coalesce(matchedEvidence.excerpt, '')) CONTAINS term
    OR toLower(coalesce(matchedClaim.text, '')) CONTAINS term
)
WITH fact, subject, object, relation,
  CASE
    WHEN size(exactEntityTerms) > 0 THEN 100
    WHEN size(relatedEntityTerms) > 0 THEN 80
    WHEN size(textTerms) > 0 THEN 40
    ELSE 0
  END AS match_score
OPTIONAL MATCH (claim:Claim)-[:SUPPORTS]->(fact)
OPTIONAL MATCH (fact)-[:HAS_EVIDENCE]->(evidence:Evidence)
WHERE evidence IS NULL OR coalesce(evidence.active, true) = true
RETURN
  fact.id AS fact_id,
  fact.subject_key AS subject_key,
  fact.relation_key AS relation_key,
  fact.object_key AS object_key,
  fact.support_count AS support_count,
  fact.confidence AS fact_confidence,
  subject.display_name AS subject_name,
  object.display_name AS object_name,
  relation.label AS relation_label,
  relation.aliases AS relation_aliases,
  max(match_score) AS match_score,
  collect(DISTINCT {
    id: claim.id,
    text: claim.text,
    stance: claim.stance,
    confidence: claim.confidence,
    raw_predicate: claim.raw_predicate,
    canonical_relation: claim.canonical_relation
  }) AS claims,
  collect(DISTINCT {
    id: evidence.id,
    post_id: evidence.post_id,
    chunk_id: evidence.chunk_id,
    title: evidence.title,
    url: evidence.url,
    excerpt: evidence.excerpt,
    raw_predicate: evidence.raw_predicate,
    canonical_relation: evidence.canonical_relation,
    extraction_confidence: evidence.extraction_confidence
  }) AS evidence
ORDER BY match_score DESC, coalesce(fact.support_count, 0) DESC, coalesce(fact.confidence, 0.0) DESC
LIMIT 12
"""


def is_configured() -> bool:
    return bool(
        _get_bool_config("AI_NEO4J_GRAPHRAG_ENABLED", False)
        and _get_config_value("NEO4J_URI")
        and _get_config_value("NEO4J_USERNAME")
        and _get_config_value("NEO4J_PASSWORD")
    )


def query_graph_context(
    message: str,
    entities: dict[str, Any] | None = None,
    *,
    driver: Any | None = None,
) -> dict[str, Any]:
    resolved_entities = entities or extract_recycling_entities(message)
    entity_names = _entity_names_for_lookup(resolved_entities)

    if not _get_bool_config("AI_NEO4J_GRAPHRAG_ENABLED", False):
        return _fallback_context(
            entities=resolved_entities,
            fallback_reason="feature_disabled",
        )
    if not is_configured():
        return _fallback_context(
            entities=resolved_entities,
            fallback_reason="neo4j_unavailable",
        )
    owned_driver = None
    try:
        active_driver = driver
        if active_driver is None:
            owned_driver = _create_driver()
            active_driver = owned_driver
        with active_driver.session() as session:
            records = (
                list(session.run(GRAPH_CONTEXT_CYPHER, items=entity_names)) if entity_names else []
            )
            open_records = list(
                session.run(
                    OPEN_GRAPH_CONTEXT_CYPHER,
                    terms=_open_graph_terms(resolved_entities, message),
                )
            )
        return _context_from_records(
            records,
            open_records=open_records,
            entities=resolved_entities,
        )
    except Exception as exc:
        return _fallback_context(
            entities=resolved_entities,
            fallback_reason="neo4j_unavailable",
            error=str(exc),
        )
    finally:
        if owned_driver is not None:
            owned_driver.close()


def build_graph_prompt_block(graph_context: dict[str, Any] | None) -> str:
    if not graph_context or not graph_context.get("enabled"):
        return ""

    lines = ["Neo4j recycling graph evidence available for this turn:"]
    entities = graph_context.get("entities") or {}
    items = [str(item) for item in entities.get("items") or [] if item]
    if items:
        lines.append(f"- Matched items: {', '.join(items)}")

    for path in (graph_context.get("paths") or [])[:8]:
        source = path.get("from")
        relation = path.get("relation")
        target = path.get("to")
        if source and relation and target:
            lines.append(f"- Path: {source} --{relation}--> {target}")

    for rule in (graph_context.get("rules") or [])[:4]:
        title = str(rule.get("title") or rule.get("id") or "").strip()
        description = str(rule.get("description") or "").strip()
        if title and description:
            lines.append(f"- Rule: {title}: {description}")
        elif title:
            lines.append(f"- Rule: {title}")

    for risk in (graph_context.get("risks") or [])[:4]:
        name = str(risk.get("name") or "").strip()
        severity = str(risk.get("severity") or "").strip()
        description = str(risk.get("description") or "").strip()
        if name and description:
            suffix = f" ({severity})" if severity else ""
            lines.append(f"- Risk: {name}{suffix}: {description}")
        elif name:
            lines.append(f"- Risk: {name}")

    facilities = [str(item) for item in graph_context.get("facility_types") or [] if item]
    if facilities:
        lines.append(f"- Facility types: {', '.join(facilities[:4])}")

    for fact in (graph_context.get("relation_facts") or [])[:6]:
        subject = str(fact.get("subject") or fact.get("subject_key") or "").strip()
        relation = str(fact.get("relation") or fact.get("relation_key") or "").strip()
        obj = str(fact.get("object") or fact.get("object_key") or "").strip()
        support_count = fact.get("support_count")
        if subject and relation and obj:
            suffix = f" (supported by {support_count} source(s))" if support_count else ""
            lines.append(f"- Open claim: {subject} --{relation}--> {obj}{suffix}")

    citations = graph_context.get("forum_citations") or []
    if citations:
        lines.append("Forum sources attached to graph evidence:")
        for citation in citations[:4]:
            title = str(citation.get("title") or citation.get("url") or "").strip()
            url = str(citation.get("url") or "").strip()
            if title and url:
                lines.append(f"- [{title}]({url})")

    lines.extend(
        [
            "Graph evidence rules:",
            "- Treat graph rules and risks as higher-priority evidence than forum anecdotes.",
            "- Use open forum graph claims as community examples only when they do not conflict with graph rules.",
            "- If you use open forum graph claims, cite the attached forum source links.",
            "- If graph and forum evidence are both missing, avoid overclaiming and suggest checking local recycling guidance.",
        ]
    )
    return "\n".join(lines)


def format_graph_paths(records: Iterable[Any]) -> list[dict[str, str]]:
    paths: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for record in records:
        item_name = _record_get(record, "item_name")
        material_name = _record_get(record, "material_name")
        disposal_method = _record_get(record, "disposal_method")
        facility_type = _record_get(record, "facility_type")

        for relation, target in (
            ("MADE_OF", material_name),
            ("DISPOSE_AS", disposal_method),
            ("ACCEPTED_AT", facility_type),
        ):
            if relation == "ACCEPTED_AT":
                source = disposal_method
            else:
                source = item_name
            if not source or not target:
                continue
            key = (str(source), relation, str(target))
            if key in seen:
                continue
            paths.append({"from": str(source), "relation": relation, "to": str(target)})
            seen.add(key)

        for rule in _clean_maps(_record_get(record, "rules")):
            title = rule.get("title")
            if item_name and title:
                key = (str(item_name), "HAS_RULE", str(title))
                if key not in seen:
                    paths.append({"from": str(item_name), "relation": "HAS_RULE", "to": str(title)})
                    seen.add(key)

        for risk in _clean_maps(_record_get(record, "risks")):
            name = risk.get("name")
            if item_name and name:
                key = (str(item_name), "HAS_RISK", str(name))
                if key not in seen:
                    paths.append({"from": str(item_name), "relation": "HAS_RISK", "to": str(name)})
                    seen.add(key)

    return paths


def _context_from_records(
    records: list[Any],
    *,
    open_records: list[Any] | None = None,
    entities: dict[str, Any],
) -> dict[str, Any]:
    rules = _unique_maps(
        rule
        for record in records
        for rule in _clean_maps(_record_get(record, "rules"))
        if rule.get("id") or rule.get("title")
    )
    risks = _unique_maps(
        risk
        for record in records
        for risk in _clean_maps(_record_get(record, "risks"))
        if risk.get("name")
    )
    knowledge_chunks = _unique_maps(
        chunk
        for record in records
        for chunk in _clean_maps(_record_get(record, "knowledge_chunks"))
        if chunk.get("id") or chunk.get("title")
    )
    facility_types = sorted(
        {
            str(value)
            for value in (_record_get(record, "facility_type") for record in records)
            if value
        }
    )
    paths = format_graph_paths(records)
    open_context = _open_context_from_records(open_records or [])

    return {
        "enabled": True,
        "entities": entities,
        "paths": paths,
        "rules": rules,
        "risks": risks,
        "facility_types": facility_types,
        "knowledge_chunks": knowledge_chunks,
        **open_context,
        "confidence": "medium"
        if paths or rules or risks or open_context["relation_facts"]
        else "low",
    }


def _fallback_context(
    *,
    entities: dict[str, Any],
    fallback_reason: str,
    error: str | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "enabled": False,
        "fallback_reason": fallback_reason,
        "entities": entities,
        "paths": [],
        "rules": [],
        "risks": [],
        "facility_types": [],
        "knowledge_chunks": [],
        "open_claims": [],
        "relation_facts": [],
        "forum_citations": [],
        "source_evidence": [],
        "confidence": "low",
    }
    if error:
        context["error"] = error[:240]
    return context


def _create_driver() -> Any:
    try:
        from neo4j import GraphDatabase
    except ImportError as exc:
        raise RuntimeError("neo4j_driver_missing") from exc

    return GraphDatabase.driver(
        _get_config_value("NEO4J_URI"),
        auth=(
            _get_config_value("NEO4J_USERNAME"),
            _get_config_value("NEO4J_PASSWORD"),
        ),
    )


def _entity_names_for_lookup(entities: dict[str, Any]) -> list[str]:
    names = []
    for value in entities.get("items") or []:
        normalized = str(value or "").strip().lower()
        if normalized and normalized not in names:
            names.append(normalized)
    return names


def _open_graph_terms(entities: dict[str, Any], message: str) -> list[str]:
    terms: list[str] = []
    for value in [*(entities.get("items") or []), *(entities.get("materials") or [])]:
        _append_open_graph_term(terms, value)
    words = [
        _normalize_key(item)
        for item in str(message or "").split()
        if len(str(item).strip(".,;:!?")) >= 4
    ]
    for word in words[:8]:
        _append_open_graph_term(terms, word)
    for alias in _open_graph_alias_terms(message):
        _append_open_graph_term(terms, alias)
    fallback = _normalize_key(message)
    if fallback:
        return terms or [fallback]
    return ["__no_open_graph_terms__"]


def _append_open_graph_term(terms: list[str], value: Any) -> None:
    normalized = _normalize_key(value)
    if not normalized or normalized in _OPEN_GRAPH_STOPWORDS:
        return
    variants = [normalized, normalized.replace(" ", "_")]
    if " " in normalized:
        variants.extend(part for part in normalized.split() if len(part) >= 4)
    for variant in variants:
        if variant and variant not in terms:
            terms.append(variant)


def _open_graph_alias_terms(message: str) -> list[str]:
    normalized_message = str(message or "").lower()
    aliases: list[str] = []
    for trigger, values in _OPEN_GRAPH_QUERY_ALIASES.items():
        if trigger in normalized_message:
            aliases.extend(values)
    return aliases


def _open_context_from_records(records: list[Any]) -> dict[str, Any]:
    relation_facts: list[dict[str, Any]] = []
    open_claims: list[dict[str, Any]] = []
    source_evidence: list[dict[str, Any]] = []
    citations_by_url: dict[str, dict[str, Any]] = {}

    for record in records:
        evidence_items = _clean_maps(_record_get(record, "evidence"))
        claim_items = _clean_maps(_record_get(record, "claims"))
        relation_fact = {
            "id": _record_get(record, "fact_id"),
            "subject_key": _record_get(record, "subject_key"),
            "subject": _record_get(record, "subject_name") or _record_get(record, "subject_key"),
            "relation_key": _record_get(record, "relation_key"),
            "relation": _record_get(record, "relation_label")
            or _record_get(record, "relation_key"),
            "object_key": _record_get(record, "object_key"),
            "object": _record_get(record, "object_name") or _record_get(record, "object_key"),
            "support_count": int(_record_get(record, "support_count") or len(evidence_items) or 0),
            "confidence": _record_get(record, "fact_confidence"),
            "match_score": _record_get(record, "match_score"),
            "source_count": len({item.get("url") for item in evidence_items if item.get("url")}),
        }
        if relation_fact["id"]:
            relation_facts.append(relation_fact)
        for claim in claim_items:
            if claim.get("id"):
                open_claims.append(claim)
        for evidence in evidence_items:
            if not evidence.get("id"):
                continue
            source_evidence.append(evidence)
            url = str(evidence.get("url") or "").strip()
            if not url or url in citations_by_url:
                continue
            citations_by_url[url] = {
                "reference_id": f"forum-post-{evidence.get('post_id')}",
                "post_id": evidence.get("post_id"),
                "title": evidence.get("title") or url,
                "url": url,
                "excerpt": evidence.get("excerpt"),
                "source": "open_graph",
            }

    return {
        "open_claims": _unique_maps(open_claims),
        "relation_facts": _unique_maps(relation_facts),
        "forum_citations": list(citations_by_url.values())[:3],
        "source_evidence": _unique_maps(source_evidence),
    }


def _normalize_key(value: Any) -> str:
    return " ".join(str(value or "").lower().strip().replace("_", " ").split())


_OPEN_GRAPH_STOPWORDS = {
    "about",
    "another",
    "besides",
    "could",
    "give",
    "good",
    "have",
    "ideas",
    "method",
    "methods",
    "option",
    "recycle",
    "recycling",
    "should",
    "what",
    "where",
}


_OPEN_GRAPH_QUERY_ALIASES = {
    "塑料瓶": ["plastic bottle", "plastic_bottle", "bottle"],
    "瓶子": ["plastic bottle", "bottle", "glass jars"],
    "电池": ["battery", "batteries", "rechargeable batteries"],
    "可充电电池": ["rechargeable batteries", "battery"],
    "易拉罐": ["aluminum can", "soda can"],
    "铝罐": ["aluminum can", "soda can"],
    "玻璃罐": ["glass jars", "glass jar"],
    "玻璃瓶": ["glass jars", "glass jar"],
    "纸箱": ["cardboard", "cardboard mailer"],
    "纸板": ["cardboard", "cardboard mailer"],
    "咖啡罐": ["coffee tin"],
    "电子垃圾": ["e-waste", "electronics"],
    "旧手机": ["e-waste", "electronics"],
    "灯笼": ["lantern", "mini lantern", "plastic bottle"],
    "收纳": ["organizer", "holder", "storage"],
}


def _clean_maps(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value:
        if not isinstance(item, dict):
            continue
        filtered = {key: child for key, child in item.items() if child not in (None, "", [])}
        if filtered:
            cleaned.append(filtered)
    return cleaned


def _unique_maps(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for item in items:
        key = tuple(sorted((str(k), str(v)) for k, v in item.items()))
        if key in seen:
            continue
        unique.append(item)
        seen.add(key)
    return unique


def _record_get(record: Any, key: str) -> Any:
    if isinstance(record, dict):
        return record.get(key)
    try:
        return record[key]
    except Exception:
        return getattr(record, key, None)


def _get_config_value(name: str) -> str:
    if has_app_context():
        return str(current_app.config.get(name, "") or "").strip()
    return os.getenv(name, "").strip()


def _get_bool_config(name: str, default: bool) -> bool:
    if has_app_context():
        return bool(current_app.config.get(name, default))
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}
