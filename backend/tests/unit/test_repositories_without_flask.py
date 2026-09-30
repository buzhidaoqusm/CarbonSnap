"""Repositories must work with a plain Session and no Flask app context.

That is how FastAPI routes, scripts and workers will call them. Every test
body runs inside the app context that db_session opens, so the calls here run
in a fresh thread, which starts without one (Flask keeps it in a contextvar).
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from flask import has_app_context
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.repositories.notification import notification_repository
from app.repositories.profile import user_repository


def _run_without_app_context(func: Callable[[], object]) -> object:
    outcome: dict[str, object] = {}

    def target() -> None:
        try:
            assert not has_app_context()
            outcome["value"] = func()
        except BaseException as exc:  # re-raised in the test thread
            outcome["error"] = exc

    thread = threading.Thread(target=target)
    thread.start()
    thread.join()
    if "error" in outcome:
        raise outcome["error"]  # type: ignore[misc]
    return outcome["value"]


def test_repositories_run_on_a_plain_session(db_session):
    # Same connection as the test, so the outer rollback still cleans up.
    connection = db_session.connection()

    def work() -> tuple[str, int]:
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            user = User(username="no-flask", email="no-flask@example.com", password_hash="x")
            session.add(user)
            session.flush()
            notification_repository.create_notification(
                session,
                recipient_user_id=user.id,
                event_type="post_liked",
                source_type="forum_post",
                source_id=1,
                title="hello",
            )
            fetched = user_repository.get_by_id(session, user.id)
            assert fetched is not None
            return fetched.username, notification_repository.count_unread(session, user.id)

    assert _run_without_app_context(work) == ("no-flask", 1)


def test_get_db_yields_a_session_without_flask():
    def work() -> int:
        sessions = get_db()
        session = next(sessions)
        try:
            return session.scalar(select(1)) or 0
        finally:
            sessions.close()

    assert _run_without_app_context(work) == 1
