"""The db_session fixture must undo everything a test writes, commits included.

The two tests run in file order: the first commits a row the way application
code does, the second checks it is gone. If the rollback ever stops working
(for example the session ends up on a different connection) the second fails.
"""

from __future__ import annotations

from sqlalchemy import select

from app.extensions.db import db
from app.models.user import User

MARKER = "isolation-probe"


def test_committed_row_is_visible_within_the_test(client, make_auth_headers):
    user_id, headers = make_auth_headers(username=MARKER, email=f"{MARKER}@example.com")
    db.session.commit()

    # Visible to a request made through the app, not just to this session.
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    assert db.session.get(User, user_id) is not None


def test_committed_row_is_gone_in_the_next_test():
    assert db.session.scalar(select(User).where(User.username == MARKER)) is None
