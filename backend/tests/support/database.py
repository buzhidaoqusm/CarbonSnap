"""``db.session`` for tests: the session of the test that is running.

The application takes its Session as an argument; tests keep a module-level
handle because their helpers are many and small. conftest's db_session
fixture binds ``db.session`` to the test's connection before each test and
unbinds it afterwards, so whatever a test writes is rolled back with it.
"""

from __future__ import annotations

from sqlalchemy.orm import scoped_session


class _TestDatabase:
    session: scoped_session


db = _TestDatabase()
