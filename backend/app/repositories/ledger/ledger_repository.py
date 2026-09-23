from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.extensions.db import db
from app.models.ai import RecyclingAuditAttempt, RecyclingCase, WasteAnalysisRecord
from app.models.ledger import Transaction
from app.models.user import User


def record_analysis_and_earn(
    *,
    user_id: int,
    waste_type: str,
    co2_saved_kg: float,
    carbon_points: int,
    image_url: str | None,
    raw_ai_response_json: str | None,
) -> tuple[WasteAnalysisRecord, Transaction, User]:
    """Atomically insert analysis record + earn transaction, then update user totals."""
    record = WasteAnalysisRecord(
        user_id=user_id,
        image_url=image_url,
        waste_type=waste_type,
        co2_saved_kg=co2_saved_kg,
        carbon_points=carbon_points,
        raw_ai_response_json=raw_ai_response_json,
    )
    db.session.add(record)
    db.session.flush()  # populate record.id before creating transaction

    txn = Transaction(
        user_id=user_id,
        type="earn",
        points_delta=carbon_points,
        co2_delta_kg=co2_saved_kg,
        source_type="waste_analysis",
        source_id=record.id,
    )
    db.session.add(txn)

    user = db.session.get(User, user_id)
    user.current_points += carbon_points
    user.total_carbon_amount = round(user.total_carbon_amount + co2_saved_kg, 4)

    db.session.commit()
    return record, txn, user


def finalize_approved_recycling_case_and_earn(
    *,
    user_id: int,
    conversation_id: int,
    recycling_case_id: int,
    approved_audit_attempt_id: int,
    image_url: str | None,
    waste_type: str,
    confidence: float,
    estimated_weight_kg: float,
    co2_saved_kg: float,
    carbon_points: int,
    raw_ai_response_json: str | None,
) -> tuple[WasteAnalysisRecord, Transaction, User]:
    """Finalize a recycling case after audit approval and earn points atomically."""
    try:
        user = db.session.get(User, user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found.")

        recycling_case = db.session.get(RecyclingCase, recycling_case_id)
        if recycling_case is None:
            raise ValueError(f"Recycling case {recycling_case_id} not found.")
        if recycling_case.user_id != user_id:
            raise ValueError(
                f"Recycling case {recycling_case_id} does not belong to user {user_id}."
            )
        if recycling_case.conversation_id != conversation_id:
            raise ValueError(
                f"Recycling case {recycling_case_id} does not belong to conversation {conversation_id}."
            )
        if recycling_case.approved_analysis_id is not None:
            raise ValueError(f"Recycling case {recycling_case_id} has already been finalized.")

        approved_attempt = db.session.get(RecyclingAuditAttempt, approved_audit_attempt_id)
        if approved_attempt is None:
            raise ValueError(f"Audit attempt {approved_audit_attempt_id} not found.")
        if approved_attempt.recycling_case_id != recycling_case_id:
            raise ValueError(
                f"Audit attempt {approved_audit_attempt_id} does not belong to recycling case {recycling_case_id}."
            )
        if approved_attempt.user_id != user_id:
            raise ValueError(
                f"Audit attempt {approved_audit_attempt_id} does not belong to user {user_id}."
            )
        if approved_attempt.conversation_id != conversation_id:
            raise ValueError(
                f"Audit attempt {approved_audit_attempt_id} does not belong to conversation {conversation_id}."
            )
        if approved_attempt.audit_result != "passed":
            raise ValueError(f"Audit attempt {approved_audit_attempt_id} is not approved.")

        record = WasteAnalysisRecord(
            user_id=user_id,
            conversation_id=conversation_id,
            recycling_case_id=recycling_case_id,
            approved_audit_attempt_id=approved_audit_attempt_id,
            image_url=image_url,
            waste_type=waste_type,
            confidence=confidence,
            estimated_weight_kg=estimated_weight_kg,
            co2_saved_kg=co2_saved_kg,
            carbon_points=carbon_points,
            raw_ai_response_json=raw_ai_response_json,
        )
        db.session.add(record)
        db.session.flush()

        txn = Transaction(
            user_id=user_id,
            type="earn",
            points_delta=carbon_points,
            co2_delta_kg=co2_saved_kg,
            source_type="waste_analysis",
            source_id=record.id,
        )
        db.session.add(txn)

        user.current_points += carbon_points
        user.total_carbon_amount = round(user.total_carbon_amount + co2_saved_kg, 4)

        recycling_case.approved_analysis_id = record.id
        recycling_case.status = "audit_passed"

        db.session.commit()
        return record, txn, user
    except Exception:
        db.session.rollback()
        raise


def get_waste_records_page(
    user_id: int, page: int, per_page: int
) -> tuple[list[WasteAnalysisRecord], int]:
    """Return (records, total_count) ordered by newest first."""
    total = (
        db.session.scalar(
            select(func.count(WasteAnalysisRecord.id)).where(WasteAnalysisRecord.user_id == user_id)
        )
        or 0
    )
    records = db.session.scalars(
        select(WasteAnalysisRecord)
        .where(WasteAnalysisRecord.user_id == user_id)
        .order_by(WasteAnalysisRecord.created_at.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
    ).all()
    return list(records), total


def get_transactions_page(user_id: int, page: int, per_page: int) -> tuple[list[Transaction], int]:
    """Return (transactions, total_count) ordered by newest first."""
    total = (
        db.session.scalar(select(func.count(Transaction.id)).where(Transaction.user_id == user_id))
        or 0
    )
    txns = db.session.scalars(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
    ).all()
    return list(txns), total


def sum_earned_points(user_id: int) -> int:
    """Return lifetime earned points, ignoring spend transactions."""
    value = db.session.scalar(
        select(func.sum(Transaction.points_delta)).where(
            Transaction.user_id == user_id,
            Transaction.type == "earn",
            Transaction.points_delta > 0,
        )
    )
    return int(value or 0)


def get_weekly_points_gains(window_days: int = 7) -> list[dict]:
    """Return ranked weekly points gains derived from earn transactions."""
    window_start = datetime.now(UTC) - timedelta(days=window_days)
    weekly_gain = func.sum(Transaction.points_delta)
    last_activity_at = func.max(Transaction.created_at)

    rows = db.session.execute(
        select(
            Transaction.user_id.label("user_id"),
            User.avatar_url.label("avatar_url"),
            weekly_gain.label("weekly_points_gain"),
            last_activity_at.label("last_activity_at"),
        )
        .join(User, User.id == Transaction.user_id)
        .where(
            Transaction.type == "earn",
            Transaction.points_delta > 0,
            Transaction.created_at >= window_start,
        )
        .group_by(Transaction.user_id, User.avatar_url)
        .order_by(
            weekly_gain.desc(),
            last_activity_at.desc(),
            Transaction.user_id.asc(),
        )
    ).all()

    return [
        {
            "user_id": row.user_id,
            "avatar_url": row.avatar_url or "",
            "weekly_points_gain": int(row.weekly_points_gain or 0),
            "last_activity_at": row.last_activity_at.isoformat() if row.last_activity_at else "",
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Generic point mutation helpers (used by market / project services)
# Both helpers assume they are called WITHIN an existing db.session context;
# the caller is responsible for commit() so multi-step operations stay atomic.
# ---------------------------------------------------------------------------


class InsufficientPointsError(Exception):
    """Raised when a user does not have enough points for a spend operation."""


def spend_points(
    *,
    user_id: int,
    points: int,
    source_type: str,
    source_id: int | None = None,
) -> Transaction:
    """Deduct *points* from user balance and write a 'spend' transaction.

    Raises InsufficientPointsError if the user's current_points < points.
    Does NOT commit; caller must commit after all related writes.
    """
    user = db.session.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found.")
    if user.current_points < points:
        raise InsufficientPointsError(
            f"User {user_id} has {user.current_points} points but needs {points}."
        )
    user.current_points -= points

    txn = Transaction(
        user_id=user_id,
        type="spend",
        points_delta=points,
        co2_delta_kg=0.0,
        source_type=source_type,
        source_id=source_id,
    )
    db.session.add(txn)
    return txn


def earn_points(
    *,
    user_id: int,
    points: int,
    source_type: str,
    source_id: int | None = None,
) -> Transaction:
    """Add *points* to user balance and write an 'earn' transaction.

    Does NOT commit; caller must commit after all related writes.
    """
    user = db.session.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found.")
    user.current_points += points

    txn = Transaction(
        user_id=user_id,
        type="earn",
        points_delta=points,
        co2_delta_kg=0.0,
        source_type=source_type,
        source_id=source_id,
    )
    db.session.add(txn)
    return txn
