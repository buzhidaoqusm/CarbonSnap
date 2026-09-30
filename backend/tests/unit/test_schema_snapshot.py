"""Pins the schema the models describe, so rewriting them cannot drift.

Recorded before the models moved to SQLAlchemy 2.0 typed mappings. It holds
the PostgreSQL DDL for every table and index, plus what DDL cannot show:
Python-side defaults and onupdate hooks, which a rewrite could silently drop.

To re-record after an intentional schema change (which also needs a migration):

    UPDATE_SCHEMA_SNAPSHOT=1 uv run pytest tests/unit/test_schema_snapshot.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import Column, CreateIndex, CreateTable

import app.models  # noqa: F401  registers every table
from app.extensions.db import db

SNAPSHOT = Path(__file__).resolve().parents[1] / "fixtures" / "schema_snapshot.json"


def _describe_default(value: object) -> object:
    if value is None:
        return None
    arg = getattr(value, "arg", value)
    if callable(arg):
        return "<callable>"
    return repr(arg)


def _describe_column(column: Column) -> dict[str, object]:
    return {
        "type": str(column.type.compile(dialect=postgresql.dialect())),
        "nullable": column.nullable,
        "primary_key": column.primary_key,
        "unique": column.unique,
        "index": column.index,
        "default": _describe_default(column.default),
        "onupdate": _describe_default(column.onupdate),
        "server_default": _describe_default(
            getattr(column.server_default, "arg", column.server_default)
        ),
        "foreign_keys": sorted(
            f"{fk.target_fullname} use_alter={fk.use_alter} name={fk.name}"
            for fk in column.foreign_keys
        ),
    }


def _schema() -> dict[str, object]:
    dialect = postgresql.dialect()
    schema: dict[str, object] = {}
    for name, table in sorted(db.metadata.tables.items()):
        schema[name] = {
            "ddl": str(CreateTable(table).compile(dialect=dialect)).strip(),
            "indexes": sorted(
                str(CreateIndex(index).compile(dialect=dialect)) for index in table.indexes
            ),
            "columns": {column.name: _describe_column(column) for column in table.columns},
        }
    return schema


def test_schema_matches_snapshot():
    produced = _schema()
    if os.getenv("UPDATE_SCHEMA_SNAPSHOT"):
        SNAPSHOT.write_text(
            json.dumps(produced, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip("snapshot re-recorded")

    assert SNAPSHOT.exists(), "no snapshot recorded; run with UPDATE_SCHEMA_SNAPSHOT=1"
    recorded = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert sorted(produced) == sorted(recorded), "tables added or removed"
    for name in recorded:
        assert produced[name] == recorded[name], f"table {name} changed"
