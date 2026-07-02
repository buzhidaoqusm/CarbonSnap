from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

from flask import current_app, has_app_context

from app.extensions.db import db
from app.services.forum import forum_indexing_service
from app.services.recommendation import topic_mapping_service


_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="forum-maintenance")


def enqueue_post_refresh(*, post_id: int, title: str, content: str) -> Future | None:
    return _run_or_enqueue(
        _refresh_post_search_surfaces,
        post_id=int(post_id),
        title=str(title or ""),
        content=str(content or ""),
    )


def enqueue_post_removal(*, post_id: int) -> Future | None:
    return _run_or_enqueue(_remove_post_search_surfaces, post_id=int(post_id))


def _refresh_post_search_surfaces(*, post_id: int, title: str, content: str) -> None:
    forum_indexing_service.reindex_post(post_id=post_id, title=title, content=content)
    topic_mapping_service.refresh_forum_post_topics(post_id=post_id, title=title, content=content)


def _remove_post_search_surfaces(*, post_id: int) -> None:
    forum_indexing_service.remove_post_index(post_id)


def _run_or_enqueue(func: Callable[..., Any], **kwargs: Any) -> Future | None:
    if _should_run_inline():
        func(**kwargs)
        return None

    app = current_app._get_current_object() if has_app_context() else None
    if app is None:
        return _EXECUTOR.submit(func, **kwargs)
    return _EXECUTOR.submit(_run_with_app_context, app, func, kwargs)


def _run_with_app_context(app: Any, func: Callable[..., Any], kwargs: dict[str, Any]) -> None:
    with app.app_context():
        try:
            func(**kwargs)
        except Exception:
            current_app.logger.exception("Forum background maintenance job failed.")
        finally:
            db.session.remove()


def _should_run_inline() -> bool:
    if not has_app_context():
        return False

    if current_app.config.get("FORUM_BACKGROUND_JOBS_INLINE"):
        return True

    if current_app.config.get("FORUM_BACKGROUND_JOBS_ENABLED") is False:
        return True

    return bool(current_app.config.get("TESTING"))
