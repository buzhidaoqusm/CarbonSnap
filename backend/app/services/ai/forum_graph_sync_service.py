from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from app.services.ai import forum_graph_extraction_service
from app.services.ai.neo4j_graph_retrieval_service import _create_driver, is_configured
from app.services.ai.relation_normalization_service import (
    canonical_relation_definitions,
    normalize_graph_key,
    normalize_relation_type,
)


UPSERT_OPEN_GRAPH_CYPHER = """
MERGE (post:ForumPost {post_id: $post_id})
SET post.title = $title,
    post.url = $url,
    post.author_id = $author_id,
    post.created_at = $created_at,
    post.status = 'published'
MERGE (chunk:KnowledgeChunk {id: $chunk_id})
SET chunk.post_id = $post_id,
    chunk.chunk_index = $chunk_index,
    chunk.title = $title,
    chunk.text = $chunk_text,
    chunk.source = $url,
    chunk.source_type = 'forum_post',
    chunk.source_id = $post_id,
    chunk.source_url = $url,
    chunk.chunk_version = $chunk_version
MERGE (post)-[:HAS_CHUNK]->(chunk)
WITH post, chunk
UNWIND $entities AS entity_data
MERGE (entity:Entity {normalized_name: entity_data.key})
SET entity.display_name = entity_data.name,
    entity.entity_type = entity_data.entity_type,
    entity.updated_at = datetime()
MERGE (chunk)-[:MENTIONS]->(entity)
"""


UPSERT_RELATION_FACT_CYPHER = """
MERGE (subject:Entity {normalized_name: $subject_key})
SET subject.display_name = $subject_name,
    subject.entity_type = 'concept',
    subject.updated_at = datetime()
MERGE (object:Entity {normalized_name: $object_key})
SET object.display_name = $object_name,
    object.entity_type = 'concept',
    object.updated_at = datetime()
MERGE (relation:RelationType {key: $relation_key})
SET relation.label = $relation_label,
    relation.aliases = $relation_aliases,
    relation.created_by = $relation_created_by,
    relation.confidence = $relation_merge_confidence,
    relation.updated_at = datetime()
MERGE (fact:RelationFact {id: $fact_id})
SET fact.subject_key = $subject_key,
    fact.relation_key = $relation_key,
    fact.object_key = $object_key,
    fact.confidence = CASE
        WHEN coalesce(fact.confidence, 0.0) > $relation_confidence THEN fact.confidence
        ELSE $relation_confidence
    END,
    fact.updated_at = datetime()
MERGE (fact)-[:SUBJECT]->(subject)
MERGE (fact)-[:OBJECT]->(object)
MERGE (fact)-[:USES_RELATION]->(relation)
MERGE (claim:Claim {id: $claim_id})
SET claim.text = $claim_text,
    claim.stance = $stance,
    claim.confidence = $relation_confidence,
    claim.raw_predicate = $raw_predicate,
    claim.canonical_relation = $relation_key,
    claim.updated_at = datetime()
WITH fact, claim
MERGE (claim)-[:SUPPORTS]->(fact)
WITH fact, claim
MATCH (chunk:KnowledgeChunk {id: $chunk_id})
MERGE (chunk)-[:HAS_CLAIM]->(claim)
MERGE (evidence:Evidence {id: $evidence_id})
SET evidence.post_id = $post_id,
    evidence.chunk_id = $chunk_id,
    evidence.title = $title,
    evidence.url = $url,
    evidence.excerpt = $excerpt,
    evidence.raw_predicate = $raw_predicate,
    evidence.canonical_relation = $relation_key,
    evidence.extraction_confidence = $relation_confidence,
    evidence.active = true,
    evidence.updated_at = datetime()
MERGE (fact)-[:HAS_EVIDENCE]->(evidence)
WITH fact
MATCH (fact)-[:HAS_EVIDENCE]->(activeEvidence:Evidence)
WHERE coalesce(activeEvidence.active, true) = true
WITH fact, count(activeEvidence) AS support_count
SET fact.support_count = support_count
"""


DELETE_POST_OPEN_GRAPH_CYPHER = """
MATCH (evidence:Evidence {post_id: $post_id})
SET evidence.active = false,
    evidence.updated_at = datetime()
WITH collect(evidence) AS evidences
MATCH (post:ForumPost {post_id: $post_id})
SET post.status = 'deleted'
RETURN size(evidences) AS evidence_count
"""


UPSERT_FIXED_MADE_OF_CYPHER = """
MERGE (item:Item {name: $subject_name})
SET item.aliases = coalesce(item.aliases, []),
    item.source = 'open_forum_graph'
MERGE (material:Material {name: $object_name})
SET material.source = 'open_forum_graph'
MERGE (item)-[:MADE_OF]->(material)
"""


RELATION_TYPES_CYPHER = """
MATCH (relation:RelationType)
RETURN relation.key AS key, relation.label AS label, relation.aliases AS aliases
"""


def sync_forum_post_graph(
    *,
    post_id: int,
    title: str,
    content: str,
    author_id: int | None,
    created_at: datetime | None,
    chunks: list[Any],
    driver: Any | None = None,
) -> dict[str, Any]:
    if not chunks:
        return {"synced": False, "reason": "no_chunks", "relation_fact_count": 0}

    if driver is None and not is_configured():
        return {"synced": False, "reason": "neo4j_unavailable", "relation_fact_count": 0}

    owned_driver = None
    try:
        active_driver = driver
        if active_driver is None:
            owned_driver = _create_driver()
            active_driver = owned_driver
        with active_driver.session() as session:
            existing_relation_types = _load_relation_types(session)
            _ensure_seed_relation_types(session)
            relation_count = 0
            extraction_fallbacks: list[str] = []
            for chunk in chunks:
                chunk_id = _chunk_id(chunk)
                chunk_text = str(getattr(chunk, "chunk_text", "") or "")
                chunk_index = int(getattr(chunk, "chunk_index", 0) or 0)
                chunk_version = int(getattr(chunk, "chunk_version", 1) or 1)
                url = _post_url(post_id)
                extracted = forum_graph_extraction_service.extract_forum_graph_payload(
                    title=title,
                    chunk_text=chunk_text,
                    post_id=post_id,
                    chunk_id=chunk_id,
                    url=url,
                )
                if extracted.get("fallback_reason"):
                    extraction_fallbacks.append(str(extracted["fallback_reason"]))
                entities = _entities_for_chunk(extracted, chunk_text=chunk_text)
                session.run(
                    UPSERT_OPEN_GRAPH_CYPHER,
                    post_id=int(post_id),
                    title=title,
                    url=url,
                    author_id=author_id,
                    created_at=created_at.isoformat() if created_at else None,
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    chunk_text=chunk_text,
                    chunk_version=chunk_version,
                    entities=entities,
                )
                for relation in extracted.get("relations") or []:
                    normalized_relation = normalize_relation_type(
                        relation["predicate"],
                        existing_relation_types=existing_relation_types,
                    )
                    existing_relation_types.append(normalized_relation)
                    _upsert_relation_fact(
                        session,
                        post_id=post_id,
                        title=title,
                        url=url,
                        chunk_id=chunk_id,
                        chunk_text=chunk_text,
                        relation=relation,
                        normalized_relation=normalized_relation,
                    )
                    relation_count += 1

            return {
                "synced": True,
                "reason": None,
                "relation_fact_count": relation_count,
                "extraction_fallbacks": extraction_fallbacks,
            }
    except Exception as exc:
        return {"synced": False, "reason": f"graph_sync_error:{exc.__class__.__name__}", "error": str(exc)[:240]}
    finally:
        if owned_driver is not None:
            owned_driver.close()


def remove_forum_post_graph(*, post_id: int, driver: Any | None = None) -> dict[str, Any]:
    if driver is None and not is_configured():
        return {"removed": False, "reason": "neo4j_unavailable"}

    owned_driver = None
    try:
        active_driver = driver
        if active_driver is None:
            owned_driver = _create_driver()
            active_driver = owned_driver
        with active_driver.session() as session:
            records = list(session.run(DELETE_POST_OPEN_GRAPH_CYPHER, post_id=int(post_id)))
        count = 0
        if records:
            count = int(_record_get(records[0], "evidence_count") or 0)
        return {"removed": True, "evidence_count": count}
    except Exception as exc:
        return {"removed": False, "reason": f"graph_remove_error:{exc.__class__.__name__}", "error": str(exc)[:240]}
    finally:
        if owned_driver is not None:
            owned_driver.close()


def _upsert_relation_fact(
    session: Any,
    *,
    post_id: int,
    title: str,
    url: str,
    chunk_id: str,
    chunk_text: str,
    relation: dict[str, Any],
    normalized_relation: dict[str, Any],
) -> None:
    subject_key = relation["subject_key"]
    object_key = relation["object_key"]
    relation_key = normalized_relation["key"]
    fact_id = _relation_fact_id(subject_key, relation_key, object_key)
    claim_id = _stable_id("claim", fact_id, chunk_id, relation["claim"])
    evidence_id = _stable_id("evidence", fact_id, chunk_id, str(post_id))
    session.run(
        UPSERT_RELATION_FACT_CYPHER,
        post_id=int(post_id),
        title=title,
        url=url,
        chunk_id=chunk_id,
        subject_key=subject_key,
        subject_name=relation["subject"],
        object_key=object_key,
        object_name=relation["object"],
        relation_key=relation_key,
        relation_label=normalized_relation["label"],
        relation_aliases=normalized_relation["aliases"],
        relation_created_by=normalized_relation["merge_strategy"],
        relation_merge_confidence=float(normalized_relation["merge_confidence"]),
        relation_confidence=float(relation["confidence"]),
        fact_id=fact_id,
        claim_id=claim_id,
        claim_text=relation["claim"],
        stance=relation["stance"],
        raw_predicate=relation["predicate"],
        evidence_id=evidence_id,
        excerpt=_excerpt(chunk_text),
    )
    if normalized_relation["key"] == "made_of":
        session.run(
            UPSERT_FIXED_MADE_OF_CYPHER,
            subject_name=relation["subject"],
            object_name=relation["object"],
        )


def _ensure_seed_relation_types(session: Any) -> None:
    for relation in canonical_relation_definitions():
        session.run(
            """
            MERGE (relation:RelationType {key: $key})
            SET relation.label = $label,
                relation.aliases = $aliases,
                relation.created_by = 'seed',
                relation.confidence = 1.0
            """,
            key=relation["key"],
            label=relation["label"],
            aliases=relation["aliases"],
        )


def _load_relation_types(session: Any) -> list[dict[str, Any]]:
    rows = list(session.run(RELATION_TYPES_CYPHER))
    return [
        {
            "key": str(_record_get(row, "key") or ""),
            "label": str(_record_get(row, "label") or ""),
            "aliases": list(_record_get(row, "aliases") or []),
        }
        for row in rows
        if _record_get(row, "key")
    ]


def _entities_for_chunk(extracted: dict[str, Any], *, chunk_text: str) -> list[dict[str, Any]]:
    entities = list(extracted.get("entities") or [])
    seen = {item.get("key") for item in entities}
    for relation in extracted.get("relations") or []:
        for key_name, name_key in (("subject_key", "subject"), ("object_key", "object")):
            key = relation.get(key_name)
            if key and key not in seen:
                entities.append(
                    {
                        "key": key,
                        "name": relation.get(name_key) or str(key).replace("_", " "),
                        "entity_type": "concept",
                    }
                )
                seen.add(key)
    if not entities and chunk_text.strip():
        fallback = normalize_graph_key(chunk_text.split()[0])
        if fallback:
            entities.append({"key": fallback, "name": fallback.replace("_", " "), "entity_type": "concept"})
    return entities


def _chunk_id(chunk: Any) -> str:
    embedding_id = str(getattr(chunk, "embedding_id", "") or "").strip()
    if embedding_id:
        return embedding_id
    row_id = getattr(chunk, "id", None)
    if row_id is not None:
        return f"forum-chunk-{row_id}"
    return _stable_id("chunk", str(getattr(chunk, "post_id", "")), str(getattr(chunk, "chunk_index", "")))


def _relation_fact_id(subject_key: str, relation_key: str, object_key: str) -> str:
    return f"fact-{_stable_hash(subject_key, relation_key, object_key)}"


def _stable_id(prefix: str, *parts: str) -> str:
    return f"{prefix}-{_stable_hash(*parts)}"


def _stable_hash(*parts: str) -> str:
    digest = hashlib.sha1("\u241f".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return digest[:20]


def _post_url(post_id: int) -> str:
    return f"/forum/posts/{int(post_id)}"


def _excerpt(text: str, *, limit: int = 320) -> str:
    return " ".join(str(text or "").split())[:limit]


def _record_get(record: Any, key: str) -> Any:
    if isinstance(record, dict):
        return record.get(key)
    try:
        return record[key]
    except Exception:
        return getattr(record, key, None)
