"""Migrations must build the production schema on an empty PostgreSQL database.

The container runs ``alembic upgrade head`` on start, so this runs the same
command, in a subprocess, against a scratch database next to the test one.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def scratch_database_url():
    test_url = make_url(os.environ["DATABASE_URL"])
    url = test_url.set(database=f"{test_url.database}_migrations")
    admin = create_engine(test_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    yield url.render_as_string(hide_password=False)
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
    admin.dispose()


def _alembic(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL": database_url}
    return subprocess.run(
        [str(Path(sys.executable).with_name("alembic")), "-c", "migrations/alembic.ini", *args],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def _check(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, f"{result.args}\n{result.stdout}\n{result.stderr}"


def test_migrations_upgrade_match_models_and_downgrade(scratch_database_url):
    _check(_alembic(scratch_database_url, "upgrade", "head"))
    # No difference between the migrated schema and the models.
    _check(_alembic(scratch_database_url, "check"))
    # Every downgrade works too, and the chain can be replayed.
    _check(_alembic(scratch_database_url, "downgrade", "base"))
    _check(_alembic(scratch_database_url, "upgrade", "head"))


# The last revision before market refunds got their own source type.
BEFORE_MARKET_REFUND = "c2e8f1a3b7d5"


def test_market_refunds_are_backfilled_and_restored(scratch_database_url):
    # Rows as the old cancel_order wrote them: the buyer's refund was a
    # 'market_order' earn row, the same shape as the seller's settlement, and
    # only the order's buyer tells them apart. Plain SQL, so the rows match the
    # schema of that revision whatever the models look like later.
    _check(_alembic(scratch_database_url, "upgrade", BEFORE_MARKET_REFUND))
    engine = create_engine(scratch_database_url)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, username, email, password_hash,"
                    " total_carbon_amount, current_points, created_at) VALUES"
                    " (1, 'buyer', 'buyer@example.com', 'x', 0, 0, now()),"
                    " (2, 'seller', 'seller@example.com', 'x', 0, 0, now())"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO market_items (id, seller_id, title, price_points, status,"
                    " created_at) VALUES (1, 2, 'Bike', 100, 'sold_out', now())"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO orders (id, item_id, buyer_id, seller_id, price_points, status,"
                    " created_at) VALUES"
                    " (1, 1, 1, 2, 100, 'cancelled', now()),"
                    " (2, 1, 1, 2, 100, 'completed', now())"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO transactions (id, user_id, type, points_delta, co2_delta_kg,"
                    " source_type, source_id, created_at) VALUES"
                    # Order 1, cancelled: the buyer paid, then got a refund.
                    " (1, 1, 'spend', 100, 0, 'market_order', 1, now()),"
                    " (2, 1, 'earn', 100, 0, 'market_order', 1, now()),"
                    # Order 2, completed: the buyer paid, the seller was paid.
                    " (3, 1, 'spend', 100, 0, 'market_order', 2, now()),"
                    " (4, 2, 'earn', 100, 0, 'market_order', 2, now()),"
                    # Recycling earn whose source_id happens to match order 1.
                    " (5, 1, 'earn', 3, 0.03, 'waste_analysis', 1, now())"
                )
            )
        before = {
            1: "market_order",
            2: "market_order",
            3: "market_order",
            4: "market_order",
            5: "waste_analysis",
        }

        _check(_alembic(scratch_database_url, "upgrade", "head"))
        assert _transaction_source_types(engine) == {**before, 2: "market_refund"}

        _check(_alembic(scratch_database_url, "downgrade", BEFORE_MARKET_REFUND))
        assert _transaction_source_types(engine) == before
    finally:
        engine.dispose()


def _transaction_source_types(engine) -> dict[int, str]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, source_type FROM transactions")).all()
    return {row.id: row.source_type for row in rows}
