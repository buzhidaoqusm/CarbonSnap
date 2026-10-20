"""Database sessions without Flask.

FastAPI routes, scripts and tests get a Session from here; repositories take
that Session as an argument instead of reaching for a global. During the move
off Flask, Flask-SQLAlchemy keeps its own engine for the Flask routes, so a
process holds two small pools against the same database until 3.4 removes
the Flask side.
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
