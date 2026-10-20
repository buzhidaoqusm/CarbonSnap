"""Messages, status codes and shapes of the non-streaming AI routes: chat,
location context and the conversation history.

Pinned against the Flask routes before they moved to FastAPI.
"""

from __future__ import annotations

import pytest

from app.services.ai import ai_conversation_service, ai_decision_engine
from app.services.ai.openrouter_service import OpenRouterConfigError
from tests.integration.test_ai_persistence_api import _fake_general_chat_decision

CHAT_FIELDS = {
    "assistant_message_id",
    "conversation_id",
    "conversation_title",
    "decision",
    "forum_references",
    "graph_context",
    "memory_updates",
    "model",
    "reply",
    "trace",
    "usage",
    "user_message_id",
}
CONVERSATION_FIELDS = {
    "id",
    "user_id",
    "title",
    "status",
    "current_pending_action",
    "session_context_json",
    "last_message_at",
    "created_at",
    "updated_at",
}
MESSAGE_FIELDS = {
    "id",
    "conversation_id",
    "role",
    "message_type",
    "content_text",
    "content_json",
    "image_url",
    "recycling_case",
    "related_analysis_id",
    "sequence_no",
    "trace",
    "created_at",
}
GENERIC = "The AI service is temporarily unavailable. Please try again."


def _assert_error(response, status: int, code: int, message: str) -> None:
    assert response.status_code == status, response.text
    assert response.json() == {"code": code, "message": message, "data": {}}


@pytest.fixture(autouse=True)
def _fake_chat(monkeypatch, override_settings, llm_unavailable):
    override_settings(ai_demo_replay_enabled=False)
    monkeypatch.setattr(ai_decision_engine, "decide_message", _fake_general_chat_decision)
    monkeypatch.setattr(
        ai_conversation_service,
        "chat_with_openrouter",
        lambda **kwargs: {"reply": "Reply", "model": "test-model", "usage": {}},
    )


def _chat(client, headers, **body) -> dict:
    response = client.post("/api/ai/chat", json={"message": "Hello", **body}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]


class TestChat:
    def test_replies_and_names_the_conversation(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.post("/api/ai/chat", json={"message": "Hello"}, headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 0 and body["message"] == "ok"
        assert set(body["data"]) == CHAT_FIELDS
        assert body["data"]["reply"] == "Reply"
        assert isinstance(body["data"]["conversation_id"], int)

    def test_continues_a_conversation_given_as_a_string(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        first = _chat(client, headers)

        again = _chat(client, headers, conversation_id=str(first["conversation_id"]))

        assert again["conversation_id"] == first["conversation_id"]

    @pytest.mark.parametrize(
        "extra",
        [{"conversation_id": ""}, {"history": None}, {"message": 5}, {"message": None}],
        ids=["blank conversation", "null history", "number message", "null message"],
    )
    def test_lenient_fields_start_a_chat(self, client, make_auth_headers, extra):
        # A null or a number is turned into text ("None", "5"), as before.
        _, headers = make_auth_headers()

        data = _chat(client, headers, **extra)

        assert isinstance(data["conversation_id"], int)

    @pytest.mark.parametrize(
        ("body", "message"),
        [
            (None, "Field 'message' or 'image' is required."),
            ({"message": "  "}, "Field 'message' or 'image' is required."),
            ({"message": "", "image": "  "}, "Field 'message' or 'image' is required."),
            ({"message": "x", "history": "a"}, "Field 'history' must be a list when provided."),
            (
                {"message": "x", "image": 5},
                "Field 'image' must be a base64 data URL string when provided.",
            ),
            (
                {"message": "x", "client_context": [1]},
                "Field 'client_context' must be an object when provided.",
            ),
            (
                {"message": "x", "conversation_id": "abc"},
                "Field 'conversation_id' must be an integer when provided.",
            ),
        ],
    )
    def test_rejects_an_invalid_body(self, client, make_auth_headers, body, message):
        _, headers = make_auth_headers()

        response = client.post("/api/ai/chat", json=body, headers=headers)

        _assert_error(response, 400, 40001, message)

    def test_another_users_conversation_is_not_found(self, client, make_auth_headers):
        _, owner = make_auth_headers()
        _, other = make_auth_headers()
        conversation_id = _chat(client, owner)["conversation_id"]

        response = client.post(
            "/api/ai/chat",
            json={"message": "x", "conversation_id": conversation_id},
            headers=other,
        )

        _assert_error(response, 404, 40400, f"Conversation {conversation_id} not found.")

    def test_a_missing_provider_key_is_named(self, client, make_auth_headers, monkeypatch):
        def missing_key(**kwargs):
            raise OpenRouterConfigError("OPENROUTER_API_KEY is not set")

        monkeypatch.setattr(ai_conversation_service, "chat_with_openrouter", missing_key)
        _, headers = make_auth_headers()

        response = client.post("/api/ai/chat", json={"message": "x"}, headers=headers)

        _assert_error(response, 500, 50000, "OPENROUTER_API_KEY is not set")

    def test_other_failures_stay_opaque(self, client, make_auth_headers, monkeypatch):
        def boom(**kwargs):
            raise RuntimeError("provider said something internal")

        monkeypatch.setattr(ai_conversation_service, "chat_with_openrouter", boom)
        _, headers = make_auth_headers()

        response = client.post("/api/ai/chat", json={"message": "x"}, headers=headers)

        _assert_error(response, 502, 50000, GENERIC)


class TestConversations:
    def test_lists_the_users_conversations(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        _, other = make_auth_headers()
        conversation_id = _chat(client, headers)["conversation_id"]

        data = client.get("/api/ai/conversations", headers=headers).json()["data"]

        assert set(data) == {"items", "total", "page", "per_page"}
        assert data["total"] == 1 and (data["page"], data["per_page"]) == (1, 20)
        [item] = data["items"]
        assert set(item) == CONVERSATION_FIELDS
        assert item["id"] == conversation_id and item["user_id"] == user_id
        assert client.get("/api/ai/conversations", headers=other).json()["data"]["items"] == []

    def test_paging_is_clamped(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.get("/api/ai/conversations?page=0&per_page=500", headers=headers)

        assert (response.json()["data"]["page"], response.json()["data"]["per_page"]) == (1, 100)

    def test_messages_come_with_the_conversation(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        conversation_id = _chat(client, headers)["conversation_id"]

        response = client.get(f"/api/ai/conversations/{conversation_id}/messages", headers=headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert set(data) == {"conversation", "items", "pending_recycling_case", "total"}
        assert set(data["conversation"]) == CONVERSATION_FIELDS
        assert [set(item) for item in data["items"]] == [MESSAGE_FIELDS, MESSAGE_FIELDS]
        assert [item["role"] for item in data["items"]] == ["user", "assistant"]
        assert data["total"] == 2 and data["pending_recycling_case"] is None

    @pytest.mark.parametrize("method", ["GET", "DELETE"])
    def test_another_users_conversation_is_not_found(self, client, make_auth_headers, method):
        _, owner = make_auth_headers()
        _, other = make_auth_headers()
        conversation_id = _chat(client, owner)["conversation_id"]
        url = f"/api/ai/conversations/{conversation_id}"
        if method == "GET":
            url += "/messages"

        response = client.request(method, url, headers=other)

        _assert_error(response, 404, 40400, f"Conversation {conversation_id} not found.")

    def test_delete_removes_it_once(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        conversation_id = _chat(client, headers)["conversation_id"]
        url = f"/api/ai/conversations/{conversation_id}"

        first = client.delete(url, headers=headers)
        second = client.delete(url, headers=headers)

        assert first.status_code == 200
        assert first.json()["data"] == {"deleted_conversation_id": conversation_id}
        _assert_error(second, 404, 40400, f"Conversation {conversation_id} not found.")


class TestLocationContext:
    URL = "/api/ai/location-context"

    @pytest.mark.parametrize(
        ("body", "message"),
        [
            (None, "Field 'session_id' is required."),
            ({"session_id": "  "}, "Field 'session_id' is required."),
            (
                {"session_id": "s1"},
                "Provide one of browser_location, manual_area, skip_nearby_search, "
                "or permission_state=denied.",
            ),
            (
                {"session_id": "s1", "browser_location": {"lat": "x"}},
                "Field 'browser_location' must include numeric 'lat' and 'lng' values.",
            ),
            (
                {"session_id": "s1", "browser_location": [1]},
                "Field 'browser_location' must include numeric 'lat' and 'lng' values.",
            ),
        ],
    )
    def test_rejects_an_invalid_body(self, client, make_auth_headers, body, message):
        _, headers = make_auth_headers()

        response = client.post(self.URL, json=body, headers=headers)

        _assert_error(response, 400, 40001, message)

    def test_stores_the_browser_location(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.post(
            self.URL,
            json={"session_id": "s1", "browser_location": {"lat": 1, "lng": 2}},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["session_id"] == "s1"
        assert data["location_state"]["coordinates"] == {"lat": 1.0, "lng": 2.0}
        assert data["location_state"]["permission_state"] == "granted"
        assert data["location_state"]["location_source"] == "browser"

    @pytest.mark.parametrize(
        "extra", [{"conversation_id": "abc"}, {}], ids=["bad conversation id", "none"]
    )
    def test_skipping_needs_no_conversation(self, client, make_auth_headers, extra):
        _, headers = make_auth_headers()

        response = client.post(
            self.URL,
            json={"session_id": "s2", "skip_nearby_search": True, **extra},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["data"]["location_state"]["skip_nearby_search"] is True

    def test_a_failing_lookup_stays_opaque(self, client, make_auth_headers):
        # The geocoder cannot reach the network in tests, which it reports as
        # an unexpected error rather than a MapProviderError.
        _, headers = make_auth_headers()

        response = client.post(
            self.URL, json={"session_id": "s3", "manual_area": "Dublin"}, headers=headers
        )

        _assert_error(response, 502, 50000, GENERIC)


class TestEnvelope:
    """What changes with the move: every error is an envelope."""

    def test_no_token(self, client):
        response = client.get("/api/ai/conversations")

        assert response.status_code == 401
        assert response.json()["code"] == 40100

    def test_a_malformed_token(self, client):
        response = client.post(
            "/api/ai/chat", json={"message": "x"}, headers={"Authorization": "Bearer nope"}
        )

        assert response.status_code == 401
        assert response.json()["code"] == 40100

    def test_an_id_that_is_not_a_number(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.get("/api/ai/conversations/abc/messages", headers=headers)

        assert response.status_code == 400
        assert response.json()["code"] == 40000

    def test_another_method(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.put("/api/ai/conversations", headers=headers)

        assert response.status_code == 405
        assert response.json()["code"] == 40500

    def test_paging_that_is_not_a_number(self, client, make_auth_headers):
        # Flask fell back to the defaults; PageParams answers 400, as on the
        # other lists.
        _, headers = make_auth_headers()

        response = client.get("/api/ai/conversations?page=abc", headers=headers)

        assert response.status_code == 400
        assert response.json()["code"] == 40000

    def test_a_body_that_is_not_json(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.post(
            "/api/ai/chat",
            content=b"not json",
            headers={**headers, "Content-Type": "application/json"},
        )

        assert response.status_code == 400
        assert response.json()["code"] == 40000
