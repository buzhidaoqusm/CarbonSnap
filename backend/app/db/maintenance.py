"""Bulk operations for the seed and reset scripts."""

from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session


def truncate_tables(session: Session, table_names: Iterable[str]) -> None:
    """Empty tables and restart their id sequences, in one statement.

    CASCADE also empties any table whose foreign keys point at one of these,
    so no orphaned rows are left behind. Commits.
    """
    names = sorted(set(table_names))
    if not names:
        return
    quoted = ", ".join(f'"{name}"' for name in names)
    session.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))
    session.commit()
