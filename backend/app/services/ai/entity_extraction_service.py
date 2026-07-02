from __future__ import annotations

import re
from typing import Any


_TOKEN_BOUNDARY_TEMPLATE = r"(?<![a-z0-9]){term}(?![a-z0-9])"

ITEM_SYNONYMS: dict[str, tuple[str, ...]] = {
    "battery": ("battery", "batteries", "lithium battery", "aa battery", "rechargeable battery"),
    "plastic bottle": ("plastic bottle", "pet bottle", "water bottle", "drink bottle"),
    "coffee cup": ("coffee cup", "takeaway cup", "paper cup", "disposable cup"),
    "cardboard box": ("cardboard box", "corrugated cardboard", "shipping box"),
    "glass jar": ("glass jar", "food jar", "sauce jar", "glass bottle"),
    "electronics": ("electronics", "e-waste", "ewaste", "old phone", "small appliance"),
}

MATERIAL_SYNONYMS: dict[str, tuple[str, ...]] = {
    "plastic": ("plastic", "pet"),
    "paper": ("paper", "cardboard"),
    "glass": ("glass",),
    "electronics": ("electronics", "electronic components"),
    "hazardous": ("hazardous", "lithium", "chemical"),
}


def extract_recycling_entities(message: str) -> dict[str, Any]:
    normalized = _normalize_text(message)
    item_matches = _match_synonyms(normalized, ITEM_SYNONYMS)
    material_matches = _match_synonyms(normalized, MATERIAL_SYNONYMS)

    return {
        "items": [item["canonical"] for item in item_matches],
        "materials": [item["canonical"] for item in material_matches],
        "matches": item_matches + material_matches,
    }


def _match_synonyms(
    normalized_text: str,
    synonyms_by_canonical: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for canonical, synonyms in synonyms_by_canonical.items():
        matched_synonyms = [
            synonym
            for synonym in synonyms
            if _contains_term(normalized_text, _normalize_text(synonym))
        ]
        if not matched_synonyms:
            continue
        matches.append(
            {
                "canonical": canonical,
                "matched": matched_synonyms,
                "confidence": "high",
                "source": "deterministic_synonym",
            }
        )
    return matches


def _contains_term(normalized_text: str, normalized_term: str) -> bool:
    if not normalized_text or not normalized_term:
        return False
    pattern = _TOKEN_BOUNDARY_TEMPLATE.format(term=re.escape(normalized_term))
    return re.search(pattern, normalized_text) is not None


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").lower().strip().split())
