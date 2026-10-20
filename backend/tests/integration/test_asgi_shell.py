"""The ASGI app as a whole: CORS, docs, and what an unrouted request gets."""

from __future__ import annotations


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


def test_db_pool_covers_every_stream_thread(monkeypatch):
    # A chat stream holds its connection for the whole turn (the transaction
    # stays open across the LLM calls, PERFORMANCE_ISSUES #9). With a pool
    # smaller than the stream threads the extra streams waited 30 s and
    # failed: 34% of chat requests at 40 users on the default 5 + 10.
    from app.core.config import clear_settings_cache
    from app.db.session import get_engine

    monkeypatch.setenv("AI_STREAM_THREADS", "40")
    clear_settings_cache()
    get_engine.cache_clear()
    try:
        engine = get_engine()
        pool = engine.pool
        capacity = pool.size() + max(pool._max_overflow, 0)  # type: ignore[attr-defined]
        engine.dispose()
    finally:
        get_engine.cache_clear()
        clear_settings_cache()

    assert capacity >= 40


def test_wrong_method_on_a_route_is_405(client):
    for method, path in [("POST", "/api/notifications/read-all"), ("DELETE", "/api/auth/me")]:
        response = client.request(method, path)

        assert response.status_code == 405, (method, path)
        assert response.json() == {"code": 40500, "message": "Method Not Allowed", "data": {}}


def test_unknown_paths_are_a_404_envelope(client):
    # Flask used to catch these and answer with its HTML page.
    for path in ["/api/no-such-route", "/no-such-page"]:
        response = client.get(path)

        assert response.status_code == 404, path
        assert response.json() == {"code": 40400, "message": "Not Found", "data": {}}
