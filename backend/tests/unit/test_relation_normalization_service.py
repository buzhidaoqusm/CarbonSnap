from __future__ import annotations

from app.services.ai.relation_normalization_service import normalize_relation_type


def test_relation_aliases_merge_to_same_canonical_relation():
    values = ["拥有", "持有", "has", "contains"]

    keys = {normalize_relation_type(value)["key"] for value in values}

    assert keys == {"has"}


def test_reuse_aliases_merge_to_same_canonical_relation():
    values = ["reuse as", "upcycle into", "改造成"]

    keys = {normalize_relation_type(value)["key"] for value in values}

    assert keys == {"can_be_reused_as"}


def test_unknown_relation_can_merge_with_existing_similar_relation():
    result = normalize_relation_type(
        "repaired with",
        existing_relation_types=[
            {"key": "repair_with", "label": "repair with", "aliases": ["fixed with"]}
        ],
        similarity_threshold=0.7,
    )

    assert result["key"] == "repair_with"
    assert result["merge_strategy"] == "existing_similarity"


def test_low_similarity_relation_creates_new_relation_type():
    result = normalize_relation_type(
        "decorates",
        existing_relation_types=[
            {"key": "repair_with", "label": "repair with", "aliases": ["fixed with"]}
        ],
        similarity_threshold=0.95,
    )

    assert result["key"] == "decorates"
    assert result["merge_strategy"] == "created_from_predicate"
