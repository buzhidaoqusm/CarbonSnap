"""
Reset selected AI workflow tables and import only the plastic-bottle-real-chat 1-5 flow.

Usage (from repo root, with backend venv available):
  python backend/scripts/seed_plastic_bottle_real_chat_1_5.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
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
from app.models.memory import UserMemoryItem
from app.models.user import User


SEEDS_ROOT = _REPO_ROOT / "data" / "seeds"
_SEED_REF_PLACEHOLDER = "__seed_ref__:"

TARGET_RESET_TABLES = [
    "ai_message_decisions",
    "ai_messages",
    "recycling_audit_attempts",
    "recycling_cases",
    "waste_analysis_records",
    "ai_conversations",
    "user_memory_items",
]

TARGET_SEED_KEYS_BY_TABLE = {
    "ai_conversations": ["plastic-bottle-real-chat"],
    "ai_messages": [
        "plastic-bottle-real-chat-message-01",
        "plastic-bottle-real-chat-message-02",
        "plastic-bottle-real-chat-message-03",
        "plastic-bottle-real-chat-message-04",
        "plastic-bottle-real-chat-message-05",
    ],
    "recycling_cases": ["plastic-bottle-real-chat-case-01"],
    "recycling_audit_attempts": ["plastic-bottle-real-chat-audit-01"],
    "waste_analysis_records": ["plastic-bottle-real-chat-record-01"],
    "ai_message_decisions": ["plastic-bottle-real-chat-decision-01"],
    "user_memory_items": [],
}

# Order is chosen to satisfy non-null constraints while still allowing deferred refs.
TABLE_LOAD_ORDER = [
    "ai_conversations",
    "ai_messages",
    "recycling_cases",
    "recycling_audit_attempts",
    "waste_analysis_records",
    "ai_message_decisions",
    "user_memory_items",
]

TABLE_MODEL_MAP = {
    "ai_conversations": AIConversation,
    "ai_messages": AIMessage,
    "recycling_cases": RecyclingCase,
    "recycling_audit_attempts": RecyclingAuditAttempt,
    "waste_analysis_records": WasteAnalysisRecord,
    "ai_message_decisions": AIMessageDecision,
    "user_memory_items": UserMemoryItem,
}


def _is_sqlite() -> bool:
    return db.engine.dialect.name == "sqlite"


def _existing_reset_tables() -> list[str]:
    existing_table_names = set(db.metadata.tables.keys())
    return [table_name for table_name in TARGET_RESET_TABLES if table_name in existing_table_names]


def _clear_target_tables() -> list[str]:
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
        return parsed.astimezone(timezone.utc)
    if field_name.endswith("_json") and isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _parse_seed_ref(value: str) -> tuple[str, str]:
    try:
        ref_table, ref_key = str(value).split(".", 1)
    except ValueError as exc:
        raise ValueError(
            f"Invalid seed ref '{value}'. Expected format '<table>.<seed_key>'."
        ) from exc
    return ref_table, ref_key


def _resolve_external_ref(
    *,
    ref_table: str,
    ref_key: str,
    registry: dict[str, dict[str, int]],
) -> int | None:
    if ref_table != "users":
        return None

    cached = registry.setdefault("users", {}).get(ref_key)
    if cached is not None:
        return int(cached)

    user_seed_path = SEEDS_ROOT / "users" / f"{ref_key}.json"
    if not user_seed_path.is_file():
        return None

    user_seed = _load_json_file(user_seed_path)
    username = str(user_seed.get("username") or "").strip()
    email = str(user_seed.get("email") or "").strip()

    user = None
    if username:
        user = db.session.query(User).filter(User.username == username).one_or_none()
    if user is None and email:
        user = db.session.query(User).filter(User.email == email).one_or_none()
    if user is None:
        return None

    registry["users"][ref_key] = int(user.id)
    return int(user.id)


def _resolve_ref(value: str, registry: dict[str, dict[str, int]]) -> int:
    ref_table, ref_key = _parse_seed_ref(value)

    resolved_id = registry.get(ref_table, {}).get(ref_key)
    if resolved_id is None:
        resolved_id = _resolve_external_ref(
            ref_table=ref_table,
            ref_key=ref_key,
            registry=registry,
        )

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
    *,
    target_tables: set[str],
) -> tuple[Any, bool]:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        has_placeholders = False
        for key, child in value.items():
            if key.endswith("_ref") and isinstance(child, str):
                resolved_id = _try_resolve_ref(child, registry)
                normalized_key = f"{key[:-4]}_id"
                if resolved_id is None:
                    ref_table, _ = _parse_seed_ref(child)
                    if ref_table in target_tables:
                        normalized[normalized_key] = f"{_SEED_REF_PLACEHOLDER}{child}"
                        has_placeholders = True
                    else:
                        # Keep unresolved external refs as-is, e.g. transactions.* in content_json.
                        normalized[key] = child
                else:
                    normalized[normalized_key] = resolved_id
                continue

            resolved_child, child_has_placeholders = _replace_json_seed_refs(
                child,
                registry,
                target_tables=target_tables,
            )
            normalized[key] = resolved_child
            has_placeholders = has_placeholders or child_has_placeholders
        return normalized, has_placeholders

    if isinstance(value, list):
        normalized_items: list[Any] = []
        has_placeholders = False
        for item in value:
            resolved_item, item_has_placeholders = _replace_json_seed_refs(
                item,
                registry,
                target_tables=target_tables,
            )
            normalized_items.append(resolved_item)
            has_placeholders = has_placeholders or item_has_placeholders
        return normalized_items, has_placeholders

    return value, False


def _resolve_json_placeholders(value: Any, registry: dict[str, dict[str, int]]) -> Any:
    if isinstance(value, dict):
        return {
            key: _resolve_json_placeholders(child, registry)
            for key, child in value.items()
        }
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
    target_tables: set[str],
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

            ref_value = str(value)
            resolved_id = _try_resolve_ref(ref_value, registry)
            if resolved_id is not None:
                payload[target_field] = resolved_id
                continue

            ref_table, _ = _parse_seed_ref(ref_value)
            if ref_table in target_tables:
                payload[target_field] = None
                deferred_ref_fields.append((target_field, ref_value))
                continue

            raise ValueError(
                f"Cannot resolve external seed ref '{ref_value}' in table '{table_name}'. "
                f"Ensure required base rows already exist before running this script."
            )

        if key.endswith("_json") and isinstance(value, (list, dict)):
            normalized_json, has_placeholders = _replace_json_seed_refs(
                value,
                registry,
                target_tables=target_tables,
            )
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
    return sorted(
        path
        for path in table_dir.glob("*.json")
        if path.is_file() and path.name != "template.json"
    )


def _load_seed_record_for_key(table_name: str, seed_key: str) -> dict[str, Any]:
    for seed_path in _load_seed_files_for_table(table_name):
        raw_record = _load_json_file(seed_path)
        if str(raw_record.get("_seed_key") or "").strip() == seed_key:
            return raw_record
    raise FileNotFoundError(
        f"No seed record found for table '{table_name}' with _seed_key '{seed_key}'."
    )


def _seed_table(
    *,
    table_name: str,
    model_class,
    registry: dict[str, dict[str, int]],
    deferred_updates: list[dict[str, Any]],
    target_tables: set[str],
) -> int:
    registry.setdefault(table_name, {})
    inserted_count = 0

    for seed_key in TARGET_SEED_KEYS_BY_TABLE.get(table_name, []):
        raw_record = _load_seed_record_for_key(table_name, seed_key)
        normalized_seed_key, payload, deferred_ref_fields, deferred_json_fields = _normalize_seed_record(
            table_name=table_name,
            raw_record=raw_record,
            registry=registry,
            target_tables=target_tables,
        )

        row = model_class(**payload)
        db.session.add(row)
        db.session.flush()

        if getattr(row, "id", None) is None:
            raise ValueError(
                f"Seed insert for table '{table_name}' did not produce a primary key: {normalized_seed_key}"
            )

        registry[table_name][normalized_seed_key] = int(row.id)

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
            parsed_value = json.loads(raw_value) if isinstance(raw_value, str) and raw_value else raw_value
            resolved_value = _resolve_json_placeholders(parsed_value, registry)
            setattr(row, update["field_name"], json.dumps(resolved_value, ensure_ascii=False))
            continue

        raise ValueError(f"Unknown deferred seed update kind: {update['kind']}")

    db.session.commit()


def main() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()

        cleared_tables = _clear_target_tables()
        registry: dict[str, dict[str, int]] = {}
        deferred_updates: list[dict[str, Any]] = []
        inserted_summary: list[tuple[str, int]] = []
        target_tables = set(TARGET_SEED_KEYS_BY_TABLE.keys())

        for table_name in TABLE_LOAD_ORDER:
            model_class = TABLE_MODEL_MAP[table_name]
            inserted_count = _seed_table(
                table_name=table_name,
                model_class=model_class,
                registry=registry,
                deferred_updates=deferred_updates,
                target_tables=target_tables,
            )
            inserted_summary.append((table_name, inserted_count))

        _apply_deferred_updates(deferred_updates=deferred_updates, registry=registry)

        print("Plastic bottle real-chat seed complete (messages 1-5).")
        print(f"- cleared tables: {len(cleared_tables)}")
        for table_name, count in inserted_summary:
            print(f"- {table_name}: {count} rows")


if __name__ == "__main__":
    main()
