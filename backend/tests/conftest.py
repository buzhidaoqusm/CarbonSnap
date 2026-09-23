"""Shared pytest fixtures for all test layers.

Architecture:
- Every test run gets its own throwaway SQLite file in a temp directory. The
  environment is pinned *before* ``create_app()`` runs, because
  Flask-SQLAlchemy 3.x builds the engine inside ``init_app`` — overriding
  ``SQLALCHEMY_DATABASE_URI`` afterwards has no effect and silently leaves the
  suite pointed at the developer's ``data/carbonsnap.db`` (which ``drop_all``
  would then wipe).
- `app` fixture is session-scoped (created once) and asserts the engine really
  landed on the throwaway database.
- `db_session` fixture is function-scoped: drops and recreates all tables
  before every test, guaranteeing full data isolation.
- `client` provides a Flask test client.
- `make_auth_headers` is a per-test factory that creates distinct users.
"""

import os
import socket
from pathlib import Path
from tempfile import mkdtemp

import pytest

# --- Pinned before importing the app: settings read os.environ at import/boot.
_TEST_TMP_ROOT = Path(mkdtemp(prefix="carbonsnap-tests-"))
_TEST_DB_PATH = _TEST_TMP_ROOT / "test.db"

_EMPTY_ENV_FILE = _TEST_TMP_ROOT / "empty.env"
_EMPTY_ENV_FILE.write_text("", encoding="utf-8")

os.environ.update(
    {
        # Ignore the developer's local .env so results are identical here and
        # in CI; everything the suite depends on is pinned below.
        "ENV_FILE": str(_EMPTY_ENV_FILE),
        # Never touch the developer's dev database.
        "DATABASE_URL": f"sqlite:///{_TEST_DB_PATH}",
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

@pytest.fixture(scope="session")
def app():
    flask_app = create_app()
    flask_app.config.update(
        TESTING=True,
        JWT_ACCESS_TOKEN_EXPIRES=False,
        AI_DECISION_ENGINE_MODE="llm_first",
        AI_DECISION_ENGINE_VERSION="decision-engine-v2",
        AI_DECISION_CONFIDENCE_THRESHOLD=0.65,
    )
    with flask_app.app_context():
        # Fail loudly rather than destroying a real database: db_session below
        # runs drop_all() before every single test.
        bound_url = str(_db.engine.url)
        assert str(_TEST_DB_PATH) in bound_url, (
            f"Tests are bound to {bound_url!r} instead of the throwaway database "
            f"at {_TEST_DB_PATH}. Refusing to run — drop_all() would wipe it."
        )
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


# ---------------------------------------------------------------------------
# DB isolation  (function-scoped — fresh tables for every test)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def db_session(app):
    """Drop and recreate all tables before each test for full isolation."""
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield _db.session
        _db.session.remove()


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
            _db.session.commit()          # commit so HTTP requests see the row
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
