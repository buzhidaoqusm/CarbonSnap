"""Concurrent requests must not spend points twice, overfund or double-sell.

The rest of the suite runs every request on one connection inside one
rolled-back transaction, so requests can never overlap there. These tests
start the real server in a subprocess against a scratch database and send
pairs of requests released together by a barrier.

Before the rows were locked, 20 rounds of the first, third and fourth went
wrong 14, 19 and 16 times: balances lost 60 points per bad round, projects
raised 120 of 100, items got two orders.
"""

from __future__ import annotations

import datetime as dt
import os
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.ledger import Transaction
from app.models.market import MarketItem, Order
from app.models.project import Project, ProjectContribution
from app.models.user import User

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ROUNDS = 10


@pytest.fixture(scope="module")
def scratch_url() -> Iterator[str]:
    test_url = make_url(os.environ["DATABASE_URL"])
    url = test_url.set(database=f"{test_url.database}_concurrency")
    admin = create_engine(test_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    rendered = url.render_as_string(hide_password=False)
    upgrade = subprocess.run(
        [sys.executable, "-m", "flask", "--app", "app:create_app()", "db", "upgrade"],
        cwd=BACKEND_ROOT,
        env={**os.environ, "DATABASE_URL": rendered},
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert upgrade.returncode == 0, upgrade.stderr
    yield rendered
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
    admin.dispose()


@pytest.fixture(scope="module")
def base_url(scratch_url) -> Iterator[str]:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "--factory",
            "app.main:create_api",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=BACKEND_ROOT,
        env={**os.environ, "DATABASE_URL": scratch_url},
    )
    base = f"http://127.0.0.1:{port}/api"
    try:
        deadline = time.monotonic() + 60
        while True:
            try:
                if httpx.get(f"{base}/health", trust_env=False).status_code == 200:
                    break
            except httpx.TransportError:
                pass
            assert server.poll() is None, "server exited"
            assert time.monotonic() < deadline, "server did not start"
            time.sleep(0.2)
        yield base
    finally:
        server.terminate()
        server.wait(timeout=30)


@pytest.fixture(scope="module")
def db(scratch_url) -> Iterator[Session]:
    engine = create_engine(scratch_url)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _user(db: Session, points: int) -> tuple[int, dict[str, str]]:
    n = db.scalar(select(func.count()).select_from(User)) or 0
    user = User(
        username=f"user{n}", email=f"user{n}@example.com", password_hash="x", current_points=points
    )
    db.add(user)
    db.commit()
    return user.id, {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _project(db: Session, creator_id: int, target: int) -> int:
    project = Project(
        creator_user_id=creator_id,
        title="Rain garden",
        points_target=target,
        deadline_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=5),
    )
    db.add(project)
    db.commit()
    return project.id


def _together(base: str, requests: list[Callable[[httpx.Client], httpx.Response]]):
    barrier = threading.Barrier(len(requests))
    responses: list[httpx.Response | None] = [None] * len(requests)

    def run(i: int) -> None:
        with httpx.Client(base_url=base, timeout=30, trust_env=False) as client:
            barrier.wait()
            responses[i] = requests[i](client)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(len(requests))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return [r.status_code for r in responses if r is not None]


def test_one_balance_cannot_pay_twice(base_url, db):
    for _ in range(ROUNDS):
        maker_id, _ = _user(db, 0)
        backer_id, backer = _user(db, 100)
        first, second = _project(db, maker_id, 1000), _project(db, maker_id, 1000)

        statuses = _together(
            base_url,
            [
                lambda c, p=p, h=backer: c.post(
                    f"/projects/{p}/contributions", json={"points": 60}, headers=h
                )
                for p in (first, second)
            ],
        )

        db.expire_all()
        spent = db.scalar(
            select(func.sum(Transaction.points_delta)).where(
                Transaction.user_id == backer_id, Transaction.type == "spend"
            )
        )
        assert sorted(statuses) == [201, 402]
        assert (db.get(User, backer_id).current_points, spent) == (40, 60)


def test_one_user_funding_two_projects_at_once(base_url, db):
    # Both succeed, and both then rebuild the user's preference profile. That
    # rebuild deletes and re-inserts the user's rows; run twice at once, the
    # second insert hit the unique key, the error was swallowed, and the
    # still-failed session turned an already committed contribution into a 500.
    for _ in range(ROUNDS):
        maker_id, _ = _user(db, 0)
        _, backer = _user(db, 200)
        first, second = _project(db, maker_id, 1000), _project(db, maker_id, 1000)

        statuses = _together(
            base_url,
            [
                lambda c, p=p, h=backer: c.post(
                    f"/projects/{p}/contributions", json={"points": 60}, headers=h
                )
                for p in (first, second)
            ],
        )

        assert statuses == [201, 201]


def test_a_project_cannot_be_overfunded(base_url, db):
    for _ in range(ROUNDS):
        maker_id, _ = _user(db, 0)
        backers = [_user(db, 100)[1] for _ in range(2)]
        project_id = _project(db, maker_id, 100)

        statuses = _together(
            base_url,
            [
                lambda c, h=h, p=project_id: c.post(
                    f"/projects/{p}/contributions", json={"points": 60}, headers=h
                )
                for h in backers
            ],
        )

        db.expire_all()
        raised = db.scalar(
            select(func.sum(ProjectContribution.points)).where(
                ProjectContribution.project_id == project_id
            )
        )
        assert sorted(statuses) == [201, 409]
        assert (raised, db.get(Project, project_id).points_raised) == (60, 60)


def test_an_item_cannot_be_sold_twice(base_url, db):
    for _ in range(ROUNDS):
        seller_id, _ = _user(db, 0)
        buyers = [_user(db, 100)[1] for _ in range(2)]
        item = MarketItem(seller_id=seller_id, title="Bike", price_points=50)
        db.add(item)
        db.commit()

        statuses = _together(
            base_url,
            [
                lambda c, h=h, i=item.id: c.post("/market/orders", json={"item_id": i}, headers=h)
                for h in buyers
            ],
        )

        orders = db.scalar(select(func.count()).select_from(Order).where(Order.item_id == item.id))
        assert sorted(statuses) == [201, 409]
        assert orders == 1


def test_an_order_cannot_be_both_shipped_and_cancelled(base_url, db):
    # Both checked status == "paid" and then wrote: the buyer was refunded for
    # an order the seller had shipped, and could still confirm it, paying the
    # seller too (15 of 20 rounds).
    for _ in range(ROUNDS):
        seller_id, seller = _user(db, 0)
        buyer_id, buyer = _user(db, 100)
        item = MarketItem(seller_id=seller_id, title="Bike", price_points=50)
        db.add(item)
        db.commit()
        with httpx.Client(base_url=base_url, timeout=30, trust_env=False) as client:
            order = client.post("/market/orders", json={"item_id": item.id}, headers=buyer)
        order_id = order.json()["data"]["id"]

        statuses = _together(
            base_url,
            [
                lambda c, o=order_id, h=seller: c.patch(f"/market/orders/{o}/ship", headers=h),
                lambda c, o=order_id, h=buyer: c.patch(f"/market/orders/{o}/cancel", headers=h),
            ],
        )

        assert sorted(statuses) == [200, 409]
