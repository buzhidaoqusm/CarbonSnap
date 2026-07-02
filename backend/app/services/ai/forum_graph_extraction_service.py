from __future__ import annotations

import json
from typing import Any

from app.services.ai.openrouter_service import complete_json_diagnostic
from app.services.ai.relation_normalization_service import normalize_graph_key


MIN_RELATION_CONFIDENCE = 0.55


def extract_forum_graph_payload(
    *,
    title: str,
    chunk_text: str,
    post_id: int,
    chunk_id: str,
    url: str,
) -> dict[str, Any]:
    diagnostic = complete_json_diagnostic(
        user_message=json.dumps(
            {
                "post_id": post_id,
                "chunk_id": chunk_id,
                "url": url,
                "title": title,
                "chunk_text": chunk_text,
            },
            ensure_ascii=False,
        ),
        system_prompt=_EXTRACTION_PROMPT,
    )
    payload = diagnostic.get("payload")
    if not isinstance(payload, dict):
        return {
            "entities": _fallback_entities(title=title, chunk_text=chunk_text),
            "relations": [],
            "fallback_reason": diagnostic.get("error") or "invalid_extraction_payload",
            "raw_reply": diagnostic.get("raw_reply"),
        }

    return {
        "entities": _normalize_entities(payload.get("entities")),
        "relations": _normalize_relations(payload.get("relations")),
        "fallback_reason": None,
        "raw_reply": diagnostic.get("raw_reply"),
    }


def _normalize_entities(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    entities: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        key = normalize_graph_key(name)
        if not key or key in seen:
            continue
        entities.append(
            {
                "key": key,
                "name": name,
                "entity_type": str(item.get("type") or item.get("entity_type") or "concept").strip()
                or "concept",
            }
        )
        seen.add(key)
    return entities


def _normalize_relations(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    relations: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject") or "").strip()
        predicate = str(item.get("predicate") or "").strip()
        object_name = str(item.get("object") or item.get("object_name") or "").strip()
        confidence = _safe_float(item.get("confidence"), default=0.0)
        if not subject or not predicate or not object_name or confidence < MIN_RELATION_CONFIDENCE:
            continue
        relations.append(
            {
                "subject": subject,
                "subject_key": normalize_graph_key(subject),
                "predicate": predicate,
                "object": object_name,
                "object_key": normalize_graph_key(object_name),
                "claim": str(item.get("claim") or "").strip()
                or f"{subject} {predicate} {object_name}",
                "stance": str(item.get("stance") or "supports").strip() or "supports",
                "confidence": confidence,
            }
        )
    return relations


def _fallback_entities(*, title: str, chunk_text: str) -> list[dict[str, Any]]:
    text = " ".join([str(title or ""), str(chunk_text or "")]).strip()
    if not text:
        return []
    words = [word.strip(".,;:!?()[]{}\"'").lower() for word in text.split()]
    candidates = [word for word in words if len(word) >= 4 and word.isascii()]
    if not candidates:
        return []
    name = candidates[0]
    return [{"key": normalize_graph_key(name), "name": name, "entity_type": "concept"}]


def _safe_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


_EXTRACTION_PROMPT = """
You extract open graph facts from CarbonSnap forum text.
Return exactly one JSON object. Do not wrap it in markdown.

Schema:
{
  "entities": [{"name": "short entity name", "type": "item|material|use|place|concept"}],
  "relations": [
    {
      "subject": "entity name",
      "predicate": "short relation phrase",
      "object": "entity name",
      "claim": "one sentence from or supported by the chunk",
      "stance": "supports|warns|contradicts",
      "confidence": 0.0
    }
  ]
}

Rules:
- Extract only facts supported by the provided chunk.
- Prefer concrete reusable relation phrases.
- Use confidence >= 0.55 only when the relation is clear.
- Keep entities concise and reusable across posts.
""".strip()
