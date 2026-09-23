from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

_NON_WORD_RE = re.compile(r"[^\w\u4e00-\u9fff]+", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")

_CANONICAL_RELATIONS: tuple[dict[str, Any], ...] = (
    {
        "key": "has",
        "label": "has",
        "aliases": (
            "has",
            "have",
            "contains",
            "contain",
            "owns",
            "own",
            "holds",
            "hold",
            "possesses",
            "possess",
            "拥有",
            "持有",
            "含有",
            "包含",
        ),
    },
    {
        "key": "can_be_reused_as",
        "label": "can be reused as",
        "aliases": (
            "reuse as",
            "reused as",
            "can be reused as",
            "repurpose as",
            "repurposed as",
            "upcycle into",
            "upcycled into",
            "turn into",
            "turned into",
            "convert into",
            "converted into",
            "改造成",
            "改为",
            "做成",
            "变成",
            "再利用为",
        ),
    },
    {
        "key": "made_of",
        "label": "made of",
        "aliases": (
            "made of",
            "made from",
            "composed of",
            "consists of",
            "material is",
            "材质是",
            "由 制成",
            "由制成",
            "组成",
        ),
    },
)


def normalize_graph_key(value: str) -> str:
    normalized = _normalize_text(value)
    return normalized.replace(" ", "_")


def normalize_relation_type(
    raw_predicate: str,
    *,
    existing_relation_types: list[dict[str, Any]] | None = None,
    similarity_threshold: float = 0.82,
) -> dict[str, Any]:
    normalized = _normalize_text(raw_predicate)
    if not normalized:
        return _relation_payload(
            key="related_to",
            label="related to",
            aliases=["related to"],
            raw_predicate=raw_predicate,
            merge_confidence=0.0,
            merge_strategy="fallback_blank",
        )

    canonical_match = _match_known_relation(normalized)
    if canonical_match is not None:
        return {
            **canonical_match,
            "raw_predicate": raw_predicate,
            "merge_confidence": 1.0,
            "merge_strategy": "alias",
        }

    existing_match = _match_existing_relation(
        normalized,
        existing_relation_types or [],
        threshold=similarity_threshold,
    )
    if existing_match is not None:
        return existing_match

    return _relation_payload(
        key=normalize_graph_key(raw_predicate) or "related_to",
        label=normalized,
        aliases=[normalized],
        raw_predicate=raw_predicate,
        merge_confidence=0.72,
        merge_strategy="created_from_predicate",
    )


def canonical_relation_definitions() -> list[dict[str, Any]]:
    return [
        _relation_payload(
            key=str(item["key"]),
            label=str(item["label"]),
            aliases=[str(alias) for alias in item["aliases"]],
            raw_predicate=str(item["label"]),
            merge_confidence=1.0,
            merge_strategy="seed",
        )
        for item in _CANONICAL_RELATIONS
    ]


def _match_known_relation(normalized_predicate: str) -> dict[str, Any] | None:
    for item in _CANONICAL_RELATIONS:
        aliases = [_normalize_text(alias) for alias in item["aliases"]]
        if normalized_predicate in aliases:
            return _relation_payload(
                key=str(item["key"]),
                label=str(item["label"]),
                aliases=aliases,
                raw_predicate=normalized_predicate,
                merge_confidence=1.0,
                merge_strategy="alias",
            )
    return None


def _match_existing_relation(
    normalized_predicate: str,
    existing_relation_types: list[dict[str, Any]],
    *,
    threshold: float,
) -> dict[str, Any] | None:
    best: tuple[float, dict[str, Any]] | None = None
    for item in existing_relation_types:
        key = str(item.get("key") or "").strip()
        label = _normalize_text(str(item.get("label") or key))
        aliases = [_normalize_text(str(alias)) for alias in item.get("aliases") or []]
        candidates = [value for value in [label, key.replace("_", " "), *aliases] if value]
        score = max((_similarity(normalized_predicate, value) for value in candidates), default=0.0)
        if score >= threshold and (best is None or score > best[0]):
            best = (score, item)

    if best is None:
        return None

    score, item = best
    key = str(item.get("key") or normalize_graph_key(str(item.get("label") or "")))
    label = str(item.get("label") or key.replace("_", " "))
    aliases = [str(alias) for alias in item.get("aliases") or [label]]
    return _relation_payload(
        key=key,
        label=label,
        aliases=aliases,
        raw_predicate=normalized_predicate,
        merge_confidence=round(score, 3),
        merge_strategy="existing_similarity",
    )


def _relation_payload(
    *,
    key: str,
    label: str,
    aliases: list[str],
    raw_predicate: str,
    merge_confidence: float,
    merge_strategy: str,
) -> dict[str, Any]:
    return {
        "key": normalize_graph_key(key) or "related_to",
        "label": _normalize_text(label) or "related to",
        "aliases": sorted({_normalize_text(alias) for alias in aliases if _normalize_text(alias)}),
        "raw_predicate": str(raw_predicate or ""),
        "merge_confidence": float(merge_confidence),
        "merge_strategy": merge_strategy,
    }


def _normalize_text(value: str) -> str:
    lowered = str(value or "").lower().strip()
    cleaned = _NON_WORD_RE.sub(" ", lowered)
    return _SPACE_RE.sub(" ", cleaned).strip()


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left in right or right in left:
        return 0.9
    return SequenceMatcher(None, left, right).ratio()
