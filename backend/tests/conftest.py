"""Shared pytest fixtures for all test layers.

Architecture:
- Uses an in-memory SQLite database (separate from the dev database).
- `app` fixture is session-scoped (created once).
- `db_session` fixture is function-scoped: drops and recreates all tables
  before every test, guaranteeing full data isolation without relying on
  Flask-SQLAlchemy 3.x session.bind (which was removed in 3.x).
- `client` provides a Flask test client.
- `make_auth_headers` is a per-test factory that creates distinct users.
"""

import pytest
from tempfile import mkdtemp
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions.db import db as _db
from app.models.user import User


# ---------------------------------------------------------------------------
# App fixture  (session-scoped — created once per test run)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    flask_app = create_app()
    upload_root = mkdtemp(prefix="carbonsnap-test-uploads-")
    flask_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        JWT_SECRET_KEY="test-secret",
        JWT_ACCESS_TOKEN_EXPIRES=False,
        UPLOAD_ROOT=upload_root,
        UPLOAD_URL_PREFIX="/api/uploads",
        AI_DECISION_ENGINE_MODE="llm_first",
        AI_DECISION_ENGINE_VERSION="decision-engine-v2",
        AI_DECISION_CONFIDENCE_THRESHOLD=0.65,
        AI_GRAPH_AGENT_ENABLED=False,
        AI_NEO4J_GRAPHRAG_ENABLED=False,
        NEO4J_URI="",
        NEO4J_USERNAME="",
        NEO4J_PASSWORD="",
    )
    with flask_app.app_context():
        yield flask_app


# ---------------------------------------------------------------------------
# DB isolation  (function-scoped — fresh tables for every test)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def db_session(app):
    """Drop and recreate all tables before each test for full isolation.

    SQLite in-memory DDL is extremely fast so this adds negligible overhead
    while being 100% reliable across Flask-SQLAlchemy versions.
    """
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
