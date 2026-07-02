from __future__ import annotations

from app.services.ai import forum_graph_extraction_service


def test_extract_forum_graph_payload_normalizes_llm_entities_and_relations(monkeypatch):
    monkeypatch.setattr(
        forum_graph_extraction_service,
        "complete_json_diagnostic",
        lambda **kwargs: {
            "payload": {
                "entities": [{"name": "Plastic Bottle", "type": "item"}],
                "relations": [
                    {
                        "subject": "Plastic Bottle",
                        "predicate": "can be reused as",
                        "object": "Lantern",
                        "claim": "Plastic bottles can be reused as lantern crafts.",
                        "confidence": 0.86,
                    },
                    {
                        "subject": "Bottle",
                        "predicate": "decorates",
                        "object": "",
                        "claim": "Incomplete relation",
                        "confidence": 0.9,
                    },
                ],
            },
            "raw_reply": "{}",
            "error": None,
        },
    )

    result = forum_graph_extraction_service.extract_forum_graph_payload(
        title="Bottle lantern",
        chunk_text="Plastic bottles can be reused as lantern crafts.",
        post_id=12,
        chunk_id="post-12-v1-c0",
        url="/forum/posts/12",
    )

    assert result["fallback_reason"] is None
    assert result["entities"] == [
        {"key": "plastic_bottle", "name": "Plastic Bottle", "entity_type": "item"}
    ]
    assert result["relations"] == [
        {
            "subject": "Plastic Bottle",
            "subject_key": "plastic_bottle",
            "predicate": "can be reused as",
            "object": "Lantern",
            "object_key": "lantern",
            "claim": "Plastic bottles can be reused as lantern crafts.",
            "stance": "supports",
            "confidence": 0.86,
        }
    ]


def test_extract_forum_graph_payload_falls_back_when_provider_returns_invalid_json(monkeypatch):
    monkeypatch.setattr(
        forum_graph_extraction_service,
        "complete_json_diagnostic",
        lambda **kwargs: {
            "payload": None,
            "raw_reply": "not-json",
            "error": "invalid_json:ValueError",
        },
    )

    result = forum_graph_extraction_service.extract_forum_graph_payload(
        title="Bottle lantern",
        chunk_text="Plastic bottles can become lanterns.",
        post_id=12,
        chunk_id="post-12-v1-c0",
        url="/forum/posts/12",
    )

    assert result["fallback_reason"] == "invalid_json:ValueError"
    assert result["entities"]
    assert result["relations"] == []
