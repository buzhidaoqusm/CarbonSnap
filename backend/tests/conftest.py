"""Shared pytest fixtures for all test layers.

Architecture:
- Tests run on PostgreSQL, the same database as production, so dialect
  behaviour (foreign keys, string lengths, types) is what gets tested. Start it
  with ``docker compose up -d postgres``; ``TEST_DATABASE_URL`` points elsewhere.
- Every run drops and recreates the test database, whose name must end in
  ``_test``. The environment is pinned *before* ``create_app()`` runs, because
  Flask-SQLAlchemy 3.x builds the engine inside ``init_app`` — overriding
  ``SQLALCHEMY_DATABASE_URI`` afterwards has no effect.
- `app` fixture is session-scoped (created once) and asserts the engine really
  landed on the test database.
- Tables are created once per run. `db_session` runs every test inside one
  outer transaction and rolls it back afterwards, so nothing a test writes is
  seen by the next one, even though the code under test calls commit().
- `client` provides a Flask test client.
- `make_auth_headers` is a per-test factory that creates distinct users.
"""

import os
import socket
from pathlib import Path
from tempfile import mkdtemp

import pytest
from flask_sqlalchemy.session import _app_ctx_id
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import scoped_session, sessionmaker

# --- Pinned before importing the app: settings read os.environ at import/boot.
_TEST_TMP_ROOT = Path(mkdtemp(prefix="carbonsnap-tests-"))
# 127.0.0.1, not localhost: on Windows localhost tries ::1 first, which the
# compose port binding does not answer, and each new connection then hangs
# until the TCP connect timeout.
_TEST_DATABASE_URL = make_url(
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://carbonsnap:carbonsnap@127.0.0.1:5432/carbonsnap_test",
    )
)

_EMPTY_ENV_FILE = _TEST_TMP_ROOT / "empty.env"
_EMPTY_ENV_FILE.write_text("", encoding="utf-8")

os.environ.update(
    {
        # Ignore the developer's local .env so results are identical here and
        # in CI; everything the suite depends on is pinned below.
        "ENV_FILE": str(_EMPTY_ENV_FILE),
        # Never touch the developer's dev database.
        "DATABASE_URL": _TEST_DATABASE_URL.render_as_string(hide_password=False),
        "UPLOAD_ROOT": str(_TEST_TMP_ROOT / "uploads"),
        "UPLOAD_URL_PREFIX": "/api/uploads",
        "JWT_SECRET_KEY": "test-secret",
        # Placeholder credentials: non-empty so provider config checks pass,
        # never valid so an un-mocked call fails instead of billing anyone.
        "OPENROUTER_API_KEY": "test-key",
        "QWEN_API_KEY": "test-key",
        "OPENROUTER_BASE_URL": "http://openrouter.test.invalid/v1",
        "QWEN_BASE_URL": "http://qwen.test.invalid/v1",
        # Obviously fake endpoints. The block_network fixture below is what
        # actually stops outbound traffic; these just make intent clear.
        "OSM_NOMINATIM_URL": "http://nominatim.test.invalid",
        "OSM_OVERPASS_URL": "http://overpass.test.invalid/api/interpreter",
        # Empty JSON list, otherwise settings falls back to public mirrors.
        "OSM_OVERPASS_FALLBACK_URLS_JSON": "[]",
        "OSM_OVERPASS_TIMEOUT_SECONDS": "1",
        "OSM_OVERPASS_CONNECT_TIMEOUT_SECONDS": "1",
        "OSM_OVERPASS_MAX_ATTEMPTS_PER_ENDPOINT": "1",
        "OSM_OVERPASS_RETRY_BACKOFF_MS": "0",
        "AI_LLM_TIMEOUT_SECONDS": "5",
        "AI_LLM_MAX_RETRIES": "0",
        "AI_DECISION_ENGINE_MODE": "llm_first",
        "AI_DECISION_ENGINE_VERSION": "decision-engine-v2",
        "AI_DECISION_CONFIDENCE_THRESHOLD": "0.65",
        # Optional subsystems stay off unless a test turns them on.
        "AI_GRAPH_AGENT_ENABLED": "false",
        "AI_NEO4J_GRAPHRAG_ENABLED": "false",
        "AI_DEMO_REPLAY_ENABLED": "false",
        "AI_TOOL_SELECTION_MODE": "",
        "AI_TOOL_SELECTION_SHADOW_LOG": "",
        "NEO4J_URI": "",
        "NEO4J_USERNAME": "",
        "NEO4J_PASSWORD": "",
    }
)

from flask_jwt_extended import create_access_token  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions.db import db as _db  # noqa: E402
from app.models.user import User  # noqa: E402

# ---------------------------------------------------------------------------
# App fixture  (session-scoped — created once per test run)
# ---------------------------------------------------------------------------


def _recreate_test_database() -> None:
    name = _TEST_DATABASE_URL.database or ""
    # Fail loudly rather than destroying a real database.
    assert name.endswith("_test"), (
        f"Test database {name!r} does not end in '_test'. Refusing to drop it."
    )
    admin = create_engine(_TEST_DATABASE_URL.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{name}"'))
    except Exception as exc:
        pytest.exit(
            f"Cannot reach PostgreSQL at {_TEST_DATABASE_URL!r}: {exc}. "
            "Start it with: docker compose up -d postgres",
            returncode=2,
        )
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def app():
    _recreate_test_database()
    flask_app = create_app()
    flask_app.config.update(
        TESTING=True,
        JWT_ACCESS_TOKEN_EXPIRES=False,
    )
    with flask_app.app_context():
        # Fail loudly rather than writing to a real database.
        bound = _db.engine.url.database
        assert bound == _TEST_DATABASE_URL.database, (
            f"Tests are bound to {bound!r} instead of {_TEST_DATABASE_URL.database!r}. "
            "Refusing to run."
        )
        _db.create_all()
        yield flask_app


# ---------------------------------------------------------------------------
# Network isolation
# ---------------------------------------------------------------------------

_ALLOWED_HOSTS = {"127.0.0.1", "::1", "localhost", ""}


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Fail fast on any un-mocked outbound connection.

    Without this a forgotten mock silently calls a real provider: it bills
    someone, makes the suite non-deterministic, and (on Windows) costs seconds
    per attempt waiting for the connection to be refused.
    """
    real_getaddrinfo = socket.getaddrinfo
    real_create_connection = socket.create_connection
    real_connect = socket.socket.connect

    def _check(host) -> None:
        if str(host) not in _ALLOWED_HOSTS:
            raise RuntimeError(
                f"Blocked network access to {host!r} during tests. "
                "Mock the client instead of calling out."
            )

    def guarded_getaddrinfo(host, *args, **kwargs):
        _check(host)
        return real_getaddrinfo(host, *args, **kwargs)

    def guarded_create_connection(address, *args, **kwargs):
        _check(address[0] if isinstance(address, tuple) else address)
        return real_create_connection(address, *args, **kwargs)

    def guarded_connect(self, address, *args, **kwargs):
        if isinstance(address, tuple):
            _check(address[0])
        return real_connect(self, address, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", guarded_create_connection)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)


# ---------------------------------------------------------------------------
# Config isolation  (the app fixture is session-scoped, so feature flags a test
# flips with app.config.update() would otherwise leak into every later test)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def restore_app_config(app):
    original = dict(app.config)
    yield
    app.config.clear()
    app.config.update(original)


@pytest.fixture
def override_settings(app, monkeypatch):
    """Change settings for one test: ``override_settings(ai_trace_enabled=False)``.

    Updates both get_settings() and the legacy app.config keys, so a test works
    whether the code under test has moved to get_settings() yet or not. Both
    are restored when the test ends. Values are used as given, not validated.
    """
    from app.config.settings import legacy_config
    from app.core import config

    def apply(**changes):
        unknown = sorted(set(changes) - set(config.Settings.model_fields))
        # Settings ignores unknown names, so a typo here would silently change
        # nothing and the test would pass for the wrong reason.
        assert not unknown, f"Unknown settings: {unknown}"
        updated = config.get_settings().model_copy(update=changes)
        monkeypatch.setattr(config, "_override", updated)
        app.config.update(legacy_config(updated))
        return updated

    return apply


# ---------------------------------------------------------------------------
# DB isolation  (function-scoped — every test is rolled back)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def db_session(app):
    """Run the test inside a transaction that is rolled back when it ends.

    The code under test commits freely. With join_transaction_mode
    "create_savepoint" each of those commits only releases a SAVEPOINT inside
    the outer transaction, and the final rollback undoes all of them.

    db.session is swapped for a plain SQLAlchemy session bound to that one
    connection: Flask-SQLAlchemy's own Session.get_bind() always hands back the
    engine for mapped classes, so a session-level bind would be ignored and
    queries would quietly run on a fresh, un-rolled-back connection. Scoping
    stays per app context, as in Flask-SQLAlchemy.
    """
    with app.app_context():
        connection = _db.engine.connect()
        outer = connection.begin()
        session = scoped_session(
            sessionmaker(bind=connection, join_transaction_mode="create_savepoint"),
            scopefunc=_app_ctx_id,
        )
        original = _db.session
        _db.session = session
        try:
            yield session
        finally:
            session.remove()
            _db.session = original
            outer.rollback()
            connection.close()


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# User / auth helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def make_user(app):
    """Factory: make_user(username, email, password) -> (User, token).

    Runs inside the current app context so the user is visible to the
    same db session used by the test.
    """

    def _factory(
        username: str = "testuser",
        email: str = "test@example.com",
        password: str = "password123",
        points: int = 0,
    ):
        with app.app_context():
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                current_points=points,
            )
            _db.session.add(user)
            _db.session.flush()
            _db.session.commit()  # commit so HTTP requests see the row
            token = create_access_token(identity=str(user.id))
            # Re-fetch to get a detached-safe copy with the real PK.
            user_id = user.id
        return user_id, token

    return _factory


@pytest.fixture()
def make_auth_headers(make_user):
    """Factory: returns (user_id, headers) for a new unique user per call."""
    counter = {"n": 0}

    def _factory(username: str | None = None, email: str | None = None, points: int = 0):
        n = counter["n"]
        counter["n"] += 1
        user_id, token = make_user(
            username=username or f"user{n}",
            email=email or f"user{n}@example.com",
            points=points,
        )
        return user_id, {"Authorization": f"Bearer {token}"}

    return _factory
