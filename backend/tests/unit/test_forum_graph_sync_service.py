from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.services.ai import forum_graph_sync_service


@dataclass
class FakeChunk:
    id: int
    post_id: int
    chunk_text: str
    chunk_index: int
    chunk_version: int
    embedding_id: str


class FakeSession:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def run(self, query, **parameters):
        self.calls.append((query, parameters))
        if "MATCH (relation:RelationType)" in query:
            return []
        return []


class FakeDriver:
    def __init__(self):
        self.session_obj = FakeSession()

    def session(self):
        return self.session_obj


def test_sync_forum_post_graph_upserts_entities_relation_fact_and_evidence(monkeypatch):
    driver = FakeDriver()
    monkeypatch.setattr(
        forum_graph_sync_service.forum_graph_extraction_service,
        "extract_forum_graph_payload",
        lambda **kwargs: {
            "entities": [
                {"key": "plastic_bottle", "name": "plastic bottle", "entity_type": "item"}
            ],
            "relations": [
                {
                    "subject": "plastic bottle",
                    "subject_key": "plastic_bottle",
                    "predicate": "upcycle into",
                    "object": "lantern",
                    "object_key": "lantern",
                    "claim": "Plastic bottles can be upcycled into lanterns.",
                    "stance": "supports",
                    "confidence": 0.88,
                }
            ],
            "fallback_reason": None,
        },
    )

    result = forum_graph_sync_service.sync_forum_post_graph(
        post_id=12,
        title="Bottle lantern ideas",
        content="Plastic bottles can be upcycled into lanterns.",
        author_id=7,
        created_at=datetime(2026, 5, 12, tzinfo=UTC),
        chunks=[
            FakeChunk(
                id=1,
                post_id=12,
                chunk_text="Plastic bottles can be upcycled into lanterns.",
                chunk_index=0,
                chunk_version=1,
                embedding_id="post-12-v1-c0",
            )
        ],
        driver=driver,
    )

    relation_calls = [
        params for query, params in driver.session_obj.calls if "MERGE (fact:RelationFact" in query
    ]
    assert result["synced"] is True
    assert result["relation_fact_count"] == 1
    assert relation_calls[0]["relation_key"] == "can_be_reused_as"
    assert relation_calls[0]["raw_predicate"] == "upcycle into"
    assert relation_calls[0]["evidence_id"].startswith("evidence-")


def test_sync_forum_post_graph_aggregates_same_fact_with_distinct_evidence(monkeypatch):
    driver = FakeDriver()
    monkeypatch.setattr(
        forum_graph_sync_service.forum_graph_extraction_service,
        "extract_forum_graph_payload",
        lambda **kwargs: {
            "entities": [],
            "relations": [
                {
                    "subject": "plastic bottle",
                    "subject_key": "plastic_bottle",
                    "predicate": "reuse as",
                    "object": "lantern",
                    "object_key": "lantern",
                    "claim": "Plastic bottles can become lanterns.",
                    "stance": "supports",
                    "confidence": 0.8,
                }
            ],
            "fallback_reason": None,
        },
    )

    result = forum_graph_sync_service.sync_forum_post_graph(
        post_id=12,
        title="Bottle lantern ideas",
        content="Plastic bottles can become lanterns.",
        author_id=7,
        created_at=None,
        chunks=[
            FakeChunk(1, 12, "Chunk one", 0, 1, "post-12-v1-c0"),
            FakeChunk(2, 12, "Chunk two", 1, 1, "post-12-v1-c1"),
        ],
        driver=driver,
    )

    relation_calls = [
        params for query, params in driver.session_obj.calls if "MERGE (fact:RelationFact" in query
    ]
    assert result["relation_fact_count"] == 2
    assert relation_calls[0]["fact_id"] == relation_calls[1]["fact_id"]
    assert relation_calls[0]["evidence_id"] != relation_calls[1]["evidence_id"]


def test_sync_forum_post_graph_reuses_fixed_made_of_relationship(monkeypatch):
    driver = FakeDriver()
    monkeypatch.setattr(
        forum_graph_sync_service.forum_graph_extraction_service,
        "extract_forum_graph_payload",
        lambda **kwargs: {
            "entities": [],
            "relations": [
                {
                    "subject": "coffee cup",
                    "subject_key": "coffee_cup",
                    "predicate": "composed of",
                    "object": "plastic-lined paper",
                    "object_key": "plastic_lined_paper",
                    "claim": "Coffee cups are composed of plastic-lined paper.",
                    "stance": "supports",
                    "confidence": 0.86,
                }
            ],
            "fallback_reason": None,
        },
    )

    forum_graph_sync_service.sync_forum_post_graph(
        post_id=22,
        title="Coffee cup material",
        content="Coffee cups are composed of plastic-lined paper.",
        author_id=7,
        created_at=None,
        chunks=[
            FakeChunk(
                1, 22, "Coffee cups are composed of plastic-lined paper.", 0, 1, "post-22-v1-c0"
            )
        ],
        driver=driver,
    )

    assert any(
        "MERGE (item)-[:MADE_OF]->(material)" in query
        for query, _params in driver.session_obj.calls
    )


def test_remove_forum_post_graph_marks_evidence_inactive():
    driver = FakeDriver()

    result = forum_graph_sync_service.remove_forum_post_graph(post_id=12, driver=driver)

    assert result["removed"] is True
    assert any(
        "SET evidence.active = false" in query for query, _params in driver.session_obj.calls
    )
