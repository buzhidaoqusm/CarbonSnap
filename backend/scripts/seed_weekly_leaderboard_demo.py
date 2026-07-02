"""
Seed repeatable weekly leaderboard demo data into the development database.

Usage (from repo root):
  backend\.venv\Scripts\python.exe backend\scripts\seed_weekly_leaderboard_demo.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND_ROOT))

from app import create_app
from app.extensions.db import db
from app.models.ledger import Transaction
from app.models.user import User


SOURCE_TYPE = "leaderboard_demo"
DEMO_AVATAR_BASE = "https://api.dicebear.com/9.x/shapes/svg?seed="

DEMO_WEEKLY_GAINS = {
    "demo_ai_recycler": [18, 12, 9],
    "community_guide": [80, 62, 46],
    "repair_lab_notes": [74, 48, 32],
    "demo_seller": [55, 38, 24],
    "diy_corner": [41, 29, 18],
    "home_reset_journal": [36, 24, 16],
    "demo_buyer": [28, 19, 11],
}


def _ensure_avatar(user: User) -> None:
    if user.avatar_url:
        return
    user.avatar_url = f"{DEMO_AVATAR_BASE}{user.username}"


def _rollback_existing_demo_transactions() -> int:
    existing = (
        db.session.query(Transaction)
        .filter(Transaction.source_type == SOURCE_TYPE)
        .all()
    )
    deducted = 0
    for txn in existing:
        user = db.session.get(User, txn.user_id)
        if user is not None and txn.type == "earn":
            user.current_points = max(0, int(user.current_points or 0) - int(txn.points_delta or 0))
        db.session.delete(txn)
        deducted += 1
    return deducted


def _seed_demo_transactions(users_by_username: dict[str, User]) -> int:
    inserted = 0
    now = datetime.now(timezone.utc)

    for username, gains in DEMO_WEEKLY_GAINS.items():
        user = users_by_username.get(username)
        if user is None:
            continue

        _ensure_avatar(user)

        for index, gain in enumerate(gains):
            txn = Transaction(
                user_id=user.id,
                type="earn",
                points_delta=int(gain),
                co2_delta_kg=0.0,
                source_type=SOURCE_TYPE,
                source_id=index + 1,
                created_at=now - timedelta(days=index * 2, hours=index + 1),
            )
            db.session.add(txn)
            user.current_points = int(user.current_points or 0) + int(gain)
            inserted += 1

    return inserted


def main() -> None:
    app = create_app()
    with app.app_context():
        users = db.session.query(User).order_by(User.id.asc()).all()
        users_by_username = {str(user.username): user for user in users}

        removed = _rollback_existing_demo_transactions()
        inserted = _seed_demo_transactions(users_by_username)
        db.session.commit()

        weekly_totals = defaultdict(int)
        for username, gains in DEMO_WEEKLY_GAINS.items():
            if username in users_by_username:
                weekly_totals[username] = sum(int(gain) for gain in gains)

        ranked = sorted(
            weekly_totals.items(),
            key=lambda item: (-item[1], item[0]),
        )

        print("Weekly leaderboard demo seed complete.")
        print(f"- removed previous demo transactions: {removed}")
        print(f"- inserted demo transactions: {inserted}")
        print("- weekly ranking preview:")
        for index, (username, points) in enumerate(ranked[:5], start=1):
            print(f"  {index}. {username}: +{points} pts")


if __name__ == "__main__":
    main()
