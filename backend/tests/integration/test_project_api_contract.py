"""Validation, errors, paging and response shapes of the project API.

Pinned against the Flask routes before they moved to FastAPI and kept
unchanged across the move.
"""

from __future__ import annotations

import base64
import datetime as dt
import re

import jwt as pyjwt
import pytest

from app.extensions.db import db
from app.models.project import Project

PNG_DATA_URL = (
    "data:image/png;base64,"
    + base64.b64encode(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082"
        )
    ).decode()
)
NAIVE_ISO = r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?"
PROJECT_FIELDS = {
    "id",
    "creator_user_id",
    "creator_username",
    "title",
    "description",
    "cover_image_url",
    "points_target",
    "points_raised",
    "points_remaining",
    "progress_ratio",
    "status",
    "deadline_at",
    "created_at",
    "days_left",
    "is_expired",
    "contribution_count",
    "contributor_count",
}


def _future(days: int = 10) -> str:
    return (dt.datetime.now(dt.UTC) + dt.timedelta(days=days)).isoformat()


def _body(**overrides):
    body = {"title": "Rain garden", "points_target": 100, "deadline_at": _future()}
    body.update(overrides)
    return body


def _create(client, headers, **overrides) -> dict:
    response = client.post("/api/projects", json=_body(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _contribute(client, headers, project_id, points):
    return client.post(
        f"/api/projects/{project_id}/contributions", json={"points": points}, headers=headers
    )


def _assert_error(response, status: int, code: int, message: str) -> None:
    assert response.status_code == status, response.text
    assert response.json() == {"code": code, "message": message, "data": {}}


# ---------------------------------------------------------------------------
# POST /api/projects
# ---------------------------------------------------------------------------


class TestCreate:
    def test_response_shape(self, client, make_auth_headers):
        creator_id, headers = make_auth_headers(username="maker")

        data = _create(client, headers, description="  By the library.  ", points_target=150)

        assert set(data) == PROJECT_FIELDS
        assert data["creator_user_id"] == creator_id
        assert data["creator_username"] == "maker"
        assert data["description"] == "By the library."
        assert data["cover_image_url"] is None
        assert (data["points_target"], data["points_raised"], data["points_remaining"]) == (
            150,
            0,
            150,
        )
        assert data["progress_ratio"] == 0.0
        assert data["status"] == "fundraising"
        assert data["days_left"] == 10
        assert data["is_expired"] is False
        assert (data["contribution_count"], data["contributor_count"]) == (0, 0)
        assert re.fullmatch(NAIVE_ISO, data["created_at"])
        assert re.fullmatch(NAIVE_ISO, data["deadline_at"])

    @pytest.mark.parametrize(
        ("overrides", "message"),
        [
            ({"title": "   "}, "Field 'title' is required."),
            ({"points_target": "lots"}, "'points_target' must be an integer."),
            ({"points_target": 0}, "'points_target' must be a positive integer."),
            ({"deadline_at": ""}, "Field 'deadline_at' is required."),
            ({"deadline_at": "next week"}, "Field 'deadline_at' must be a valid ISO datetime."),
            ({"deadline_at": _future(-1)}, "Field 'deadline_at' must be in the future."),
        ],
        ids=["title", "target-not-int", "target-zero", "no-deadline", "bad-deadline", "past"],
    )
    def test_validation(self, client, make_auth_headers, overrides, message):
        _, headers = make_auth_headers()

        response = client.post("/api/projects", json=_body(**overrides), headers=headers)

        _assert_error(response, 400, 40001, message)

    def test_numeric_string_target_is_accepted(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        assert _create(client, headers, points_target="120")["points_target"] == 120


# ---------------------------------------------------------------------------
# POST /api/projects/uploads
# ---------------------------------------------------------------------------


class TestUpload:
    def test_stores_image(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.post(
            "/api/projects/uploads", json={"image": PNG_DATA_URL}, headers=headers
        )

        assert response.status_code == 201
        assert re.fullmatch(
            r"/api/uploads/project/[0-9a-f]{32}\.png", response.json()["data"]["url"]
        )

    @pytest.mark.parametrize("body", [{}, {"image": 42}], ids=["missing", "not-a-string"])
    def test_image_must_be_a_string(self, client, make_auth_headers, body):
        _, headers = make_auth_headers()

        response = client.post("/api/projects/uploads", json=body, headers=headers)

        _assert_error(response, 400, 40001, "Field 'image' must be a base64 data URL string.")

    def test_image_must_be_a_data_url(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = client.post("/api/projects/uploads", json={"image": "x"}, headers=headers)

        _assert_error(response, 400, 40001, "Field 'image' must be a base64 image data URL.")

    def test_requires_login(self, client):
        assert client.post("/api/projects/uploads", json={"image": PNG_DATA_URL}).status_code == 401


# ---------------------------------------------------------------------------
# GET /api/projects, GET /api/projects/<id>
# ---------------------------------------------------------------------------


class TestRead:
    def test_list_paging_defaults_and_clamping(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        _create(client, headers)

        default = client.get("/api/projects").json()["data"]
        clamped = client.get("/api/projects?page=0&per_page=500").json()["data"]

        assert (default["page"], default["per_page"]) == (1, 12)
        assert (clamped["page"], clamped["per_page"]) == (1, 100)
        assert set(default) == {"items", "total", "page", "per_page", "summary"}
        assert default["summary"] == {
            "fundraising_count": 1,
            "completed_count": 0,
            "points_raised_total": 0,
        }
        assert set(default["items"][0]) == PROJECT_FIELDS

    def test_detail_includes_recent_contributions(self, client, make_auth_headers):
        _, creator = make_auth_headers()
        backer_id, backer = make_auth_headers(username="backer", points=50)
        project = _create(client, creator)
        _contribute(client, backer, project["id"], 20)

        data = client.get(f"/api/projects/{project['id']}").json()["data"]

        assert set(data) == PROJECT_FIELDS | {"recent_contributions"}
        (entry,) = data["recent_contributions"]
        assert set(entry) == {
            "id",
            "project_id",
            "user_id",
            "contributor_username",
            "points",
            "created_at",
        }
        assert (entry["user_id"], entry["contributor_username"], entry["points"]) == (
            backer_id,
            "backer",
            20,
        )

    def test_detail_not_found(self, client):
        _assert_error(client.get("/api/projects/999999"), 404, 40400, "Project not found.")


# ---------------------------------------------------------------------------
# POST /api/projects/<id>/contributions
# ---------------------------------------------------------------------------


class TestContribute:
    def test_response_shape(self, client, make_auth_headers):
        _, creator = make_auth_headers()
        _, backer = make_auth_headers(points=50)
        project = _create(client, creator)

        response = _contribute(client, backer, project["id"], 20)

        assert response.status_code == 201
        data = response.json()["data"]
        assert set(data) == {"project", "contribution", "viewer_current_points"}
        assert data["viewer_current_points"] == 30
        assert data["project"]["points_raised"] == 20
        assert data["project"]["progress_ratio"] == 0.2
        assert data["contribution"]["points"] == 20

    @pytest.mark.parametrize(
        ("points", "message"),
        [
            ("many", "'points' must be an integer."),
            (0, "'points' must be a positive integer."),
        ],
    )
    def test_points_validation(self, client, make_auth_headers, points, message):
        _, creator = make_auth_headers()
        _, backer = make_auth_headers(points=50)
        project = _create(client, creator)

        _assert_error(_contribute(client, backer, project["id"], points), 400, 40001, message)

    def test_unknown_project(self, client, make_auth_headers):
        _, backer = make_auth_headers(points=50)

        _assert_error(_contribute(client, backer, 999999, 5), 404, 40400, "Project not found.")

    def test_exceeding_the_remaining_target(self, client, make_auth_headers):
        _, creator = make_auth_headers()
        _, backer = make_auth_headers(points=500)
        project = _create(client, creator, points_target=100)
        _contribute(client, backer, project["id"], 70)

        _assert_error(
            _contribute(client, backer, project["id"], 40),
            409,
            40903,
            "Contribution exceeds the remaining target. Maximum allowed is 30 points.",
        )

    def test_completed_project(self, client, make_auth_headers):
        _, creator = make_auth_headers()
        _, backer = make_auth_headers(points=500)
        project = _create(client, creator, points_target=100)
        assert (
            _contribute(client, backer, project["id"], 100).json()["data"]["project"]["status"]
            == "completed"
        )

        _assert_error(
            _contribute(client, backer, project["id"], 1),
            409,
            40901,
            "This project is already fully funded.",
        )

    def test_expired_project(self, app, client, make_auth_headers):
        _, creator = make_auth_headers()
        _, backer = make_auth_headers(points=500)
        project = _create(client, creator)
        with app.app_context():
            db.session.get(Project, project["id"]).deadline_at = dt.datetime.now(
                dt.UTC
            ) - dt.timedelta(days=1)
            db.session.commit()

        _assert_error(
            _contribute(client, backer, project["id"], 5),
            409,
            40902,
            "This project has passed its deadline.",
        )

    def test_insufficient_points(self, client, make_auth_headers):
        _, creator = make_auth_headers()
        _, backer = make_auth_headers(points=5)
        project = _create(client, creator)

        _assert_error(
            _contribute(client, backer, project["id"], 10),
            402,
            40200,
            "Insufficient points for this contribution.",
        )


# ---------------------------------------------------------------------------
# Tokens on routes where login is optional
# ---------------------------------------------------------------------------


class TestOptionalLogin:
    @pytest.mark.parametrize("path", ["/api/projects", "/api/projects/{id}"])
    def test_bad_token_is_a_401_envelope(self, client, make_auth_headers, path):
        # A token that is sent must be valid, even where none is required.
        _, headers = make_auth_headers()
        project = _create(client, headers)

        response = client.get(
            path.format(id=project["id"]), headers={"Authorization": "Bearer garbage"}
        )

        assert response.status_code == 401
        assert response.json()["code"] == 40100

    @pytest.mark.parametrize("path", ["/api/projects", "/api/projects/{id}"])
    def test_legacy_username_token(self, app, client, make_user, make_auth_headers, path):
        _, headers = make_auth_headers()
        project = _create(client, headers)
        make_user(username="legacy", email="legacy@example.com")
        token = pyjwt.encode(
            {
                "sub": "legacy",
                "type": "access",
                "exp": dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
            },
            app.config["JWT_SECRET_KEY"],
            algorithm="HS256",
        )

        response = client.get(
            path.format(id=project["id"]), headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
