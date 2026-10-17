"""Best-effort writes that run after a request's own work.

Behaviour events, preference profiles, the memory summary and ranking are
derived data: a failure must not fail the request. But a failed write leaves
the session's transaction failed, and every later query in the request then
raises, which turns a success into a 500. Call this from the except block.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def discard_failed_side_effect(session: Session, what: str) -> None:
    """Log the error and roll back the failed transaction.

    Only for blocks that run after the request's own work is committed, or
    when it has written nothing yet: the rollback discards anything pending.
    """
    logger.exception("Side effect failed (%s); continuing without it.", what)
    session.rollback()
