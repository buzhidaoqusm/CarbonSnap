"""
Reset AI-related example-data tables and import AI seed JSON files from `data/seeds`.

Usage (from repo root, with backend venv available):
  python backend/scripts/seed_ai_example_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from sqlalchemy import text

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND_ROOT))

from app import create_app
from app.extensions.db import db
from app.models.user import User
from scripts import seed_example_data


AI_TABLE_LOAD_ORDER = [
    "user_memory_items",
    "ai_conversations",
    "ai_messages",
    "recycling_cases",
    "recycling_audit_attempts",
    "waste_analysis_records",
    "ai_message_decisions",
    "transactions",
]

AI_USER_REF_TABLES = [
    "user_memory_items",
    "ai_conversations",
    "ai_messages",
    "recycling_cases",
    "recycling_audit_attempts",
    "waste_analysis_records",
    "ai_message_decisions",
    "transactions",
]

AI_RESET_TABLES = [
    "ai_message_decisions",
    "user_memory_items",
    "recycling_audit_attempts",
    "waste_analysis_records",
    "recycling_cases",
    "ai_messages",
    "ai_conversations",
]


def _split_seed_ref(value: str) -> tuple[str, str]:
    try:
        return tuple(str(value).split(".", 1))  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError(
            f"Invalid seed ref '{value}'. Expected format '<table>.<seed_key>'."
        ) from exc


def _collect_user_seed_refs(value: Any, refs: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.endswith("_ref") and isinstance(child, str):
                ref_table, ref_key = _split_seed_ref(child)
                if ref_table == "users":
                    refs.add(ref_key)
                continue
            _collect_user_seed_refs(child, refs)
        return

    if isinstance(value, list):
        for item in value:
            _collect_user_seed_refs(item, refs)


def _collect_referenced_user_seed_keys() -> list[str]:
    refs: set[str] = set()
    for table_name in AI_USER_REF_TABLES:
        for seed_path in seed_example_data._load_seed_files_for_table(table_name):
            raw_record = seed_example_data._load_json_file(seed_path)
            _collect_user_seed_refs(raw_record, refs)
    return sorted(refs)


def _find_existing_user(*, email: str, username: str) -> User | None:
    email_match = db.session.query(User).filter(User.email == email).one_or_none()
    username_match = db.session.query(User).filter(User.username == username).one_or_none()

    if email_match is not None and username_match is not None and email_match.id != username_match.id:
        raise ValueError(
            "Seeded AI user matches two different existing users: "
            f"email={email!r}, username={username!r}."
        )

    return email_match or username_match


def _sync_seed_user(
    *,
    seed_key: str,
    registry: dict[str, dict[str, int]],
) -> str:
    raw_record = seed_example_data._load_json_file(
        seed_example_data.SEEDS_ROOT / "users" / f"{seed_key}.json"
    )
    normalized_seed_key, payload, deferred_ref_fields, deferred_json_fields = (
        seed_example_data._normalize_seed_record(
            table_name="users",
            raw_record=raw_record,
            registry=registry,
        )
    )
    if deferred_ref_fields or deferred_json_fields:
        raise ValueError(f"User seed '{seed_key}' contains unsupported deferred references.")

    existing_user = _find_existing_user(
        email=str(payload["email"]),
        username=str(payload["username"]),
    )
    if existing_user is None:
        row = User(**payload)
        db.session.add(row)
        db.session.flush()
        registry.setdefault("users", {})[normalized_seed_key] = int(row.id)
        return "created"

    for field_name, field_value in payload.items():
        setattr(existing_user, field_name, field_value)
    db.session.flush()
    registry.setdefault("users", {})[normalized_seed_key] = int(existing_user.id)
    return "updated"


def _existing_ai_reset_tables() -> list[str]:
    existing_table_names = set(db.metadata.tables.keys())
    return [table_name for table_name in AI_RESET_TABLES if table_name in existing_table_names]


def _clear_ai_tables() -> dict[str, int]:
    summary = {
        "transactions": 0,
        "tables": 0,
    }
    existing_table_names = set(db.metadata.tables.keys())

    if "recycling_cases" in existing_table_names:
        db.session.execute(
            text("UPDATE recycling_cases SET approved_analysis_id = NULL WHERE approved_analysis_id IS NOT NULL")
        )
    if "waste_analysis_records" in existing_table_names:
        db.session.execute(
            text(
                "UPDATE waste_analysis_records "
                "SET approved_audit_attempt_id = NULL "
                "WHERE approved_audit_attempt_id IS NOT NULL"
            )
        )
    if "ai_messages" in existing_table_names:
        db.session.execute(
            text("UPDATE ai_messages SET related_analysis_id = NULL WHERE related_analysis_id IS NOT NULL")
        )

    if "transactions" in existing_table_names:
        result = db.session.execute(
            text("DELETE FROM transactions WHERE source_type = 'waste_analysis'")
        )
        summary["transactions"] = int(result.rowcount or 0)

    for table_name in _existing_ai_reset_tables():
        db.session.execute(text(f'DELETE FROM "{table_name}"'))
        summary["tables"] += 1

    db.session.commit()
    return summary


def _sync_ai_seed_users(*, registry: dict[str, dict[str, int]]) -> tuple[int, int]:
    created_count = 0
    updated_count = 0
    for seed_key in _collect_referenced_user_seed_keys():
        result = _sync_seed_user(seed_key=seed_key, registry=registry)
        if result == "created":
            created_count += 1
        else:
            updated_count += 1
    db.session.commit()
    return created_count, updated_count


def _recalculate_user_balances() -> int:
    totals_by_user = {
        int(row.user_id): (
            int(row.points_total or 0),
            float(row.co2_total or 0.0),
        )
        for row in db.session.execute(
            text(
                """
                SELECT
                  user_id,
                  COALESCE(SUM(CASE WHEN type = 'earn' THEN points_delta ELSE -points_delta END), 0) AS points_total,
                  COALESCE(SUM(co2_delta_kg), 0) AS co2_total
                FROM transactions
                GROUP BY user_id
                """
            )
        )
    }

    updated_count = 0
    for user in db.session.query(User).all():
        points_total, co2_total = totals_by_user.get(int(user.id), (0, 0.0))
        user.current_points = points_total
        user.total_carbon_amount = co2_total
        updated_count += 1

    db.session.commit()
    return updated_count


def main() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        clear_summary = _clear_ai_tables()
        restored_upload_assets = seed_example_data._restore_seed_upload_assets()

        registry: dict[str, dict[str, int]] = {}
        deferred_updates: list[dict[str, Any]] = []
        inserted_summary: list[tuple[str, int]] = []

        created_users, updated_users = _sync_ai_seed_users(registry=registry)

        for table_name in AI_TABLE_LOAD_ORDER:
            model_class = seed_example_data.TABLE_MODEL_MAP[table_name]
            count = seed_example_data._seed_table(
                table_name=table_name,
                model_class=model_class,
                registry=registry,
                deferred_updates=deferred_updates,
            )
            inserted_summary.append((table_name, count))

        seed_example_data._apply_deferred_updates(
            deferred_updates=deferred_updates,
            registry=registry,
        )
        refreshed_users = _recalculate_user_balances()

        print("AI example data seed complete.")
        print(f"- cleared AI tables: {clear_summary['tables']}")
        print(f"- cleared AI transactions: {clear_summary['transactions']}")
        print(f"- restored upload assets: {restored_upload_assets}")
        print(f"- synced users: {created_users} created, {updated_users} updated")
        print(f"- refreshed user balances: {refreshed_users}")
        for table_name, count in inserted_summary:
            print(f"- {table_name}: {count} rows")


if __name__ == "__main__":
    main()
