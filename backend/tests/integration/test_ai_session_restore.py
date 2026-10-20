"""A paused recycling analysis survives losing the in-process session store.

The store is a dict in the worker process, so a restart (or a request served
by another process) empties it. The location step then rebuilds the session
from what the analysis stored on the user's conversation, which needs to know
who is asking.
"""

from __future__ import annotations

import json

import pytest

from app.models.ai import AIConversation
from app.services.ai import recycling_analysis_service, recycling_session_service
from tests.integration.test_ai_persistence_api import (
    _VALID_IMAGE_DATA_URL,
    _extract_sse_payloads,
)
from tests.support.database import db

SESSION_ID = "restore-after-restart"


@pytest.fixture(autouse=True)
def _fake_models(monkeypatch, llm_unavailable):
    monkeypatch.setattr(
        recycling_analysis_service,
        "_analyze_stage1",
        lambda **kwargs: {
            "waste_type": "glass bottle",
            "confidence": 0.89,
            "estimated_weight_kg": 0.25,
            "co2_saved_kg": 0.4,
            "carbon_points": 4.0,
            "recycle_suggestions": ["Separate the cap"],
            "forum_references": [],
            "requires_location_decision": True,
        },
    )

    def fake_stream_text(**kwargs):
        yield {"type": "meta", "model": "test-model"}
        yield {"type": "delta", "content": "Follow-up"}
        yield {"type": "done", "finish_reason": "stop"}

    monkeypatch.setattr(recycling_analysis_service, "stream_text", fake_stream_text)
    # The store is process state: the transaction rollback does not reset it.
    _lose_the_session_store()
    yield
    _lose_the_session_store()


def _analyze(client, headers) -> int:
    response = client.post(
        "/api/ai/analyze-image",
        json={"message": "A bottle", "image": _VALID_IMAGE_DATA_URL, "session_id": SESSION_ID},
        headers=headers,
    )
    stage = [p for p in _extract_sse_payloads(response) if p.get("type") == "stage_payload"]
    return stage[-1]["data"]["conversation_id"]


def _lose_the_session_store() -> None:
    with recycling_session_service._SESSION_LOCK:
        recycling_session_service._SESSION_STORE.clear()


def test_the_location_step_rebuilds_the_session_from_the_conversation(client, make_auth_headers):
    _, headers = make_auth_headers()
    conversation_id = _analyze(client, headers)
    _lose_the_session_store()

    response = client.post(
        "/api/ai/location-context",
        json={"session_id": SESSION_ID, "skip_nearby_search": True, "permission_state": "denied"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["conversation_id"] == conversation_id
    stored = json.loads(db.session.get(AIConversation, conversation_id).session_context_json)
    assert stored["location_state"]["skip_nearby_search"] is True


def test_another_user_cannot_pick_up_the_session(client, make_auth_headers):
    _, owner = make_auth_headers()
    _, other = make_auth_headers()
    conversation_id = _analyze(client, owner)
    _lose_the_session_store()

    response = client.post(
        "/api/ai/location-context",
        json={"session_id": SESSION_ID, "skip_nearby_search": True, "permission_state": "denied"},
        headers=other,
    )

    assert response.status_code == 200
    assert response.json()["data"]["conversation_id"] is None
    stored = json.loads(db.session.get(AIConversation, conversation_id).session_context_json)
    assert not (stored.get("location_state") or {}).get("skip_nearby_search")
