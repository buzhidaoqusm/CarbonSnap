"""
Seed four test accounts designed to showcase different forest density tiers.

Each account has a distinct points level so testers can verify the 3D forest
scene at various fill stages without touching production or demo data.

Usage (from repo root):
  backend\\.venv\\Scripts\\python.exe backend\\scripts\\seed_forest_test_users.py

Running this script multiple times is safe – existing rows are updated in-place
(matched by email). No other tables are modified.

Login credentials (all accounts share the same password format):
  Password: Forest@1!
  ──────────────────────────────────────────────────────────────────────────────
  forest_seedling   / seedling@forest-test.dev   →   150 pts  →  3 trees
  forest_grower     / grower@forest-test.dev     →   750 pts  → 15 trees
  forest_guardian   / guardian@forest-test.dev   → 1 800 pts  → 36 trees
  forest_full       / full@forest-test.dev       → 3 000 pts  → 60 trees (max)
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND_ROOT))

from werkzeug.security import generate_password_hash  # noqa: E402 – must be after sys.path

from app import create_app  # noqa: E402
from app.extensions.db import db  # noqa: E402
from app.models.ledger import Transaction  # noqa: E402
from app.models.user import User  # noqa: E402

# ─── Account definitions ─────────────────────────────────────────────────────
#
# Points scale (after ×100 multiplier):
#   0.03 kg plastic bottle  → 0.03 × 1.5 × 100 = 4.5 → ~5 pts per scan
#
# Forest mapping (2 pts / tree, max 60 trees):
#   6 pts  → 3 trees   (seedling)
#   30 pts → 15 trees  (grower)
#   72 pts → 36 trees  (guardian)
#  120 pts → 60 trees  (full / max)
#
_PASSWORD = "Forest@1!"

_TEST_ACCOUNTS: list[dict] = [
    {
        "username": "forest_seedling",
        "email": "seedling@forest-test.dev",
        "bio": "Test account – sparse forest tier (3 trees).",
        "current_points": 6,
        "total_carbon_amount": 0.06,
        # Transactions that sum to current_points
        "transactions": [
            {"points": 4, "co2": 0.04, "source_type": "waste_analysis", "days_ago": 7},
            {"points": 2, "co2": 0.02, "source_type": "waste_analysis", "days_ago": 2},
        ],
    },
    {
        "username": "forest_grower",
        "email": "grower@forest-test.dev",
        "bio": "Test account – growing forest tier (15 trees).",
        "current_points": 30,
        "total_carbon_amount": 0.30,
        "transactions": [
            {"points": 10, "co2": 0.10, "source_type": "waste_analysis", "days_ago": 21},
            {"points":  8, "co2": 0.08, "source_type": "waste_analysis", "days_ago": 14},
            {"points":  7, "co2": 0.07, "source_type": "waste_analysis", "days_ago": 7},
            {"points":  5, "co2": 0.05, "source_type": "project",        "days_ago": 3},
        ],
    },
    {
        "username": "forest_guardian",
        "email": "guardian@forest-test.dev",
        "bio": "Test account – dense forest tier (36 trees).",
        "current_points": 72,
        "total_carbon_amount": 0.72,
        "transactions": [
            {"points": 20, "co2": 0.20, "source_type": "waste_analysis", "days_ago": 30},
            {"points": 18, "co2": 0.18, "source_type": "waste_analysis", "days_ago": 21},
            {"points": 15, "co2": 0.15, "source_type": "project",        "days_ago": 14},
            {"points": 12, "co2": 0.12, "source_type": "waste_analysis", "days_ago": 7},
            {"points":  7, "co2": 0.07, "source_type": "market_order",   "days_ago": 3},
        ],
    },
    {
        "username": "forest_full",
        "email": "full@forest-test.dev",
        "bio": "Test account – full forest tier (60 trees, max).",
        "current_points": 120,
        "total_carbon_amount": 1.20,
        "transactions": [
            {"points": 32, "co2": 0.32, "source_type": "waste_analysis", "days_ago": 60},
            {"points": 28, "co2": 0.28, "source_type": "waste_analysis", "days_ago": 45},
            {"points": 25, "co2": 0.25, "source_type": "project",        "days_ago": 30},
            {"points": 20, "co2": 0.20, "source_type": "waste_analysis", "days_ago": 14},
            {"points": 15, "co2": 0.15, "source_type": "market_order",   "days_ago": 7},
        ],
    },
]

_SOURCE_TYPE_TAG = "forest_test_seed"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _upsert_user(account: dict) -> tuple[User, bool]:
    """Return (user, created). Updates all fields if the user already exists."""
    user = db.session.query(User).filter_by(email=account["email"]).first()
    created = user is None
    if created:
        user = User(email=account["email"])
        db.session.add(user)

    user.username = account["username"]
    user.password_hash = generate_password_hash(_PASSWORD)
    user.bio = account["bio"]
    user.current_points = account["current_points"]
    user.total_carbon_amount = account["total_carbon_amount"]
    user.avatar_url = f"https://api.dicebear.com/9.x/shapes/svg?seed={account['username']}"
    if created:
        user.created_at = datetime.now(timezone.utc) - timedelta(days=120)

    return user, created


def _replace_transactions(user: User, txn_defs: list[dict]) -> int:
    """Delete any previous seed transactions for this user, then insert fresh ones."""
    db.session.query(Transaction).filter_by(
        user_id=user.id,
        source_type=_SOURCE_TYPE_TAG,
    ).delete(synchronize_session=False)

    now = datetime.now(timezone.utc)
    for index, txn_def in enumerate(txn_defs):
        txn = Transaction(
            user_id=user.id,
            type="earn",
            points_delta=txn_def["points"],
            co2_delta_kg=txn_def["co2"],
            source_type=_SOURCE_TYPE_TAG,
            source_id=index + 1,
            created_at=now - timedelta(days=txn_def["days_ago"]),
        )
        db.session.add(txn)

    return len(txn_defs)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()

        created_count = 0
        updated_count = 0
        txn_count = 0

        for account in _TEST_ACCOUNTS:
            user, created = _upsert_user(account)
            db.session.flush()  # obtain user.id before inserting transactions
            txn_count += _replace_transactions(user, account["transactions"])
            if created:
                created_count += 1
            else:
                updated_count += 1

        db.session.commit()

        print("Forest test accounts seeded successfully.")
        print(f"  created : {created_count}")
        print(f"  updated : {updated_count}")
        print(f"  transactions upserted: {txn_count}")
        print()
        print("─" * 62)
        print(f"  Shared password : {_PASSWORD}")
        print("─" * 62)
        print(f"  {'Email':<35}  {'Points':>7}  {'Trees':>6}")
        print(f"  {'─'*35}  {'─'*7}  {'─'*6}")
        for acct in _TEST_ACCOUNTS:
            trees = min(60, acct["current_points"] // 2)
            print(f"  {acct['email']:<35}  {acct['current_points']:>7}  {trees:>5}🌲")
        print("─" * 62)


if __name__ == "__main__":
    main()
