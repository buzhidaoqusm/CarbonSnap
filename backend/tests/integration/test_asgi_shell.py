"""The ASGI shell: FastAPI answers what it has routes for, Flask the rest."""

from __future__ import annotations


def test_unmigrated_paths_reach_flask(client):
    response = client.get("/api/forum/posts")

    assert response.status_code == 200
    assert response.json()["code"] == 0


def test_fastapi_routes_take_precedence_over_flask():
    # A Flask app that still has its own /api/health: FastAPI must answer.
    from fastapi.testclient import TestClient
    from flask import Flask

    from app.main import create_api

    legacy = Flask(__name__)
    legacy.add_url_rule("/api/health", "health", lambda: {"served_by": "flask"})

    with TestClient(create_api(legacy)) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "served_by" not in response.json()


def test_cors_preflight_is_answered_for_fastapi_routes(client):
    response = client.options(
        "/api/notifications",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_fastapi_serves_its_own_docs(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "CarbonSnap API"


def test_db_pool_covers_every_flask_thread(monkeypatch):
    # Each thread serving Flask may hold a connection for a whole chat turn
    # (the transaction stays open across the LLM calls). With a pool smaller
    # than the thread pool the extra threads waited 30 s and failed: 34% of
    # chat requests at 40 users with WSGI_THREADS=40 and the default pool of
    # 5 + 10 overflow.
    from app import create_app
    from app.core.config import clear_settings_cache
    from app.extensions.db import db

    monkeypatch.setenv("WSGI_THREADS", "40")
    clear_settings_cache()
    try:
        flask_app = create_app()
        with flask_app.app_context():
            pool = db.engine.pool
            capacity = pool.size() + max(pool._max_overflow, 0)  # type: ignore[attr-defined]
            db.engine.dispose()
    finally:
        clear_settings_cache()

    assert capacity >= 40
