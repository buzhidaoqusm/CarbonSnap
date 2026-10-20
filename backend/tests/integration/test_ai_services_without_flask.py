"""The AI services run on a plain Session, with no Flask app or request.

FastAPI routes call them that way. A service that still reached for
db.session or the JWT in Flask's request would raise here, or quietly treat
the user as anonymous.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from flask import has_app_context, has_request_context
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai import AIConversation, RecyclingCase
from app.services.ai import ai_conversation_service, recycling_analysis_service
from tests.integration.test_ai_session_restore import _fake_models  # noqa: F401


@pytest.fixture()
def plain_session(db_connection):
    with Session(bind=db_connection, join_transaction_mode="create_savepoint") as session:
        yield session


def _in_a_thread(fn):
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(fn).result()


def test_a_recycling_analysis_is_stored_for_the_user(plain_session, make_auth_headers):
    user_id, _ = make_auth_headers()

    def run():
        assert not has_app_context() and not has_request_context()
        events = list(
            recycling_analysis_service.stream_recycling_analysis(
                plain_session,
                user_id=user_id,
                message="A bottle",
                image_data_url=None,
                session_id="no-flask",
            )
        )
        return events

    events = _in_a_thread(run)

    assert not [e for e in events if e.get("type") == "error"], events
    case = plain_session.scalar(select(RecyclingCase).where(RecyclingCase.user_id == user_id))
    assert case is not None and case.status == "pending_audit"


def test_conversations_are_listed_for_the_user(plain_session, make_auth_headers):
    user_id, _ = make_auth_headers()
    plain_session.add(AIConversation(user_id=user_id, title="Bottles"))
    plain_session.commit()

    result = _in_a_thread(
        lambda: ai_conversation_service.list_user_conversations(
            plain_session, user_id=user_id, page=1, per_page=20
        )
    )

    assert [item["title"] for item in result["items"]] == ["Bottles"]
