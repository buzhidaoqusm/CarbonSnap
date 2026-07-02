from __future__ import annotations

from app.services.ai.neo4j_graph_retrieval_service import (
    build_graph_prompt_block,
    format_graph_paths,
    is_configured,
    query_graph_context,
)


class FakeResult:
    def __init__(self, records):
        self.records = records

    def __iter__(self):
        return iter(self.records)


class FakeSession:
    def __init__(self, records):
        self.records = records
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def run(self, query, **parameters):
        self.queries.append((query, parameters))
        return FakeResult(self.records)


class FakeDriver:
    def __init__(self, records):
        self.session_obj = FakeSession(records)

    def session(self):
        return self.session_obj


class RoutingFakeSession:
    def __init__(self, fixed_records, open_records):
        self.fixed_records = fixed_records
        self.open_records = open_records
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def run(self, query, **parameters):
        self.queries.append((query, parameters))
        if "MATCH (fact:RelationFact)" in query:
            return FakeResult(self.open_records)
        return FakeResult(self.fixed_records)


class RoutingFakeDriver:
    def __init__(self, fixed_records, open_records):
        self.session_obj = RoutingFakeSession(fixed_records, open_records)

    def session(self):
        return self.session_obj


class FailingDriver:
    def session(self):
        raise RuntimeError("connection refused")


def _enable_neo4j(app):
    app.config.update(
        AI_NEO4J_GRAPHRAG_ENABLED=True,
        NEO4J_URI="bolt://localhost:7687",
        NEO4J_USERNAME="neo4j",
        NEO4J_PASSWORD="password",
    )


def test_is_configured_requires_flag_and_credentials(app):
    app.config.update(
        AI_NEO4J_GRAPHRAG_ENABLED=False,
        NEO4J_URI="bolt://localhost:7687",
        NEO4J_USERNAME="neo4j",
        NEO4J_PASSWORD="password",
    )
    assert is_configured() is False

    _enable_neo4j(app)
    assert is_configured() is True


def test_query_graph_context_uses_fake_driver_and_returns_structured_context(app):
    _enable_neo4j(app)
    records = [
        {
            "item_name": "battery",
            "material_name": "mixed metals and electrolyte",
            "disposal_method": "hazardous drop-off",
            "facility_type": "household hazardous waste facility",
            "rules": [
                {
                    "id": "rule-battery-dropoff",
                    "title": "Use battery drop-off",
                    "description": "Do not place loose batteries in mixed recycling bins.",
                    "locality": "general",
                }
            ],
            "risks": [
                {
                    "name": "fire hazard",
                    "description": "Damaged lithium batteries can overheat.",
                    "severity": "high",
                }
            ],
            "knowledge_chunks": [
                {
                    "id": "chunk-battery-001",
                    "title": "Battery disposal",
                    "text": "Use an approved collection point.",
                    "source": "CarbonSnap seed knowledge",
                }
            ],
        }
    ]
    driver = FakeDriver(records)

    result = query_graph_context(
        "Where do I recycle batteries?",
        {"items": ["battery"], "materials": [], "matches": []},
        driver=driver,
    )

    assert result["enabled"] is True
    assert result["entities"]["items"] == ["battery"]
    assert result["confidence"] == "medium"
    assert result["facility_types"] == ["household hazardous waste facility"]
    assert result["rules"][0]["id"] == "rule-battery-dropoff"
    assert result["risks"][0]["name"] == "fire hazard"
    assert result["knowledge_chunks"][0]["id"] == "chunk-battery-001"
    assert {"from": "battery", "relation": "DISPOSE_AS", "to": "hazardous drop-off"} in result["paths"]
    assert driver.session_obj.queries[0][1]["items"] == ["battery"]


def test_query_graph_context_extracts_entities_when_not_supplied(app):
    _enable_neo4j(app)
    driver = FakeDriver(
        [
            {
                "item_name": "coffee cup",
                "material_name": "plastic-lined paper",
                "disposal_method": "check local guidance",
                "facility_type": "specialty recycling program",
                "rules": [],
                "risks": [],
                "knowledge_chunks": [],
            }
        ]
    )

    result = query_graph_context("Can I recycle a takeaway cup?", driver=driver)

    assert result["entities"]["items"] == ["coffee cup"]
    assert {"from": "coffee cup", "relation": "MADE_OF", "to": "plastic-lined paper"} in result["paths"]


def test_query_graph_context_returns_fallback_when_feature_disabled(app):
    app.config.update(AI_NEO4J_GRAPHRAG_ENABLED=False)

    result = query_graph_context(
        "Can I recycle batteries?",
        {"items": ["battery"], "materials": [], "matches": []},
    )

    assert result["enabled"] is False
    assert result["fallback_reason"] == "feature_disabled"
    assert result["paths"] == []


def test_query_graph_context_returns_fallback_when_connection_fails(app):
    _enable_neo4j(app)

    result = query_graph_context(
        "Can I recycle batteries?",
        {"items": ["battery"], "materials": [], "matches": []},
        driver=FailingDriver(),
    )

    assert result["enabled"] is False
    assert result["fallback_reason"] == "neo4j_unavailable"
    assert result["paths"] == []


def test_format_graph_paths_deduplicates_records():
    records = [
        {
            "item_name": "battery",
            "material_name": "mixed metals and electrolyte",
            "disposal_method": "hazardous drop-off",
            "facility_type": "household hazardous waste facility",
            "rules": [{"title": "Use battery drop-off"}],
            "risks": [{"name": "fire hazard"}],
        },
        {
            "item_name": "battery",
            "material_name": "mixed metals and electrolyte",
            "disposal_method": "hazardous drop-off",
            "facility_type": "household hazardous waste facility",
            "rules": [{"title": "Use battery drop-off"}],
            "risks": [{"name": "fire hazard"}],
        },
    ]

    paths = format_graph_paths(records)

    assert paths.count({"from": "battery", "relation": "HAS_RISK", "to": "fire hazard"}) == 1


def test_build_graph_prompt_block_formats_evidence_without_raw_records():
    prompt = build_graph_prompt_block(
        {
            "enabled": True,
            "entities": {"items": ["battery"]},
            "paths": [{"from": "battery", "relation": "HAS_RISK", "to": "fire hazard"}],
            "rules": [
                {
                    "id": "rule-battery-dropoff",
                    "title": "Use battery drop-off",
                    "description": "Use a battery collection point.",
                }
            ],
            "risks": [{"name": "fire hazard", "severity": "high", "description": "May ignite."}],
            "facility_types": ["household hazardous waste facility"],
        }
    )

    assert "Neo4j recycling graph evidence" in prompt
    assert "battery --HAS_RISK--> fire hazard" in prompt
    assert "Use battery drop-off" in prompt
    assert "household hazardous waste facility" in prompt
    assert "{'enabled'" not in prompt


def test_query_graph_context_returns_open_relation_facts_and_forum_citations(app):
    _enable_neo4j(app)
    driver = RoutingFakeDriver(
        fixed_records=[],
        open_records=[
            {
                "fact_id": "fact-1",
                "subject_key": "plastic_bottle",
                "relation_key": "can_be_reused_as",
                "object_key": "lantern",
                "support_count": 2,
                "fact_confidence": 0.88,
                "subject_name": "plastic bottle",
                "object_name": "lantern",
                "relation_label": "can be reused as",
                "relation_aliases": ["reuse as", "upcycle into"],
                "claims": [
                    {
                        "id": "claim-1",
                        "text": "Plastic bottles can be reused as lantern crafts.",
                        "stance": "supports",
                        "confidence": 0.88,
                        "raw_predicate": "upcycle into",
                        "canonical_relation": "can_be_reused_as",
                    }
                ],
                "evidence": [
                    {
                        "id": "evidence-1",
                        "post_id": 12,
                        "chunk_id": "post-12-v1-c0",
                        "title": "Bottle lantern ideas",
                        "url": "/forum/posts/12",
                        "excerpt": "Plastic bottles can be reused as lantern crafts.",
                        "raw_predicate": "upcycle into",
                        "canonical_relation": "can_be_reused_as",
                        "extraction_confidence": 0.88,
                    }
                ],
            }
        ],
    )

    result = query_graph_context(
        "plastic bottle lantern ideas",
        {"items": ["plastic bottle"], "materials": [], "matches": []},
        driver=driver,
    )

    assert result["relation_facts"][0]["relation_key"] == "can_be_reused_as"
    assert result["open_claims"][0]["raw_predicate"] == "upcycle into"
    open_query_parameters = driver.session_obj.queries[-1][1]
    assert "plastic_bottle" in open_query_parameters["terms"]
    assert result["forum_citations"] == [
        {
            "reference_id": "forum-post-12",
            "post_id": 12,
            "title": "Bottle lantern ideas",
            "url": "/forum/posts/12",
            "excerpt": "Plastic bottles can be reused as lantern crafts.",
            "source": "open_graph",
        }
    ]


def test_query_graph_context_expands_chinese_open_graph_alias_terms(app):
    _enable_neo4j(app)
    driver = RoutingFakeDriver(
        fixed_records=[],
        open_records=[
            {
                "fact_id": "fact-cn",
                "subject_key": "plastic_bottle",
                "relation_key": "can_be_reused_as",
                "object_key": "mini_lantern",
                "support_count": 1,
                "fact_confidence": 0.9,
                "subject_name": "plastic bottle",
                "object_name": "mini lantern",
                "relation_label": "can be reused as",
                "relation_aliases": ["reuse as"],
                "claims": [],
                "evidence": [],
            }
        ],
    )

    result = query_graph_context("有没有回收塑料瓶的好方法", driver=driver)

    open_query_parameters = driver.session_obj.queries[-1][1]
    assert "plastic_bottle" in open_query_parameters["terms"]
    assert "bottle" in open_query_parameters["terms"]
    assert result["relation_facts"][0]["subject"] == "plastic bottle"


def test_build_graph_prompt_block_includes_open_claims_and_sources():
    prompt = build_graph_prompt_block(
        {
            "enabled": True,
            "entities": {"items": ["plastic bottle"]},
            "paths": [],
            "rules": [],
            "risks": [],
            "facility_types": [],
            "relation_facts": [
                {
                    "subject": "plastic bottle",
                    "relation": "can be reused as",
                    "object": "lantern",
                    "support_count": 2,
                }
            ],
            "forum_citations": [
                {"title": "Bottle lantern ideas", "url": "/forum/posts/12"}
            ],
        }
    )

    assert "Open claim: plastic bottle --can be reused as--> lantern" in prompt
    assert "[Bottle lantern ideas](/forum/posts/12)" in prompt
