from collections.abc import Iterable

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()


def truncate_tables(table_names: Iterable[str]) -> None:
    """Empty tables and restart their id sequences, in one statement.

    CASCADE also empties any table whose foreign keys point at one of these,
    so no orphaned rows are left behind. Commits.
    """
    names = sorted(set(table_names))
    if not names:
        return
    quoted = ", ".join(f'"{name}"' for name in names)
    db.session.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))
    db.session.commit()
