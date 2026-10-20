"""Messages, status codes and response shapes of the AI memory API.

Pinned against the Flask routes before they moved to FastAPI.
"""

from __future__ import annotations

import json

import pytest

from app.core.security import create_access_token
from app.models.user import User
from tests.support.database import db

URL = "/api/ai/memory"
ITEM_FIELDS = {
    "id",
    "user_id",
    "memory_type",
    "memory_key",
    "value",
    "source_type",
    "source_message_id",
    "conversation_id",
    "status",
    "created_at",
    "updated_at",
}
ACTION_PREFERENCES = {
    "prefer_nearby_options",
    "allow_manual_area_input",
    "preferred_recycling_methods",
    "avoid_recycling_methods",
    "max_recycling_distance_km",
    "response_style",
}
CONCISE = {
    "memory_type": "response_style",
    "memory_key": "response_style",
    "value": {"value": "concise"},
}


def _assert_error(response, status: int, code: int, message: str) -> None:
    assert response.status_code == status, response.text
    assert response.json() == {"code": code, "message": message, "data": {}}


def _assert_summary(summary: dict, response_style) -> None:
    assert set(summary) == {
        "version",
        "updated_at",
        "content_interest_preferences",
        "action_preferences",
    }
    assert set(summary["content_interest_preferences"]) == {"topics", "confidence_score"}
    assert set(summary["action_preferences"]) == ACTION_PREFERENCES
    assert summary["action_preferences"]["response_style"] == response_style


def _create(client, headers, body=CONCISE) -> dict:
    response = client.post(URL, json=body, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]["item"]


@pytest.fixture(autouse=True)
def _no_llm(llm_unavailable):
    return


class TestList:
    def test_lists_active_items_with_the_summary(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()
        _create(client, headers)

        response = client.get(URL, headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 0 and body["message"] == "ok"
        [item] = body["data"]["items"]
        assert set(item) == ITEM_FIELDS
        assert item["user_id"] == user_id
        assert item["value"] == {"value": "concise"}
        assert item["source_type"] == "manual_edit"
        assert item["status"] == "active"
        _assert_summary(body["data"]["summary"], "concise")

    def test_a_deleted_user_gets_an_empty_list(self, client):
        token = create_access_token(999_999)

        response = client.get(URL, headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json()["data"]["items"] == []
        _assert_summary(response.json()["data"]["summary"], None)


class TestCreate:
    def test_returns_the_item_and_the_new_summary(self, client, make_auth_headers):
        user_id, headers = make_auth_headers()

        response = client.post(URL, json=CONCISE, headers=headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert set(data) == {"item", "summary"}
        assert set(data["item"]) == ITEM_FIELDS
        assert data["item"]["memory_key"] == "response_style"
        _assert_summary(data["summary"], "concise")
        stored = json.loads(db.session.get(User, user_id).preferences_json)
        assert stored["action_preferences"]["response_style"] == "concise"

    def test_the_same_key_replaces_the_item(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        first = _create(client, headers)

        second = _create(client, headers, {**CONCISE, "value": {"value": "detailed"}})

        assert second["id"] != first["id"]
        items = client.get(URL, headers=headers).json()["data"]["items"]
        assert [item["id"] for item in items] == [second["id"]]

    @pytest.mark.parametrize(
        ("body", "message"),
        [
            (None, "Field 'memory_type' is required."),
            ({"memory_key": "k", "value": {"a": 1}}, "Field 'memory_type' is required."),
            (
                {"memory_type": "  ", "memory_key": "k", "value": {"a": 1}},
                "Field 'memory_type' is required.",
            ),
            (
                {"memory_type": "response_style", "value": {"a": 1}},
                "Field 'memory_key' is required.",
            ),
            ({**CONCISE, "value": [1]}, "Field 'value' must be a non-empty object."),
            ({**CONCISE, "value": {}}, "Field 'value' must be a non-empty object."),
            ({**CONCISE, "value": None}, "Field 'value' must be a non-empty object."),
            ({**CONCISE, "memory_type": "nope"}, "Unsupported memory_type: nope"),
            ({**CONCISE, "memory_type": 5}, "Unsupported memory_type: 5"),
            # A null memory_type is sent on as the string "None", as in PATCH.
            ({**CONCISE, "memory_type": None}, "Unsupported memory_type: None"),
        ],
    )
    def test_rejects_an_invalid_body(self, client, make_auth_headers, body, message):
        _, headers = make_auth_headers()

        response = client.post(URL, json=body, headers=headers)

        _assert_error(response, 400, 40001, message)

    def test_a_deleted_user_is_not_found(self, client):
        # Was a 500: the insert broke the user foreign key. 404, as on the
        # other routes that need a user (auth /me, ledger).
        token = create_access_token(999_999)

        response = client.post(URL, json=CONCISE, headers={"Authorization": f"Bearer {token}"})

        _assert_error(response, 404, 40400, "User not found.")


class TestUpdate:
    def test_changes_the_value(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        item = _create(client, headers)

        response = client.patch(
            f"{URL}/{item['id']}", json={"value": {"value": "detailed"}}, headers=headers
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["item"]["id"] == item["id"]
        assert data["item"]["value"] == {"value": "detailed"}
        _assert_summary(data["summary"], "detailed")

    @pytest.mark.parametrize(
        "body",
        [None, {}, {"value": None}, {"memory_key": "  "}],
        ids=["no body", "empty", "value null", "blank key"],
    )
    def test_absent_or_blank_fields_stay_as_they_were(self, client, make_auth_headers, body):
        _, headers = make_auth_headers()
        item = _create(client, headers)

        response = client.patch(f"{URL}/{item['id']}", json=body, headers=headers)

        assert response.status_code == 200
        updated = response.json()["data"]["item"]
        assert updated["memory_key"] == "response_style"
        assert updated["value"] == {"value": "concise"}

    @pytest.mark.parametrize(
        ("body", "message"),
        [
            # A null memory_type is sent on as the string "None".
            ({"memory_type": None}, "Unsupported memory_type: None"),
            ({"memory_type": "nope"}, "Unsupported memory_type: nope"),
            ({"value": [1]}, "value must be a non-empty object."),
            ({"value": {}}, "value must be a non-empty object."),
        ],
    )
    def test_rejects_an_invalid_change(self, client, make_auth_headers, body, message):
        _, headers = make_auth_headers()
        item = _create(client, headers)

        response = client.patch(f"{URL}/{item['id']}", json=body, headers=headers)

        _assert_error(response, 400, 40001, message)

    def test_a_deleted_item_cannot_be_changed(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        item = _create(client, headers)
        client.delete(f"{URL}/{item['id']}", headers=headers)

        response = client.patch(f"{URL}/{item['id']}", json={"value": {"a": 1}}, headers=headers)

        _assert_error(response, 400, 40001, "Memory item is deleted.")

    def test_another_users_item_is_not_found(self, client, make_auth_headers):
        _, owner = make_auth_headers()
        _, other = make_auth_headers()
        item = _create(client, owner)

        response = client.patch(f"{URL}/{item['id']}", json={"value": {"a": 1}}, headers=other)

        _assert_error(response, 404, 40400, "Memory item not found.")

    def test_a_missing_item_is_not_found(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.patch(f"{URL}/999999", json={"value": {"a": 1}}, headers=headers)

        _assert_error(response, 404, 40400, "Memory item not found.")


class TestDelete:
    def test_marks_the_item_deleted(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        item = _create(client, headers)

        response = client.delete(f"{URL}/{item['id']}", headers=headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert set(data["item"]) == ITEM_FIELDS
        assert data["item"]["status"] == "deleted"
        _assert_summary(data["summary"], None)
        assert client.get(URL, headers=headers).json()["data"]["items"] == []

    def test_twice_is_not_found(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        item = _create(client, headers)
        client.delete(f"{URL}/{item['id']}", headers=headers)

        response = client.delete(f"{URL}/{item['id']}", headers=headers)

        _assert_error(response, 404, 40400, "Memory item not found.")

    def test_another_users_item_is_not_found(self, client, make_auth_headers):
        _, owner = make_auth_headers()
        _, other = make_auth_headers()
        item = _create(client, owner)

        response = client.delete(f"{URL}/{item['id']}", headers=other)

        _assert_error(response, 404, 40400, "Memory item not found.")
        assert client.get(URL, headers=owner).json()["data"]["items"]


class TestEnvelope:
    """What changes with the move: every error is an envelope."""

    def test_no_token(self, client):
        response = client.get(URL)

        assert response.status_code == 401
        assert response.json()["code"] == 40100

    def test_a_malformed_token(self, client):
        response = client.get(URL, headers={"Authorization": "Bearer not-a-token"})

        assert response.status_code == 401
        assert response.json()["code"] == 40100

    def test_an_id_that_is_not_a_number(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.patch(f"{URL}/abc", json={"value": {"a": 1}}, headers=headers)

        assert response.status_code == 400
        assert response.json()["code"] == 40000

    def test_a_body_that_is_not_json(self, client, make_auth_headers):
        # Flask read it as {} and named the first missing field.
        _, headers = make_auth_headers()

        response = client.post(
            URL, content=b"not json", headers={**headers, "Content-Type": "application/json"}
        )

        assert response.status_code == 400
        assert response.json()["code"] == 40000

    def test_another_method(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.put(URL, headers=headers)

        assert response.status_code == 405
        assert response.json()["code"] == 40500
