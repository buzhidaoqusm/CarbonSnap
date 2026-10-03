"""The ASGI shell: FastAPI answers what it has routes for, Flask the rest."""

from __future__ import annotations


def test_unmigrated_paths_reach_flask(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_fastapi_serves_its_own_docs(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "CarbonSnap API"
