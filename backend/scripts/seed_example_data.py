"""
Reset fixed example-data tables and import JSON seed files from `data/seeds`.

Usage (from repo root, with backend venv available):
  python backend/scripts/seed_example_data.py
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_ROOT.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from app import create_app
from app.extensions.db import db
from app.models.ai import (
    AIConversation,
    AIMessage,
    AIMessageDecision,
    RecyclingAuditAttempt,
    RecyclingCase,
    WasteAnalysisRecord,
)
from app.models.forum import ForumPost, ForumPostChunk
from app.models.ledger import Transaction
from app.models.market import MarketItem
from app.models.memory import UserMemoryItem
from app.models.project import Project
from app.models.recommendation import ContentTopicAssignment
from app.models.user import User

SEEDS_ROOT = _REPO_ROOT / "data" / "seeds"
SEED_UPLOAD_ASSETS_ROOT = SEEDS_ROOT / "assets"
UPLOADS_ROOT = _REPO_ROOT / "data" / "uploads"
SEED_FAISS_ASSETS_ROOT = SEEDS_ROOT / "assets" / "faiss"
FAISS_ROOT = _REPO_ROOT / "data" / "faiss"
_SEED_REF_PLACEHOLDER = "__seed_ref__:"

TABLE_LOAD_ORDER = [
    "users",
    "forum_posts",
    "forum_post_chunks",
    "market_items",
    "projects",
    "content_topic_assignments",
    "user_memory_items",
    "ai_conversations",
    "ai_messages",
    "recycling_cases",
    "recycling_audit_attempts",
    "waste_analysis_records",
    "ai_message_decisions",
    "transactions",
]

TABLE_MODEL_MAP = {
    "users": User,
    "forum_posts": ForumPost,
    "forum_post_chunks": ForumPostChunk,
    "market_items": MarketItem,
    "projects": Project,
    "content_topic_assignments": ContentTopicAssignment,
    "user_memory_items": UserMemoryItem,
    "ai_conversations": AIConversation,
    "ai_messages": AIMessage,
    "recycling_cases": RecyclingCase,
    "recycling_audit_attempts": RecyclingAuditAttempt,
    "waste_analysis_records": WasteAnalysisRecord,
    "ai_message_decisions": AIMessageDecision,
    "transactions": Transaction,
}

# Fixed reset set for example-data initialization.
# Ordered from dependent tables to parent tables.
FIXED_RESET_TABLES = [
    "ai_message_decisions",
    "ai_messages",
    "recycling_audit_attempts",
    "recycling_cases",
    "waste_analysis_records",
    "ai_conversations",
    "user_memory_items",
    "notifications",
    "transactions",
    "project_contributions",
    "projects",
    "likes",
    "forum_comments",
    "forum_post_chunks",
    "forum_posts",
    "orders",
    "market_items",
    "user_behavior_events",
    "user_preference_profiles",
    "content_topic_assignments",
    "users",
]


def _is_sqlite() -> bool:
    return db.engine.dialect.name == "sqlite"


def _existing_reset_tables() -> list[str]:
    existing_table_names = set(db.metadata.tables.keys())
    return [table_name for table_name in FIXED_RESET_TABLES if table_name in existing_table_names]


def _clear_fixed_reset_tables() -> list[str]:
    table_names = _existing_reset_tables()

    if _is_sqlite():
        db.session.execute(text("PRAGMA foreign_keys=OFF"))
        db.session.commit()

    try:
        for table_name in table_names:
            db.session.execute(text(f'DELETE FROM "{table_name}"'))
        if _is_sqlite():
            try:
                db.session.execute(text("DELETE FROM sqlite_sequence"))
            except Exception:
                # sqlite_sequence may not exist in some local setups.
                pass
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    finally:
        if _is_sqlite():
            db.session.execute(text("PRAGMA foreign_keys=ON"))
            db.session.commit()

    return table_names


def _load_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _coerce_seed_value(field_name: str, value: Any) -> Any:
    if value is None:
        return None
    if field_name.endswith("_at") and isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed
        return parsed.astimezone(UTC)
    if field_name.endswith("_json") and isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _resolve_ref(value: str, registry: dict[str, dict[str, int]]) -> int:
    try:
        ref_table, ref_key = str(value).split(".", 1)
    except ValueError as exc:
        raise ValueError(
            f"Invalid seed ref '{value}'. Expected format '<table>.<seed_key>'."
        ) from exc

    resolved_id = registry.get(ref_table, {}).get(ref_key)
    if resolved_id is None:
        raise ValueError(f"Unresolved seed ref '{value}'.")
    return int(resolved_id)


def _try_resolve_ref(value: str, registry: dict[str, dict[str, int]]) -> int | None:
    try:
        return _resolve_ref(value, registry)
    except ValueError:
        return None


def _replace_json_seed_refs(
    value: Any,
    registry: dict[str, dict[str, int]],
) -> tuple[Any, bool]:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        has_placeholders = False
        for key, child in value.items():
            if key.endswith("_ref") and isinstance(child, str):
                resolved_id = _try_resolve_ref(child, registry)
                normalized_key = f"{key[:-4]}_id"
                if resolved_id is None:
                    normalized[normalized_key] = f"{_SEED_REF_PLACEHOLDER}{child}"
                    has_placeholders = True
                else:
                    normalized[normalized_key] = resolved_id
                continue

            resolved_child, child_has_placeholders = _replace_json_seed_refs(child, registry)
            normalized[key] = resolved_child
            has_placeholders = has_placeholders or child_has_placeholders
        return normalized, has_placeholders

    if isinstance(value, list):
        normalized_items: list[Any] = []
        has_placeholders = False
        for item in value:
            resolved_item, item_has_placeholders = _replace_json_seed_refs(item, registry)
            normalized_items.append(resolved_item)
            has_placeholders = has_placeholders or item_has_placeholders
        return normalized_items, has_placeholders

    return value, False


def _resolve_json_placeholders(value: Any, registry: dict[str, dict[str, int]]) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_json_placeholders(child, registry) for key, child in value.items()}
    if isinstance(value, list):
        return [_resolve_json_placeholders(item, registry) for item in value]
    if isinstance(value, str) and value.startswith(_SEED_REF_PLACEHOLDER):
        return _resolve_ref(value[len(_SEED_REF_PLACEHOLDER) :], registry)
    return value


def _normalize_seed_record(
    *,
    table_name: str,
    raw_record: dict[str, Any],
    registry: dict[str, dict[str, int]],
) -> tuple[str, dict[str, Any], list[tuple[str, str]], list[str]]:
    seed_key = str(raw_record.get("_seed_key") or "").strip()
    if not seed_key:
        raise ValueError(f"Seed record in table '{table_name}' is missing '_seed_key'.")

    payload: dict[str, Any] = {}
    deferred_ref_fields: list[tuple[str, str]] = []
    deferred_json_fields: list[str] = []
    for key, value in raw_record.items():
        if key.startswith("_"):
            continue
        if key.endswith("_ref"):
            target_field = f"{key[:-4]}_id"
            if value is None:
                payload[target_field] = None
                continue
            resolved_id = _try_resolve_ref(str(value), registry)
            if resolved_id is None:
                payload[target_field] = None
                deferred_ref_fields.append((target_field, str(value)))
            else:
                payload[target_field] = resolved_id
            continue
        if key.endswith("_json") and isinstance(value, (list, dict)):
            normalized_json, has_placeholders = _replace_json_seed_refs(value, registry)
            payload[key] = _coerce_seed_value(key, normalized_json)
            if has_placeholders:
                deferred_json_fields.append(key)
            continue
        payload[key] = _coerce_seed_value(key, value)

    return seed_key, payload, deferred_ref_fields, deferred_json_fields


def _load_seed_files_for_table(table_name: str) -> list[Path]:
    table_dir = SEEDS_ROOT / table_name
    if not table_dir.exists():
        raise FileNotFoundError(f"Seed directory not found: {table_dir}")
    if not (table_dir / "template.json").exists():
        raise FileNotFoundError(f"Missing template.json in seed directory: {table_dir}")
    return sorted(
        path for path in table_dir.glob("*.json") if path.is_file() and path.name != "template.json"
    )


def _restore_seed_upload_assets() -> int:
    if not SEED_UPLOAD_ASSETS_ROOT.exists():
        return 0

    UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    restored_count = 0

    for source_path in SEED_UPLOAD_ASSETS_ROOT.rglob("*"):
        if not source_path.is_file():
            continue
        if source_path.is_relative_to(SEED_FAISS_ASSETS_ROOT):
            continue
        relative_path = source_path.relative_to(SEED_UPLOAD_ASSETS_ROOT)
        target_path = UPLOADS_ROOT / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        restored_count += 1

    return restored_count


def _restore_seed_faiss_assets() -> int:
    FAISS_ROOT.mkdir(parents=True, exist_ok=True)

    for child in FAISS_ROOT.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    restored_count = 0
    if not SEED_FAISS_ASSETS_ROOT.exists():
        gitkeep_path = FAISS_ROOT / ".gitkeep"
        if not gitkeep_path.exists():
            gitkeep_path.write_text("", encoding="utf-8")
        return 0

    for source_path in SEED_FAISS_ASSETS_ROOT.rglob("*"):
        if not source_path.is_file():
            continue
        relative_path = source_path.relative_to(SEED_FAISS_ASSETS_ROOT)
        target_path = FAISS_ROOT / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        restored_count += 1

    return restored_count


def _validate_seeded_forum_rag_assets(*, forum_post_chunk_count: int) -> None:
    if forum_post_chunk_count <= 0:
        return

    manifest_path = FAISS_ROOT / "forum_rag.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            "Seeded forum_post_chunks were imported, but data/seeds/assets/faiss/forum_rag.json is missing. "
            "Export the current forum RAG assets before running seed_example_data.py."
        )


def _seed_table(
    *,
    table_name: str,
    model_class,
    registry: dict[str, dict[str, int]],
    deferred_updates: list[dict[str, Any]],
) -> int:
    inserted_count = 0
    registry.setdefault(table_name, {})

    for seed_path in _load_seed_files_for_table(table_name):
        raw_record = _load_json_file(seed_path)
        seed_key, payload, deferred_ref_fields, deferred_json_fields = _normalize_seed_record(
            table_name=table_name,
            raw_record=raw_record,
            registry=registry,
        )
        row = model_class(**payload)
        db.session.add(row)
        db.session.flush()
        if getattr(row, "id", None) is None:
            raise ValueError(
                f"Seed insert for table '{table_name}' did not produce a primary key: {seed_path.name}"
            )
        registry[table_name][seed_key] = int(row.id)
        for field_name, ref_value in deferred_ref_fields:
            deferred_updates.append(
                {
                    "kind": "column_ref",
                    "model_class": model_class,
                    "row_id": int(row.id),
                    "field_name": field_name,
                    "ref_value": ref_value,
                }
            )
        for field_name in deferred_json_fields:
            deferred_updates.append(
                {
                    "kind": "json_ref",
                    "model_class": model_class,
                    "row_id": int(row.id),
                    "field_name": field_name,
                }
            )
        inserted_count += 1

    db.session.commit()
    return inserted_count


def _apply_deferred_updates(
    *,
    deferred_updates: list[dict[str, Any]],
    registry: dict[str, dict[str, int]],
) -> None:
    if not deferred_updates:
        return

    for update in deferred_updates:
        row = db.session.get(update["model_class"], update["row_id"])
        if row is None:
            raise ValueError(
                f"Deferred seed update target not found: {update['model_class'].__name__}#{update['row_id']}"
            )

        if update["kind"] == "column_ref":
            setattr(row, update["field_name"], _resolve_ref(update["ref_value"], registry))
            continue

        if update["kind"] == "json_ref":
            raw_value = getattr(row, update["field_name"])
            parsed_value = (
                json.loads(raw_value) if isinstance(raw_value, str) and raw_value else raw_value
            )
            resolved_value = _resolve_json_placeholders(parsed_value, registry)
            setattr(row, update["field_name"], json.dumps(resolved_value, ensure_ascii=False))
            continue

        raise ValueError(f"Unknown deferred seed update kind: {update['kind']}")

    db.session.commit()


def main() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        cleared_tables = _clear_fixed_reset_tables()
        restored_upload_assets = _restore_seed_upload_assets()
        restored_faiss_assets = _restore_seed_faiss_assets()

        registry: dict[str, dict[str, int]] = {}
        inserted_summary: list[tuple[str, int]] = []
        inserted_counts: dict[str, int] = {}
        deferred_updates: list[dict[str, Any]] = []

        for table_name in TABLE_LOAD_ORDER:
            model_class = TABLE_MODEL_MAP[table_name]
            count = _seed_table(
                table_name=table_name,
                model_class=model_class,
                registry=registry,
                deferred_updates=deferred_updates,
            )
            inserted_summary.append((table_name, count))
            inserted_counts[table_name] = count

        _apply_deferred_updates(deferred_updates=deferred_updates, registry=registry)
        _validate_seeded_forum_rag_assets(
            forum_post_chunk_count=inserted_counts.get("forum_post_chunks", 0),
        )

        print("Example data seed complete.")
        print(f"- cleared tables: {len(cleared_tables)}")
        print(f"- restored upload assets: {restored_upload_assets}")
        print(f"- restored faiss assets: {restored_faiss_assets}")
        for table_name, count in inserted_summary:
            print(f"- {table_name}: {count} rows")


if __name__ == "__main__":
    main()
