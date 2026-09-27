"""Migrations must build the production schema on an empty PostgreSQL database.

The container runs ``flask db upgrade`` on start, so this runs the same
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


def _flask_db(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL": database_url}
    return subprocess.run(
        [sys.executable, "-m", "flask", "--app", "app:create_app()", "db", *args],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def _check(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, f"{result.args}\n{result.stdout}\n{result.stderr}"


def test_migrations_upgrade_match_models_and_downgrade(scratch_database_url):
    _check(_flask_db(scratch_database_url, "upgrade"))
    # No difference between the migrated schema and the models.
    _check(_flask_db(scratch_database_url, "check"))
    # Every downgrade works too, and the chain can be replayed.
    _check(_flask_db(scratch_database_url, "downgrade", "base"))
    _check(_flask_db(scratch_database_url, "upgrade"))
