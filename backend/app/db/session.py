"""The engine and the sessions everything else is handed.

Routes get a Session from get_db(), scripts and background jobs from
get_sessionmaker(); repositories and services take it as an argument instead
of reaching for a global.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    # A chat stream keeps its connection for the whole turn (PERFORMANCE_ISSUES
    # #9), so the pool holds one per stream thread; the overflow covers the
    # short requests on the default thread pool. pre_ping replaces
    # connections the server closed while they sat idle.
    return create_engine(
        settings.database_url,
        pool_size=settings.ai_stream_threads,
        max_overflow=20,
        pool_pre_ping=True,
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    # Same expire_on_commit as Flask-SQLAlchemy, so repository code behaves the
    # same whichever framework handed it the session.
    return sessionmaker(get_engine())


def get_db() -> Iterator[Session]:
    """One Session per request; FastAPI injects it with Depends(get_db)."""
    with get_sessionmaker()() as session:
        yield session
