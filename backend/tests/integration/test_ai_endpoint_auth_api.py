"""Every AI endpoint must require a token.

These endpoints burn provider credits, so an unauthenticated caller must not be
able to reach them. /ai/analyze-image, /ai/location-context and /ai/chat/resume
were missing the decorator; this is the regression guard.
"""

from __future__ import annotations

import json

import pytest

PROTECTED_ENDPOINTS = [
    ("/api/ai/chat", {"message": "hello"}),
    ("/api/ai/chat/stream", {"message": "hello"}),
    ("/api/ai/analyze-image", {"message": "what is this?", "image": "data:image/png;base64,AAAA"}),
    ("/api/ai/location-context", {"session_id": "abc", "permission_state": "denied"}),
    ("/api/ai/chat/resume", {"session_id": "abc"}),
    ("/api/ai/audit-recycling", {"recycling_case_id": 1, "image": "data:image/png;base64,AAAA"}),
]


@pytest.mark.parametrize(("path", "payload"), PROTECTED_ENDPOINTS)
def test_ai_endpoint_rejects_anonymous_request(client, path, payload):
    response = client.post(
        path,
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_ai_conversation_endpoints_reject_anonymous_request(client):
    assert client.get("/api/ai/conversations").status_code == 401
    assert client.get("/api/ai/conversations/1/messages").status_code == 401
    assert client.delete("/api/ai/conversations/1").status_code == 401
    assert client.get("/api/ai/memory").status_code == 401
