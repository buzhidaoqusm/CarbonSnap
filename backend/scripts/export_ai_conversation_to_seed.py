"""
Export a persisted AI conversation and its related recycling records as seed JSON.

Usage (from repo root, with backend venv available):
  backend\\.venv\\Scripts\\python.exe backend\\scripts\\export_ai_conversation_to_seed.py ^
    --conversation-id 2 ^
    --conversation-seed-key plastic-bottle-real-chat ^
    --user-seed-key demo-ai-recycler ^
    --sync-user-seed ^
    --replace-existing
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select

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
from app.models.ledger import Transaction
from app.models.user import User

SEEDS_ROOT = _REPO_ROOT / "data" / "seeds"
SEED_ASSETS_ROOT = SEEDS_ROOT / "assets" / "seed-ai"
UPLOADS_ROOT = _REPO_ROOT / "data" / "uploads"
UPLOADS_PREFIX = "/api/uploads/"
AI_SEED_TABLES = [
    "ai_conversations",
    "ai_messages",
    "recycling_cases",
    "recycling_audit_attempts",
    "waste_analysis_records",
    "ai_message_decisions",
    "transactions",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export one AI conversation into seed JSON files.")
    parser.add_argument("--conversation-id", type=int, required=True)
    parser.add_argument("--conversation-seed-key", required=True)
    parser.add_argument("--user-seed-key", required=True)
    parser.add_argument("--sync-user-seed", action="store_true")
    parser.add_argument("--replace-existing", action="store_true")
    return parser.parse_args()


def _jsonable(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _parse_json_text(value: str | None) -> Any:
    if not value:
        return None
    return json.loads(value)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sanitize_audit_result_message_payload(value: Any) -> Any:
    if not isinstance(value, dict):
        return value

    audit_attempt = value.get("audit_attempt")
    if isinstance(audit_attempt, dict):
        audit_attempt.pop("id", None)

    return value


def _relative_upload_path_from_url(url: str) -> Path | None:
    normalized = str(url or "").strip()
    if not normalized.startswith(UPLOADS_PREFIX):
        return None
    return Path(normalized.removeprefix(UPLOADS_PREFIX).replace("/", "\\"))


def _copy_upload_asset(
    *,
    url: str,
    destination_stem: str,
    asset_url_map: dict[str, str],
) -> str:
    normalized = str(url or "").strip()
    if not normalized:
        return normalized
    if normalized in asset_url_map:
        return asset_url_map[normalized]

    relative_upload_path = _relative_upload_path_from_url(normalized)
    if relative_upload_path is None:
        asset_url_map[normalized] = normalized
        return normalized

    source_path = (UPLOADS_ROOT / relative_upload_path).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Uploaded asset not found for export: {source_path}")

    extension = source_path.suffix or ".bin"
    destination_filename = f"{destination_stem}{extension}"
    destination_path = SEED_ASSETS_ROOT / destination_filename
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)

    exported_url = f"{UPLOADS_PREFIX}seed-ai/{destination_filename}".replace("\\", "/")
    asset_url_map[normalized] = exported_url
    return exported_url


def _rewrite_payload(
    value: Any,
    *,
    refs: dict[tuple[str, int], str],
    asset_url_map: dict[str, str],
    asset_stem_prefix: str,
    audit_attempt_asset_urls_by_id: dict[int, str] | None = None,
    audit_attempt_asset_urls_by_key: dict[tuple[int, int], str] | None = None,
) -> Any:
    if isinstance(value, dict):
        rewritten: dict[str, Any] = {}
        for key, child in value.items():
            if key == "recycling_case_id" and isinstance(child, int):
                rewritten["recycling_case_ref"] = refs[("recycling_cases", child)]
                continue
            if key == "analysis_record_id" and isinstance(child, int):
                rewritten["analysis_record_ref"] = refs[("waste_analysis_records", child)]
                continue
            if key == "transaction_id" and isinstance(child, int):
                rewritten["transaction_ref"] = refs[("transactions", child)]
                continue
            if key in {"image_url", "audit_image_url"} and isinstance(child, str):
                if key == "audit_image_url":
                    case_id = value.get("recycling_case_id")
                    attempt_no = value.get("attempt_no")
                    attempt_key = (
                        int(case_id) if isinstance(case_id, int) else None,
                        int(attempt_no) if isinstance(attempt_no, int) else None,
                    )
                    if (
                        attempt_key[0] is not None
                        and attempt_key[1] is not None
                        and audit_attempt_asset_urls_by_key
                        and attempt_key in audit_attempt_asset_urls_by_key
                    ):
                        rewritten[key] = audit_attempt_asset_urls_by_key[attempt_key]
                        continue
                    attempt_id = value.get("id")
                    if (
                        isinstance(attempt_id, int)
                        and audit_attempt_asset_urls_by_id
                        and attempt_id in audit_attempt_asset_urls_by_id
                    ):
                        rewritten[key] = audit_attempt_asset_urls_by_id[attempt_id]
                        continue
                rewritten[key] = _copy_upload_asset(
                    url=child,
                    destination_stem=f"{asset_stem_prefix}-{key}",
                    asset_url_map=asset_url_map,
                )
                continue
            rewritten[key] = _rewrite_payload(
                child,
                refs=refs,
                asset_url_map=asset_url_map,
                asset_stem_prefix=asset_stem_prefix,
                audit_attempt_asset_urls_by_id=audit_attempt_asset_urls_by_id,
                audit_attempt_asset_urls_by_key=audit_attempt_asset_urls_by_key,
            )
        return rewritten

    if isinstance(value, list):
        return [
            _rewrite_payload(
                item,
                refs=refs,
                asset_url_map=asset_url_map,
                asset_stem_prefix=asset_stem_prefix,
                audit_attempt_asset_urls_by_id=audit_attempt_asset_urls_by_id,
                audit_attempt_asset_urls_by_key=audit_attempt_asset_urls_by_key,
            )
            for item in value
        ]

    return _jsonable(value)


def _remove_existing_ai_seed_files() -> None:
    for table_name in AI_SEED_TABLES:
        table_dir = SEEDS_ROOT / table_name
        if not table_dir.exists():
            continue
        for file_path in table_dir.glob("*.json"):
            if file_path.name == "template.json":
                continue
            file_path.unlink()

    if SEED_ASSETS_ROOT.exists():
        shutil.rmtree(SEED_ASSETS_ROOT)


def _export_user_seed(user: User, user_seed_key: str) -> None:
    existing_user_seed = SEEDS_ROOT / "users" / f"{user_seed_key}.json"
    payload = {
        "_seed_key": user_seed_key,
        "_notes": "Password: demo123",
        "username": user.username,
        "email": user.email,
        "password_hash": user.password_hash,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "total_carbon_amount": _jsonable(user.total_carbon_amount),
        "current_points": _jsonable(user.current_points),
        "preferences_json": _parse_json_text(user.preferences_json),
        "created_at": _jsonable(user.created_at),
    }
    _write_json(existing_user_seed, payload)


def main() -> None:
    args = _parse_args()
    app = create_app()

    with app.app_context():
        conversation = db.session.get(AIConversation, args.conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {args.conversation_id} not found.")

        user = db.session.get(User, conversation.user_id)
        if user is None:
            raise ValueError(f"User {conversation.user_id} not found.")

        if args.replace_existing:
            _remove_existing_ai_seed_files()

        messages = list(
            db.session.scalars(
                select(AIMessage)
                .where(AIMessage.conversation_id == conversation.id)
                .order_by(AIMessage.sequence_no.asc(), AIMessage.id.asc())
            )
        )
        cases = list(
            db.session.scalars(
                select(RecyclingCase)
                .where(RecyclingCase.conversation_id == conversation.id)
                .order_by(RecyclingCase.id.asc())
            )
        )
        audits = list(
            db.session.scalars(
                select(RecyclingAuditAttempt)
                .where(RecyclingAuditAttempt.conversation_id == conversation.id)
                .order_by(RecyclingAuditAttempt.id.asc())
            )
        )
        records = list(
            db.session.scalars(
                select(WasteAnalysisRecord)
                .where(WasteAnalysisRecord.conversation_id == conversation.id)
                .order_by(WasteAnalysisRecord.id.asc())
            )
        )
        decisions = list(
            db.session.scalars(
                select(AIMessageDecision)
                .where(AIMessageDecision.conversation_id == conversation.id)
                .order_by(AIMessageDecision.id.asc())
            )
        )
        record_ids = [record.id for record in records]
        transactions = (
            list(
                db.session.scalars(
                    select(Transaction)
                    .where(
                        Transaction.source_type == "waste_analysis",
                        Transaction.source_id.in_(record_ids),
                    )
                    .order_by(Transaction.id.asc())
                )
            )
            if record_ids
            else []
        )

        refs: dict[tuple[str, int], str] = {}
        refs[("ai_conversations", conversation.id)] = (
            f"ai_conversations.{args.conversation_seed_key}"
        )
        for message in messages:
            refs[("ai_messages", message.id)] = (
                f"ai_messages.{args.conversation_seed_key}-message-{message.sequence_no:02d}"
            )
        for index, case in enumerate(cases, start=1):
            refs[("recycling_cases", case.id)] = (
                f"recycling_cases.{args.conversation_seed_key}-case-{index:02d}"
            )
        for index, audit in enumerate(audits, start=1):
            refs[("recycling_audit_attempts", audit.id)] = (
                f"recycling_audit_attempts.{args.conversation_seed_key}-audit-{index:02d}"
            )
        for index, record in enumerate(records, start=1):
            refs[("waste_analysis_records", record.id)] = (
                f"waste_analysis_records.{args.conversation_seed_key}-record-{index:02d}"
            )
        for index, decision in enumerate(decisions, start=1):
            refs[("ai_message_decisions", decision.id)] = (
                f"ai_message_decisions.{args.conversation_seed_key}-decision-{index:02d}"
            )
        for transaction in transactions:
            refs[("transactions", transaction.id)] = (
                f"transactions.{args.conversation_seed_key}-transaction-{index:02d}"
            )

        asset_url_map: dict[str, str] = {}
        audit_attempt_asset_urls_by_id: dict[int, str] = {}
        audit_attempt_asset_urls_by_key: dict[tuple[int, int], str] = {}

        for index, audit in enumerate(audits, start=1):
            exported_audit_image_url = _copy_upload_asset(
                url=audit.audit_image_url,
                destination_stem=f"{args.conversation_seed_key}-audit-{index:02d}-image",
                asset_url_map=asset_url_map,
            )
            audit_attempt_asset_urls_by_id[int(audit.id)] = exported_audit_image_url
            audit_attempt_asset_urls_by_key[
                (int(audit.recycling_case_id), int(audit.attempt_no))
            ] = exported_audit_image_url

        conversation_payload = {
            "_seed_key": args.conversation_seed_key,
            "user_ref": f"users.{args.user_seed_key}",
            "title": conversation.title,
            "status": conversation.status,
            "current_pending_action": conversation.current_pending_action,
            "session_context_json": _rewrite_payload(
                _parse_json_text(conversation.session_context_json),
                refs=refs,
                asset_url_map=asset_url_map,
                asset_stem_prefix=args.conversation_seed_key,
                audit_attempt_asset_urls_by_id=audit_attempt_asset_urls_by_id,
                audit_attempt_asset_urls_by_key=audit_attempt_asset_urls_by_key,
            ),
            "last_message_at": _jsonable(conversation.last_message_at),
            "created_at": _jsonable(conversation.created_at),
            "updated_at": _jsonable(conversation.updated_at),
        }
        _write_json(
            SEEDS_ROOT / "ai_conversations" / f"{args.conversation_seed_key}.json",
            conversation_payload,
        )

        for message in messages:
            message_seed_key = refs[("ai_messages", message.id)].split(".", 1)[1]
            content_json = _rewrite_payload(
                _parse_json_text(message.content_json),
                refs=refs,
                asset_url_map=asset_url_map,
                asset_stem_prefix=f"{args.conversation_seed_key}-message-{message.sequence_no:02d}",
                audit_attempt_asset_urls_by_id=audit_attempt_asset_urls_by_id,
                audit_attempt_asset_urls_by_key=audit_attempt_asset_urls_by_key,
            )
            if message.message_type == "audit_result":
                content_json = _sanitize_audit_result_message_payload(content_json)
            payload = {
                "_seed_key": message_seed_key,
                "conversation_ref": refs[("ai_conversations", conversation.id)],
                "role": message.role,
                "message_type": message.message_type,
                "content_text": message.content_text,
                "content_json": content_json,
                "related_analysis_ref": (
                    refs[("waste_analysis_records", message.related_analysis_id)]
                    if message.related_analysis_id is not None
                    else None
                ),
                "sequence_no": message.sequence_no,
                "created_at": _jsonable(message.created_at),
            }
            _write_json(SEEDS_ROOT / "ai_messages" / f"{message_seed_key}.json", payload)

        for case in cases:
            case_seed_key = refs[("recycling_cases", case.id)].split(".", 1)[1]
            payload = {
                "_seed_key": case_seed_key,
                "user_ref": f"users.{args.user_seed_key}",
                "conversation_ref": refs[("ai_conversations", conversation.id)],
                "origin_message_ref": refs[("ai_messages", case.origin_message_id)],
                "waste_type_predicted": case.waste_type_predicted,
                "confidence": _jsonable(case.confidence),
                "estimated_weight_kg": _jsonable(case.estimated_weight_kg),
                "expected_co2_saved_kg": _jsonable(case.expected_co2_saved_kg),
                "expected_carbon_points": _jsonable(case.expected_carbon_points),
                "status": case.status,
                "latest_audit_attempt_no": case.latest_audit_attempt_no,
                "approved_analysis_ref": (
                    refs[("waste_analysis_records", case.approved_analysis_id)]
                    if case.approved_analysis_id is not None
                    else None
                ),
                "created_at": _jsonable(case.created_at),
                "updated_at": _jsonable(case.updated_at),
            }
            _write_json(SEEDS_ROOT / "recycling_cases" / f"{case_seed_key}.json", payload)

        for index, audit in enumerate(audits, start=1):
            audit_seed_key = refs[("recycling_audit_attempts", audit.id)].split(".", 1)[1]
            payload = {
                "_seed_key": audit_seed_key,
                "recycling_case_ref": refs[("recycling_cases", audit.recycling_case_id)],
                "user_ref": f"users.{args.user_seed_key}",
                "conversation_ref": refs[("ai_conversations", conversation.id)],
                "audit_image_url": audit_attempt_asset_urls_by_id[int(audit.id)],
                "attempt_no": audit.attempt_no,
                "audit_result": audit.audit_result,
                "auditor_confidence": _jsonable(audit.auditor_confidence),
                "audit_reason": audit.audit_reason,
                "audit_response_json": _rewrite_payload(
                    _parse_json_text(audit.audit_response_json),
                    refs=refs,
                    asset_url_map=asset_url_map,
                    asset_stem_prefix=f"{args.conversation_seed_key}-audit-{index:02d}",
                    audit_attempt_asset_urls_by_id=audit_attempt_asset_urls_by_id,
                    audit_attempt_asset_urls_by_key=audit_attempt_asset_urls_by_key,
                ),
                "created_at": _jsonable(audit.created_at),
            }
            _write_json(
                SEEDS_ROOT / "recycling_audit_attempts" / f"{audit_seed_key}.json",
                payload,
            )

        for index, record in enumerate(records, start=1):
            record_seed_key = refs[("waste_analysis_records", record.id)].split(".", 1)[1]
            payload = {
                "_seed_key": record_seed_key,
                "user_ref": f"users.{args.user_seed_key}",
                "conversation_ref": refs[("ai_conversations", conversation.id)],
                "recycling_case_ref": refs[("recycling_cases", record.recycling_case_id)],
                "approved_audit_attempt_ref": refs[
                    ("recycling_audit_attempts", record.approved_audit_attempt_id)
                ],
                "image_url": _copy_upload_asset(
                    url=record.image_url,
                    destination_stem=f"{args.conversation_seed_key}-record-{index:02d}-image",
                    asset_url_map=asset_url_map,
                ),
                "waste_type": record.waste_type,
                "confidence": _jsonable(record.confidence),
                "estimated_weight_kg": _jsonable(record.estimated_weight_kg),
                "co2_saved_kg": _jsonable(record.co2_saved_kg),
                "carbon_points": record.carbon_points,
                "raw_ai_response_json": _rewrite_payload(
                    _parse_json_text(record.raw_ai_response_json),
                    refs=refs,
                    asset_url_map=asset_url_map,
                    asset_stem_prefix=f"{args.conversation_seed_key}-record-{index:02d}",
                    audit_attempt_asset_urls_by_id=audit_attempt_asset_urls_by_id,
                    audit_attempt_asset_urls_by_key=audit_attempt_asset_urls_by_key,
                ),
                "created_at": _jsonable(record.created_at),
            }
            _write_json(
                SEEDS_ROOT / "waste_analysis_records" / f"{record_seed_key}.json",
                payload,
            )

        for index, decision in enumerate(decisions, start=1):
            decision_seed_key = refs[("ai_message_decisions", decision.id)].split(".", 1)[1]
            payload = {
                "_seed_key": decision_seed_key,
                "conversation_ref": refs[("ai_conversations", conversation.id)],
                "user_message_ref": refs[("ai_messages", decision.user_message_id)],
                "intent": decision.intent,
                "follow_up_type": decision.follow_up_type,
                "target_case_ref": (
                    refs[("recycling_cases", decision.target_case_id)]
                    if decision.target_case_id is not None
                    else None
                ),
                "confidence": _jsonable(decision.confidence),
                "needs_clarification": bool(decision.needs_clarification),
                "decision_json": _rewrite_payload(
                    _parse_json_text(decision.decision_json),
                    refs=refs,
                    asset_url_map=asset_url_map,
                    asset_stem_prefix=f"{args.conversation_seed_key}-decision-{index:02d}",
                    audit_attempt_asset_urls_by_id=audit_attempt_asset_urls_by_id,
                    audit_attempt_asset_urls_by_key=audit_attempt_asset_urls_by_key,
                ),
                "engine_version": decision.engine_version,
                "created_at": _jsonable(decision.created_at),
            }
            _write_json(
                SEEDS_ROOT / "ai_message_decisions" / f"{decision_seed_key}.json",
                payload,
            )

        for transaction in transactions:
            transaction_seed_key = refs[("transactions", transaction.id)].split(".", 1)[1]
            payload = {
                "_seed_key": transaction_seed_key,
                "user_ref": f"users.{args.user_seed_key}",
                "type": transaction.type,
                "points_delta": transaction.points_delta,
                "co2_delta_kg": _jsonable(transaction.co2_delta_kg),
                "source_type": transaction.source_type,
                "source_ref": refs[("waste_analysis_records", transaction.source_id)],
                "created_at": _jsonable(transaction.created_at),
            }
            _write_json(SEEDS_ROOT / "transactions" / f"{transaction_seed_key}.json", payload)

        if args.sync_user_seed:
            _export_user_seed(user, args.user_seed_key)

        print("AI conversation seed export complete.")
        print(f"- conversation_id: {conversation.id}")
        print(f"- conversation_seed_key: {args.conversation_seed_key}")
        print(f"- messages: {len(messages)}")
        print(f"- recycling_cases: {len(cases)}")
        print(f"- recycling_audit_attempts: {len(audits)}")
        print(f"- waste_analysis_records: {len(records)}")
        print(f"- ai_message_decisions: {len(decisions)}")
        print(f"- transactions: {len(transactions)}")
        print(f"- copied_assets: {len(asset_url_map)}")


if __name__ == "__main__":
    main()
