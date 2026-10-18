"""Re-index a forum post after it is written, off the request thread.

A job runs either inline, in the caller's session (the tests, so the work
stays inside their transaction), or on a worker thread in a session of its
own. A worker cannot borrow the request's session: a Session is not
thread-safe, and the request may close it before the job runs.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.services.forum import forum_indexing_service
from app.services.recommendation import topic_mapping_service

logger = logging.getLogger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="forum-maintenance")

Job = Callable[..., Any]


def enqueue_post_refresh(
    session: Session, *, post_id: int, title: str, content: str
) -> Future[None] | None:
    return _run_or_enqueue(
        session,
        _refresh_post_search_surfaces,
        post_id=int(post_id),
        title=str(title or ""),
        content=str(content or ""),
    )


def enqueue_post_removal(session: Session, *, post_id: int) -> Future[None] | None:
    return _run_or_enqueue(session, _remove_post_search_surfaces, post_id=int(post_id))


def _refresh_post_search_surfaces(
    session: Session, *, post_id: int, title: str, content: str
) -> None:
    forum_indexing_service.reindex_post(session, post_id=post_id, title=title, content=content)
    topic_mapping_service.refresh_forum_post_topics(
        session, post_id=post_id, title=title, content=content
    )


def _remove_post_search_surfaces(session: Session, *, post_id: int) -> None:
    forum_indexing_service.remove_post_index(session, post_id)


def _run_or_enqueue(session: Session, job: Job, **kwargs: Any) -> Future[None] | None:
    if get_settings().forum_background_jobs_inline:
        job(session, **kwargs)
        return None
    future = _EXECUTOR.submit(_run_in_own_session, job, kwargs)
    # Nobody waits on the Future, so an error would otherwise vanish with it.
    future.add_done_callback(_log_failure)
    return future


def _run_in_own_session(job: Job, kwargs: dict[str, Any]) -> None:
    with get_sessionmaker()() as session:
        job(session, **kwargs)


def _log_failure(future: Future[None]) -> None:
    error = future.exception()
    if error is not None:
        logger.error("Forum background job failed.", exc_info=error)
