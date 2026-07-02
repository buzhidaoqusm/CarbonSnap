"""
Apply the optional Neo4j GraphRAG schema and seed a small recycling graph.

Local Neo4j quick start:
  docker run --name carbonsnap-neo4j -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password neo4j:5

Usage from the repo root:
  cd backend
  python scripts/seed_recycling_graph.py

The script is safe to rerun because all writes use MERGE.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = BACKEND_ROOT / "app" / "ai" / "graph" / "schema.cypher"
ENV_PATH = BACKEND_ROOT / ".env"

GRAPH_LABELS = (
    "Item",
    "Material",
    "DisposalMethod",
    "Rule",
    "Risk",
    "FacilityType",
    "ForumPost",
    "KnowledgeChunk",
)

GRAPH_SEED_ROWS: list[dict[str, Any]] = [
    {
        "item_name": "battery",
        "aliases": ["battery", "batteries", "lithium battery", "AA battery"],
        "description": "Portable electrochemical cell that may contain metals or corrosive chemicals.",
        "category": "hazardous household waste",
        "material_name": "mixed metals and electrolyte",
        "material_category": "hazardous",
        "disposal_method": "hazardous drop-off",
        "facility_type": "household hazardous waste facility",
        "rules": [
            {
                "id": "rule-battery-dropoff",
                "title": "Use battery drop-off",
                "description": "Do not place loose batteries in mixed recycling bins; use a battery or hazardous waste drop-off point.",
                "locality": "general",
            }
        ],
        "risks": [
            {
                "name": "fire hazard",
                "description": "Damaged lithium batteries can overheat or ignite during collection and sorting.",
                "severity": "high",
            }
        ],
        "knowledge_chunks": [
            {
                "id": "chunk-battery-001",
                "title": "Battery disposal",
                "text": "Tape battery terminals when required and bring batteries to an approved collection point.",
                "source": "CarbonSnap seed knowledge",
            }
        ],
    },
    {
        "item_name": "plastic bottle",
        "aliases": ["plastic bottle", "PET bottle", "water bottle"],
        "description": "Rigid beverage bottle commonly accepted in household recycling when empty.",
        "category": "container",
        "material_name": "PET plastic",
        "material_category": "plastic",
        "disposal_method": "rinse and recycle",
        "facility_type": "curbside recycling",
        "rules": [
            {
                "id": "rule-plastic-bottle-rinse",
                "title": "Rinse plastic bottles",
                "description": "Empty and lightly rinse plastic bottles before placing them in recycling.",
                "locality": "general",
            }
        ],
        "risks": [
            {
                "name": "food contamination",
                "description": "Liquid or food residue can contaminate other recyclables.",
                "severity": "medium",
            }
        ],
        "knowledge_chunks": [
            {
                "id": "chunk-plastic-bottle-001",
                "title": "Plastic bottle recycling",
                "text": "Most clean plastic beverage bottles are recyclable through curbside programs.",
                "source": "CarbonSnap seed knowledge",
            }
        ],
    },
    {
        "item_name": "coffee cup",
        "aliases": ["coffee cup", "takeaway cup", "paper cup"],
        "description": "Disposable drink cup that is often lined with plastic or wax.",
        "category": "food service packaging",
        "material_name": "plastic-lined paper",
        "material_category": "composite",
        "disposal_method": "check local guidance",
        "facility_type": "specialty recycling program",
        "rules": [
            {
                "id": "rule-coffee-cup-local",
                "title": "Check cup lining rules",
                "description": "Many paper coffee cups are not accepted unless a local program handles lined cups.",
                "locality": "general",
            }
        ],
        "risks": [
            {
                "name": "composite material contamination",
                "description": "Plastic lining can make the cup unsuitable for standard paper recycling.",
                "severity": "medium",
            }
        ],
        "knowledge_chunks": [
            {
                "id": "chunk-coffee-cup-001",
                "title": "Coffee cup recycling",
                "text": "Disposable coffee cups often need specialty handling because of their lining.",
                "source": "CarbonSnap seed knowledge",
            }
        ],
    },
    {
        "item_name": "cardboard box",
        "aliases": ["cardboard box", "corrugated cardboard", "shipping box"],
        "description": "Corrugated fiberboard packaging used for shipping and storage.",
        "category": "paper packaging",
        "material_name": "corrugated cardboard",
        "material_category": "paper",
        "disposal_method": "flatten and recycle",
        "facility_type": "curbside recycling",
        "rules": [
            {
                "id": "rule-cardboard-flatten",
                "title": "Flatten clean cardboard",
                "description": "Flatten boxes and keep them dry before recycling.",
                "locality": "general",
            }
        ],
        "risks": [
            {
                "name": "moisture contamination",
                "description": "Wet cardboard loses fiber quality and may be rejected.",
                "severity": "low",
            }
        ],
        "knowledge_chunks": [
            {
                "id": "chunk-cardboard-001",
                "title": "Cardboard recycling",
                "text": "Clean, dry cardboard is widely recyclable when flattened.",
                "source": "CarbonSnap seed knowledge",
            }
        ],
    },
    {
        "item_name": "glass jar",
        "aliases": ["glass jar", "food jar", "sauce jar"],
        "description": "Rigid glass container for food or household products.",
        "category": "container",
        "material_name": "container glass",
        "material_category": "glass",
        "disposal_method": "rinse and recycle",
        "facility_type": "glass recycling bin",
        "rules": [
            {
                "id": "rule-glass-jar-rinse",
                "title": "Rinse glass jars",
                "description": "Remove food residue from glass jars and follow local lid guidance.",
                "locality": "general",
            }
        ],
        "risks": [
            {
                "name": "broken glass hazard",
                "description": "Broken glass can injure handlers and contaminate sorting streams.",
                "severity": "medium",
            }
        ],
        "knowledge_chunks": [
            {
                "id": "chunk-glass-jar-001",
                "title": "Glass jar recycling",
                "text": "Container glass is often recyclable, but acceptance varies by collection program.",
                "source": "CarbonSnap seed knowledge",
            }
        ],
    },
    {
        "item_name": "electronics",
        "aliases": ["electronics", "e-waste", "old phone", "small appliance"],
        "description": "Electronic device containing circuits, metals, plastics, and sometimes batteries.",
        "category": "e-waste",
        "material_name": "mixed electronic components",
        "material_category": "electronics",
        "disposal_method": "e-waste drop-off",
        "facility_type": "electronics recycling center",
        "rules": [
            {
                "id": "rule-electronics-ewaste",
                "title": "Use e-waste collection",
                "description": "Take electronics to an approved e-waste collection site instead of curbside recycling.",
                "locality": "general",
            }
        ],
        "risks": [
            {
                "name": "toxic component risk",
                "description": "Electronics can contain hazardous metals or batteries that need controlled handling.",
                "severity": "high",
            }
        ],
        "knowledge_chunks": [
            {
                "id": "chunk-electronics-001",
                "title": "Electronics recycling",
                "text": "E-waste programs recover useful materials and reduce landfill contamination.",
                "source": "CarbonSnap seed knowledge",
            }
        ],
    },
]

UPSERT_CORE_CYPHER = """
MERGE (item:Item {name: $item_name})
SET item.aliases = $aliases,
    item.description = $description,
    item.category = $category
MERGE (material:Material {name: $material_name})
SET material.category = $material_category
MERGE (method:DisposalMethod {name: $disposal_method})
MERGE (facility:FacilityType {name: $facility_type})
MERGE (item)-[:MADE_OF]->(material)
MERGE (item)-[:DISPOSE_AS]->(method)
MERGE (method)-[:ACCEPTED_AT]->(facility)
"""

UPSERT_RULES_CYPHER = """
MATCH (item:Item {name: $item_name})
UNWIND $rules AS rule_data
MERGE (rule:Rule {id: rule_data.id})
SET rule.title = rule_data.title,
    rule.description = rule_data.description,
    rule.locality = rule_data.locality
MERGE (item)-[:HAS_RULE]->(rule)
"""

UPSERT_RISKS_CYPHER = """
MATCH (item:Item {name: $item_name})
UNWIND $risks AS risk_data
MERGE (risk:Risk {name: risk_data.name})
SET risk.description = risk_data.description,
    risk.severity = risk_data.severity
MERGE (item)-[:HAS_RISK]->(risk)
"""

UPSERT_CHUNKS_CYPHER = """
MATCH (item:Item {name: $item_name})
UNWIND $knowledge_chunks AS chunk_data
MERGE (chunk:KnowledgeChunk {id: chunk_data.id})
SET chunk.title = chunk_data.title,
    chunk.text = chunk_data.text,
    chunk.source = chunk_data.source
MERGE (chunk)-[:DESCRIBES]->(item)
"""


def load_schema(path: Path = SCHEMA_PATH) -> str:
    return path.read_text(encoding="utf-8")


def split_cypher_statements(cypher: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []

    for raw_line in cypher.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        buffer.append(raw_line)
        if line.endswith(";"):
            statement = "\n".join(buffer).strip().rstrip(";").strip()
            if statement:
                statements.append(statement)
            buffer = []

    trailing = "\n".join(buffer).strip()
    if trailing:
        statements.append(trailing)

    return statements


def iter_seed_rows() -> Iterable[dict[str, Any]]:
    for row in GRAPH_SEED_ROWS:
        yield {
            **row,
            "aliases": list(row["aliases"]),
            "rules": [dict(rule) for rule in row["rules"]],
            "risks": [dict(risk) for risk in row["risks"]],
            "knowledge_chunks": [dict(chunk) for chunk in row["knowledge_chunks"]],
        }


def build_seed_statements(row: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [
        (UPSERT_CORE_CYPHER, row),
        (UPSERT_RULES_CYPHER, {"item_name": row["item_name"], "rules": row["rules"]}),
        (UPSERT_RISKS_CYPHER, {"item_name": row["item_name"], "risks": row["risks"]}),
        (
            UPSERT_CHUNKS_CYPHER,
            {"item_name": row["item_name"], "knowledge_chunks": row["knowledge_chunks"]},
        ),
    ]


def apply_schema(driver: Any, schema_path: Path = SCHEMA_PATH) -> int:
    statements = split_cypher_statements(load_schema(schema_path))
    with driver.session() as session:
        for statement in statements:
            session.run(statement)
    return len(statements)


def seed_graph(driver: Any, seed_rows: Iterable[dict[str, Any]] | None = None) -> int:
    rows = list(seed_rows or iter_seed_rows())
    with driver.session() as session:
        for row in rows:
            for cypher, parameters in build_seed_statements(row):
                session.run(cypher, **parameters)
    return len(rows)


def collect_label_counts(driver: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    with driver.session() as session:
        for label in GRAPH_LABELS:
            result = session.run(f"MATCH (node:`{label}`) RETURN count(node) AS count")
            record = result.single()
            counts[label] = int(record["count"] if record else 0)
    return counts


def read_neo4j_env() -> tuple[str, str, str]:
    load_dotenv(dotenv_path=ENV_PATH, override=False)
    uri = os.getenv("NEO4J_URI", "").strip()
    username = os.getenv("NEO4J_USERNAME", "").strip()
    password = os.getenv("NEO4J_PASSWORD", "").strip()

    missing = [
        name
        for name, value in (
            ("NEO4J_URI", uri),
            ("NEO4J_USERNAME", username),
            ("NEO4J_PASSWORD", password),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing Neo4j environment variables: {', '.join(missing)}")
    return uri, username, password


def main() -> int:
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print(
            "Missing dependency: install the Neo4j Python driver with `pip install neo4j`.",
            file=sys.stderr,
        )
        return 2

    try:
        uri, username, password = read_neo4j_env()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        print("Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD in backend/.env.", file=sys.stderr)
        return 2

    driver = GraphDatabase.driver(uri, auth=(username, password))
    try:
        schema_count = apply_schema(driver)
        item_count = seed_graph(driver)
        counts = collect_label_counts(driver)
    finally:
        driver.close()

    print(f"Applied {schema_count} schema statements.")
    print(f"Seeded {item_count} recycling item graphs.")
    for label in GRAPH_LABELS:
        print(f"{label}: {counts.get(label, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
