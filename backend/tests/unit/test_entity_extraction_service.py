from __future__ import annotations

from app.services.ai.entity_extraction_service import extract_recycling_entities


def test_extract_recycling_entities_matches_coffee_cup():
    result = extract_recycling_entities("Can I recycle a coffee cup?")

    assert result["items"] == ["coffee cup"]
    assert result["matches"][0]["source"] == "deterministic_synonym"


def test_extract_recycling_entities_matches_battery_plural():
    result = extract_recycling_entities("Where do I drop off batteries?")

    assert result["items"] == ["battery"]


def test_extract_recycling_entities_matches_multiple_items_without_substring_noise():
    result = extract_recycling_entities("I have a glass jar and an old phone.")

    assert result["items"] == ["glass jar", "electronics"]
    assert "battery" not in result["items"]


def test_extract_recycling_entities_returns_empty_lists_for_unknown_text():
    result = extract_recycling_entities("What should I do this weekend?")

    assert result["items"] == []
    assert result["materials"] == []
    assert result["matches"] == []
