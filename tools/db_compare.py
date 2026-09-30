"""Run the same four cases against SQLite and PostgreSQL, using the app's real models.

Run from backend/ (PostgreSQL: `docker compose up -d postgres` first):

    uv run python ../tools/db_compare.py sqlite:///../data/compare.db
    uv run python ../tools/db_compare.py \
        postgresql+psycopg://carbonsnap:carbonsnap@127.0.0.1:5432/compare

The tables are dropped and recreated, so the database must be named
"compare" (on PostgreSQL it is created fresh on every run).
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import app.models  # noqa: E402,F401  registers every table on db.metadata
from app.extensions.db import db  # noqa: E402

url = make_url(sys.argv[1])
if Path(url.database or "").stem != "compare":
    sys.exit(f"Refusing to use {url.database!r}: the database must be named 'compare'.")
if url.get_backend_name() == "postgresql":
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS compare WITH (FORCE)"))
        conn.execute(text("CREATE DATABASE compare"))
    admin.dispose()
engine = create_engine(url)
tables = [db.metadata.tables["users"], db.metadata.tables["ai_conversations"]]
db.metadata.drop_all(engine, tables=tables)
db.metadata.create_all(engine, tables=tables)

USER_SQL = text(
    "INSERT INTO users (username, email, password_hash, total_carbon_amount,"
    " current_points, created_at) VALUES (:u, :e, 'x', 0, :p, CURRENT_TIMESTAMP)"
)
CONV_SQL = text(
    "INSERT INTO ai_conversations (user_id, status, current_pending_action,"
    " last_message_at, created_at, updated_at) VALUES"
    " (:uid, 'active', 'none', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
)


def describe(exc: Exception) -> str:
    orig = getattr(exc, "orig", exc)
    return f"{type(orig).__name__}: {str(orig).splitlines()[0]}"


def attempt(sql, params) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(sql, params)
        print("  -> ACCEPTED (stored)")
    except Exception as exc:  # noqa: BLE001
        print(f"  -> REJECTED  {describe(exc)}")


print(f"== {engine.dialect.name} ==")
with engine.begin() as conn:
    conn.execute(USER_SQL, {"u": "alice", "e": "a@x", "p": 0})
    alice_id = conn.execute(text("SELECT id FROM users WHERE username='alice'")).scalar_one()

print("[1] foreign key: conversation for user_id=999999 (no such user)")
attempt(CONV_SQL, {"uid": 999999})

print("[2] length: 200-char username into VARCHAR(64)")
attempt(USER_SQL, {"u": "b" * 200, "e": "b@x", "p": 0})

print("[3] type: 'abc' into INTEGER current_points")
attempt(USER_SQL, {"u": "carol", "e": "c@x", "p": "abc"})

print("[4] concurrency: A keeps a write transaction on users open for 10 s;")
print("    0.5 s later B writes an unrelated row into ai_conversations")
result: dict[str, str] = {}


def writer_a() -> None:
    with engine.begin() as conn:
        conn.execute(USER_SQL, {"u": "dave", "e": "d@x", "p": 0})
        time.sleep(10)  # e.g. an LLM call made while the transaction is still open


def writer_b() -> None:
    start = time.perf_counter()
    try:
        with engine.begin() as conn:
            conn.execute(CONV_SQL, {"uid": alice_id})
        result["b"] = f"committed after {time.perf_counter() - start:.2f} s"
    except Exception as exc:  # noqa: BLE001
        result["b"] = f"FAILED after {time.perf_counter() - start:.2f} s  {describe(exc)}"


ta = threading.Thread(target=writer_a)
ta.start()
time.sleep(0.5)
tb = threading.Thread(target=writer_b)
tb.start()
ta.join()
tb.join()
print(f"  -> B {result['b']}")

with engine.connect() as conn:
    print("\nusers table now:")
    rows = conn.execute(text("SELECT id, length(username), current_points FROM users ORDER BY id"))
    for row in rows:
        print(f"  id={row[0]} username_len={row[1]} current_points={row[2]!r}")
    owners = conn.execute(text("SELECT user_id FROM ai_conversations ORDER BY id")).scalars()
    print(f"ai_conversations.user_id: {owners.all()}")
