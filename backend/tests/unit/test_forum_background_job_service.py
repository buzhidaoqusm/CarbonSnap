from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

import pytest
from flask import has_app_context
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.user import User
from app.repositories.forum import forum_repository
from app.services.forum import forum_background_job_service as jobs


@pytest.fixture
def background(monkeypatch, override_settings, db_connection):
    """Jobs run on a real worker thread, which has no Flask app context.

    Sessions the job opens for itself are bound to the test's connection, so
    it can see the test's rows and its writes are rolled back with them.
    """
    override_settings(forum_background_jobs_inline=False)
    executor = ThreadPoolExecutor(max_workers=1)
    monkeypatch.setattr(jobs, "_EXECUTOR", executor)
    monkeypatch.setattr(
        jobs,
        "get_sessionmaker",
        lambda: sessionmaker(bind=db_connection, join_transaction_mode="create_savepoint"),
    )
    yield
    executor.shutdown(wait=True)


def _post() -> int:
    user = User(
        username="author", email="author@example.com", password_hash=generate_password_hash("x")
    )
    db.session.add(user)
    db.session.flush()
    post = forum_repository.create_post(
        db.session, author_id=user.id, title="Bottle caps", content="Keep the caps on."
    )
    return post.id


def test_inline_runs_in_the_callers_session(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        jobs.forum_indexing_service,
        "reindex_post",
        lambda session, **kwargs: seen.update(session=session, **kwargs) or [],
    )
    monkeypatch.setattr(
        jobs.topic_mapping_service, "refresh_forum_post_topics", lambda session, **kwargs: []
    )

    result = jobs.enqueue_post_refresh(db.session, post_id=12, title="Bottle", content="Tips")

    assert result is None
    assert seen == {"session": db.session, "post_id": 12, "title": "Bottle", "content": "Tips"}


def test_background_job_indexes_without_an_app_context(background, monkeypatch, llm_unavailable):
    # The job used db.session, which raised "Working outside of application
    # context" on the worker thread; the error stayed in the unread Future.
    post_id = _post()
    contexts = []
    reindex = jobs.forum_indexing_service.reindex_post

    def spy(session, **kwargs):
        contexts.append(has_app_context())
        return reindex(session, **kwargs)

    monkeypatch.setattr(jobs.forum_indexing_service, "reindex_post", spy)

    future = jobs.enqueue_post_refresh(
        db.session, post_id=post_id, title="Bottle caps", content="Keep the caps on."
    )
    assert future is not None
    future.result(timeout=30)

    assert contexts == [False]
    assert forum_repository.get_chunks_by_post(db.session, post_id)


def test_background_removal_without_an_app_context(background):
    post_id = _post()
    forum_repository.save_post_chunks(
        db.session,
        post_id,
        [{"chunk_index": 0, "chunk_version": 1, "chunk_text": "x", "embedding_id": "e"}],
    )

    jobs.enqueue_post_removal(db.session, post_id=post_id).result(timeout=30)

    assert forum_repository.get_chunks_by_post(db.session, post_id) == []


def test_a_failing_background_job_is_logged(background, monkeypatch, caplog):
    def boom(session, **kwargs):
        raise RuntimeError("index unavailable")

    monkeypatch.setattr(jobs.forum_indexing_service, "reindex_post", boom)

    with caplog.at_level(logging.ERROR, logger=jobs.__name__):
        future = jobs.enqueue_post_refresh(db.session, post_id=1, title="t", content="c")
        with pytest.raises(RuntimeError):
            future.result(timeout=30)
        jobs._EXECUTOR.shutdown(wait=True)  # let the done-callback run

    assert "Forum background job failed" in caplog.text
    assert "index unavailable" in caplog.text
