from __future__ import annotations

import re
from typing import Any

PHASE1_TOPIC_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "topic_id": "plastic-recycling",
        "label": "Plastic Recycling",
        "keywords": (
            "plastic",
            "plastic bottle",
            "plastic container",
            "plastic packaging",
            "wrapper",
            "packaging",
            "bag",
        ),
        "recycling_aliases": (
            "plastic",
            "plastic bottle",
            "plastic container",
            "plastic packaging",
            "wrapper",
            "packaging",
            "bag",
        ),
    },
    {
        "topic_id": "battery-recycling",
        "label": "Battery Recycling",
        "keywords": (
            "battery",
            "batteries",
            "power bank",
            "powerbank",
            "aa battery",
            "aaa battery",
            "lithium battery",
            "charger",
        ),
        "recycling_aliases": (
            "battery",
            "batteries",
            "power bank",
            "powerbank",
            "aa battery",
            "aaa battery",
            "lithium battery",
            "charger",
        ),
    },
    {
        "topic_id": "electronics-recycling",
        "label": "Electronics Recycling",
        "keywords": (
            "electronics",
            "e-waste",
            "ewaste",
            "phone",
            "laptop",
            "computer",
            "tablet",
            "cable",
            "headphone",
            "keyboard",
            "mouse",
        ),
        "recycling_aliases": (
            "electronics",
            "e-waste",
            "ewaste",
            "phone",
            "laptop",
            "computer",
            "tablet",
            "cable",
            "headphone",
            "keyboard",
            "mouse",
        ),
    },
    {
        "topic_id": "paper-recycling",
        "label": "Paper Recycling",
        "keywords": (
            "paper",
            "cardboard",
            "carton",
            "newspaper",
            "notebook",
            "book",
        ),
        "recycling_aliases": (
            "paper",
            "cardboard",
            "carton",
            "newspaper",
            "notebook",
            "book",
        ),
    },
    {
        "topic_id": "glass-recycling",
        "label": "Glass Recycling",
        "keywords": (
            "glass",
            "glass bottle",
            "glass jar",
            "jar",
            "vase",
        ),
        "recycling_aliases": (
            "glass",
            "glass bottle",
            "glass jar",
            "jar",
            "vase",
        ),
    },
    {
        "topic_id": "metal-recycling",
        "label": "Metal Recycling",
        "keywords": (
            "metal",
            "aluminum",
            "aluminium",
            "tin",
            "steel",
            "can",
            "foil",
        ),
        "recycling_aliases": (
            "metal",
            "aluminum",
            "aluminium",
            "tin",
            "steel",
            "can",
            "foil",
        ),
    },
    {
        "topic_id": "waste-sorting",
        "label": "Waste Sorting",
        "keywords": (
            "sorting",
            "sort waste",
            "waste sorting",
            "segregate",
            "segregation",
            "mixed waste",
        ),
        "recycling_aliases": (
            "sorting",
            "sort waste",
            "waste sorting",
            "segregate",
            "segregation",
            "mixed waste",
        ),
    },
    {
        "topic_id": "upcycling",
        "label": "Upcycling",
        "keywords": (
            "upcycle",
            "upcycling",
            "repurpose",
            "reuse",
            "diy",
            "craft",
            "handmade",
        ),
        "recycling_aliases": (
            "upcycle",
            "upcycling",
            "repurpose",
            "reuse",
            "diy",
            "craft",
            "handmade",
        ),
    },
    {
        "topic_id": "community-cleanup",
        "label": "Community Cleanup",
        "keywords": (
            "cleanup",
            "clean up",
            "community cleanup",
            "litter",
            "trash pickup",
            "beach cleanup",
        ),
        "recycling_aliases": (
            "cleanup",
            "clean up",
            "community cleanup",
            "litter",
            "trash pickup",
            "beach cleanup",
        ),
    },
    {
        "topic_id": "sustainability-tips",
        "label": "Sustainability Tips",
        "keywords": (
            "sustainability",
            "sustainable",
            "eco tips",
            "green tips",
            "environmental tips",
            "tips",
        ),
        "recycling_aliases": (
            "sustainability",
            "sustainable",
            "eco tips",
            "green tips",
            "environmental tips",
            "tips",
        ),
    },
    {
        "topic_id": "uncategorized",
        "label": "Uncategorized",
        "keywords": (),
        "recycling_aliases": (),
    },
)

PHASE1_TOPIC_IDS = tuple(item["topic_id"] for item in PHASE1_TOPIC_DEFINITIONS)
TOPIC_ID_SET = frozenset(PHASE1_TOPIC_IDS)

_TOPIC_DEFINITION_BY_ID = {item["topic_id"]: item for item in PHASE1_TOPIC_DEFINITIONS}


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", str(text or "").lower())
    return " ".join(cleaned.split())


def _topic_alias_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for definition in PHASE1_TOPIC_DEFINITIONS:
        topic_id = definition["topic_id"]
        aliases = {
            topic_id,
            definition["label"],
            *definition["keywords"],
            *definition["recycling_aliases"],
        }
        for alias in aliases:
            normalized = _normalize_text(alias)
            if normalized:
                lookup[normalized] = topic_id
                lookup[normalized.replace(" ", "-")] = topic_id
    return lookup


_TOPIC_ALIAS_LOOKUP = _topic_alias_lookup()


def normalize_topic_id(value: str) -> str:
    candidate = _normalize_text(value)
    if not candidate:
        return "uncategorized"

    slug_candidate = candidate.replace(" ", "-")
    if slug_candidate in TOPIC_ID_SET:
        return slug_candidate
    if candidate in TOPIC_ID_SET:
        return candidate

    alias_match = _TOPIC_ALIAS_LOOKUP.get(candidate) or _TOPIC_ALIAS_LOOKUP.get(slug_candidate)
    if alias_match:
        return alias_match
    return "uncategorized"


def get_topic_definition(topic_id: str) -> dict[str, Any] | None:
    normalized = normalize_topic_id(topic_id)
    definition = _TOPIC_DEFINITION_BY_ID.get(normalized)
    if definition is None:
        return None
    return definition


def topic_label(topic_id: str) -> str:
    definition = get_topic_definition(topic_id)
    if definition is None:
        return "Uncategorized"
    return definition["label"]


def recall_topic_candidates(text: str) -> list[dict[str, Any]]:
    normalized = _normalize_text(text)
    if not normalized:
        return []

    candidates: list[dict[str, Any]] = []
    for definition in PHASE1_TOPIC_DEFINITIONS:
        topic_id = definition["topic_id"]
        if topic_id == "uncategorized":
            continue

        matched_keywords = tuple(
            keyword for keyword in definition["keywords"] if _normalize_text(keyword) in normalized
        )
        if not matched_keywords:
            continue

        confidence_score = round(min(0.98, 0.55 + (0.1 * len(matched_keywords))), 3)
        candidates.append(
            {
                "topic_id": topic_id,
                "label": definition["label"],
                "confidence_score": confidence_score,
                "matched_keywords": matched_keywords,
                "source": "rule_recall",
            }
        )

    candidates.sort(key=lambda item: (-float(item["confidence_score"]), item["topic_id"]))
    return candidates


def map_recycling_item_to_topics(item_name: str) -> list[dict[str, Any]]:
    normalized = _normalize_text(item_name)
    if not normalized:
        return [{"topic_id": "uncategorized", "confidence_score": 1.0}]

    recycling_rules: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "battery-recycling",
            (
                "power bank",
                "powerbank",
                "battery",
                "batteries",
                "aa battery",
                "aaa battery",
                "lithium battery",
            ),
        ),
        (
            "electronics-recycling",
            (
                "e-waste",
                "ewaste",
                "electronics",
                "phone",
                "laptop",
                "computer",
                "tablet",
                "charger",
                "cable",
                "headphone",
                "keyboard",
                "mouse",
            ),
        ),
        (
            "glass-recycling",
            (
                "glass bottle",
                "glass jar",
                "glass",
                "jar",
                "vase",
            ),
        ),
        (
            "plastic-recycling",
            (
                "plastic bottle",
                "plastic container",
                "plastic packaging",
                "plastic",
                "wrapper",
                "packaging",
                "bag",
            ),
        ),
        (
            "paper-recycling",
            (
                "paper",
                "cardboard",
                "carton",
                "newspaper",
                "notebook",
                "book",
            ),
        ),
        (
            "metal-recycling",
            (
                "metal can",
                "aluminum",
                "aluminium",
                "tin",
                "steel",
                "can",
                "foil",
                "metal",
            ),
        ),
        (
            "waste-sorting",
            (
                "sorting",
                "sort waste",
                "waste sorting",
                "segregate",
                "segregation",
                "mixed waste",
            ),
        ),
        (
            "upcycling",
            (
                "upcycling",
                "upcycle",
                "repurpose",
                "reuse",
                "diy",
                "craft",
                "handmade",
            ),
        ),
        (
            "community-cleanup",
            (
                "community cleanup",
                "cleanup",
                "clean up",
                "litter",
                "trash pickup",
                "beach cleanup",
            ),
        ),
        (
            "sustainability-tips",
            (
                "sustainability",
                "sustainable",
                "eco tips",
                "green tips",
                "environmental tips",
                "tips",
            ),
        ),
    )

    for topic_id, aliases in recycling_rules:
        if any(_normalize_text(alias) in normalized for alias in aliases):
            return [{"topic_id": topic_id, "confidence_score": 1.0}]

    return [{"topic_id": "uncategorized", "confidence_score": 1.0}]
