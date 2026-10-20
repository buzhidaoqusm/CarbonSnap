"""The wire format of the streaming AI routes.

Pinned against the Flask routes before they moved to FastAPI: the frames
(the heartbeat byte for byte, then one JSON event per frame), the headers,
the error frames, and the 400s that come back before a stream starts.
"""

from __future__ import annotations

import json

import pytest

from app.services.ai import recycling_analysis_service
from app.services.ai.openrouter_service import OpenRouterConfigError

HEARTBEAT = b'data: {"type":"heartbeat","stream_stage":"accepted"}\n\n'
GENERIC = "The AI service is temporarily unavailable. Please try again."


@pytest.fixture(autouse=True)
def _no_llm(llm_unavailable):
    return


def _frames(response) -> list[dict]:
    body = response.content
    assert body.startswith(HEARTBEAT), body[:80]
    assert body.endswith(b"\n\n")
    chunks = body[len(HEARTBEAT) :].split(b"\n\n")[:-1]
    assert all(chunk.startswith(b"data: ") for chunk in chunks), chunks
    return [json.loads(chunk[len(b"data: ") :]) for chunk in chunks]


def _failing_analysis(monkeypatch, exc: Exception) -> None:
    def fail(**kwargs):
        raise exc

    monkeypatch.setattr(recycling_analysis_service, "_analyze_stage1", fail)


class TestFrames:
    def test_headers_turn_off_caching_and_proxy_buffering(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.post("/api/ai/chat/resume", json={"session_id": "nope"}, headers=headers)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["x-accel-buffering"] == "no"

    def test_events_follow_the_heartbeat_as_json(self, client, make_auth_headers, monkeypatch):
        _failing_analysis(monkeypatch, RuntimeError("internal detail"))
        _, headers = make_auth_headers()

        response = client.post("/api/ai/analyze-image", json={"message": "x"}, headers=headers)

        events = _frames(response)
        assert [event["type"] for event in events] == ["meta", "stage_start", "error"]
        # Non-ASCII stays as it is (ensure_ascii=False), as the frontend reads it.
        assert b"\\u" not in response.content


class TestErrorFrames:
    def test_a_missing_provider_key_is_named(self, client, make_auth_headers, monkeypatch):
        _failing_analysis(monkeypatch, OpenRouterConfigError("OPENROUTER_API_KEY is not set"))
        _, headers = make_auth_headers()

        events = _frames(
            client.post("/api/ai/analyze-image", json={"message": "x"}, headers=headers)
        )

        assert events[-1] == {
            "type": "error",
            "code": 50000,
            "message": "OPENROUTER_API_KEY is not set",
        }

    def test_other_failures_stay_opaque(self, client, make_auth_headers, monkeypatch):
        _failing_analysis(monkeypatch, RuntimeError("internal detail"))
        _, headers = make_auth_headers()

        response = client.post("/api/ai/analyze-image", json={"message": "x"}, headers=headers)

        assert _frames(response)[-1] == {"type": "error", "code": 50000, "message": GENERIC}
        assert b"internal detail" not in response.content

    @pytest.mark.parametrize(
        ("url", "body"),
        [
            ("/api/ai/chat/resume", {"session_id": "nope"}),
            (
                "/api/ai/audit-recycling",
                {"image": "data:image/png;base64,AAAA", "conversation_id": 999999},
            ),
        ],
        ids=["unknown session", "unknown conversation"],
    )
    def test_a_missing_target_ends_the_stream_with_an_error(
        self, client, make_auth_headers, url, body
    ):
        _, headers = make_auth_headers()

        events = _frames(client.post(url, json=body, headers=headers))

        assert events == [{"type": "error", "code": 50000, "message": GENERIC}]


class TestBeforeTheStream:
    @pytest.mark.parametrize(
        ("url", "body", "message"),
        [
            ("/api/ai/chat/stream", {}, "Field 'message' or 'image' is required."),
            (
                "/api/ai/chat/stream",
                {"message": "x", "history": "a"},
                "Field 'history' must be a list when provided.",
            ),
            (
                "/api/ai/analyze-image",
                {"image": 5},
                "Field 'image' must be a base64 data URL string when provided.",
            ),
            (
                "/api/ai/analyze-image",
                {"conversation_id": "x"},
                "Field 'conversation_id' must be an integer when provided.",
            ),
            ("/api/ai/chat/resume", {}, "Field 'session_id' is required."),
            ("/api/ai/audit-recycling", {}, "Field 'image' is required."),
            (
                "/api/ai/audit-recycling",
                {"image": 5},
                "Field 'image' must be a base64 data URL string when provided.",
            ),
            ("/api/ai/audit-recycling", {"image": "d"}, "Field 'conversation_id' is required."),
            (
                "/api/ai/audit-recycling",
                {"image": "d", "conversation_id": 1, "recycling_case_id": "x"},
                "Field 'recycling_case_id' must be an integer when provided.",
            ),
        ],
    )
    def test_an_invalid_body_is_a_json_400(self, client, make_auth_headers, url, body, message):
        _, headers = make_auth_headers()

        response = client.post(url, json=body, headers=headers)

        assert response.status_code == 400
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"code": 40001, "message": message, "data": {}}


class TestEnvelope:
    """What changes with the move: auth failures and wrong methods are envelopes."""

    @pytest.mark.parametrize(
        "url",
        [
            "/api/ai/chat/stream",
            "/api/ai/analyze-image",
            "/api/ai/chat/resume",
            "/api/ai/audit-recycling",
        ],
    )
    def test_no_token(self, client, url):
        response = client.post(url, json={})

        assert response.status_code == 401
        assert response.json()["code"] == 40100

    def test_another_method(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.get("/api/ai/chat/stream", headers=headers)

        assert response.status_code == 405
        assert response.json()["code"] == 40500
