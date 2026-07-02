from __future__ import annotations

import re

from scripts import seed_recycling_graph


def test_schema_covers_required_graph_labels():
    schema = seed_recycling_graph.load_schema()
    statements = seed_recycling_graph.split_cypher_statements(schema)

    for label in seed_recycling_graph.GRAPH_LABELS:
        assert f":{label}" in schema
        assert any(
            statement.startswith("CREATE CONSTRAINT")
            and re.search(rf"FOR \(\w+:{label}\)", statement)
            for statement in statements
        )

    assert "CREATE FULLTEXT INDEX item_alias_fulltext" in schema
    assert "CREATE FULLTEXT INDEX recycling_rule_fulltext" in schema
    assert "CREATE FULLTEXT INDEX knowledge_chunk_fulltext" in schema


def test_seed_rows_include_initial_recycling_items():
    rows = list(seed_recycling_graph.iter_seed_rows())
    item_names = {row["item_name"] for row in rows}

    assert {
        "battery",
        "plastic bottle",
        "coffee cup",
        "cardboard box",
        "glass jar",
        "electronics",
    }.issubset(item_names)

    for row in rows:
        assert row["aliases"]
        assert row["material_name"]
        assert row["disposal_method"]
        assert row["facility_type"]
        assert row["rules"]
        assert row["risks"]
        assert row["knowledge_chunks"]


def test_split_cypher_statements_ignores_comments_and_empty_lines():
    cypher = """
    // comment
    CREATE CONSTRAINT item_name_unique IF NOT EXISTS
    FOR (item:Item)
    REQUIRE item.name IS UNIQUE;

    CREATE INDEX item_category_index IF NOT EXISTS
    FOR (item:Item)
    ON (item.category);
    """

    statements = seed_recycling_graph.split_cypher_statements(cypher)

    assert len(statements) == 2
    assert statements[0].startswith("CREATE CONSTRAINT item_name_unique")
    assert statements[1].startswith("CREATE INDEX item_category_index")


def test_build_seed_statements_are_parameterized_and_rerunnable():
    row = next(seed_recycling_graph.iter_seed_rows())

    statements = seed_recycling_graph.build_seed_statements(row)

    assert len(statements) == 4
    for cypher, parameters in statements:
        assert "MERGE" in cypher
        assert "$" in cypher
        assert parameters["item_name"] == "battery"


def test_app_settings_expose_neo4j_config(app, monkeypatch):
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USERNAME", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "password")

    from app.config.settings import load_app_settings

    load_app_settings(app)

    assert app.config["NEO4J_URI"] == "bolt://localhost:7687"
    assert app.config["NEO4J_USERNAME"] == "neo4j"
    assert app.config["NEO4J_PASSWORD"] == "password"
