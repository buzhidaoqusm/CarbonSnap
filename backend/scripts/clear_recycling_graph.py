"""
Clear all Neo4j GraphRAG nodes and relationships while keeping schema intact.

Usage from the repo root:
  cd backend
  python scripts/clear_recycling_graph.py

This preserves Neo4j constraints and indexes, so
`python scripts/seed_recycling_graph.py` can be run again immediately.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from scripts.seed_recycling_graph import read_neo4j_env

DEFAULT_BATCH_SIZE = 1000


def build_clear_batch_cypher(batch_size: int) -> str:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    return f"""
MATCH (node)
WITH node LIMIT {batch_size}
WITH collect(node) AS nodes
FOREACH (node IN nodes | DETACH DELETE node)
RETURN size(nodes) AS deleted_count
"""


def collect_total_counts(driver: Any) -> dict[str, int]:
    with driver.session() as session:
        node_record = session.run("MATCH (node) RETURN count(node) AS count").single()
        rel_record = session.run("MATCH ()-[rel]->() RETURN count(rel) AS count").single()

    return {
        "nodes": int(node_record["count"] if node_record else 0),
        "relationships": int(rel_record["count"] if rel_record else 0),
    }


def clear_graph(driver: Any, batch_size: int = DEFAULT_BATCH_SIZE) -> int:
    cypher = build_clear_batch_cypher(batch_size)
    deleted_total = 0

    with driver.session() as session:
        while True:
            record = session.run(cypher).single()
            deleted_count = int(record["deleted_count"] if record else 0)
            if deleted_count == 0:
                break
            deleted_total += deleted_count

    return deleted_total


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clear all Neo4j GraphRAG nodes and relationships while keeping schema intact."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of nodes to delete per transaction. Default: {DEFAULT_BATCH_SIZE}.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

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
        before = collect_total_counts(driver)
        deleted_nodes = clear_graph(driver, batch_size=args.batch_size)
        after = collect_total_counts(driver)
    finally:
        driver.close()

    print("Neo4j graph clear complete.")
    print(f"- nodes before: {before['nodes']}")
    print(f"- relationships before: {before['relationships']}")
    print(f"- deleted nodes: {deleted_nodes}")
    print(f"- nodes after: {after['nodes']}")
    print(f"- relationships after: {after['relationships']}")
    print("Schema constraints and indexes were preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
