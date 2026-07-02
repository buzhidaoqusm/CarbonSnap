import json
from datetime import datetime, timedelta, timezone


def _post_json(client, url, data, headers=None):
    return client.post(url, data=json.dumps(data), content_type="application/json", headers=headers)


def _future_deadline(days: int = 10) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _create_project(client, headers, **overrides):
    payload = {
        "title": "Community Rain Garden",
        "description": "A compact rain garden beside the library.",
        "points_target": 250,
        "deadline_at": _future_deadline(),
    }
    payload.update(overrides)
    response = _post_json(client, "/api/projects", payload, headers)
    assert response.status_code == 201
    return response.get_json()["data"]


def _get_notifications(client, headers):
    response = client.get("/api/notifications", headers=headers)
    assert response.status_code == 200
    return response.get_json()["data"]["items"]


class TestProjectListApi:
    def test_anonymous_user_can_list_projects(self, client, make_auth_headers):
        _, headers = make_auth_headers()
        _create_project(client, headers)

        response = client.get("/api/projects")

        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["total"] == 1
        assert data["summary"]["fundraising_count"] == 1

    def test_authenticated_list_includes_own_projects(self, client, make_auth_headers):
        _, creator_headers = make_auth_headers()
        _, other_headers = make_auth_headers()
        own_project = _create_project(client, creator_headers, title="My project")
        other_project = _create_project(client, other_headers, title="Other project")

        response = client.get("/api/projects", headers=creator_headers)

        assert response.status_code == 200
        ids = [item["id"] for item in response.get_json()["data"]["items"]]
        assert ids[0] == own_project["id"]
        assert own_project["id"] in ids
        assert other_project["id"] in ids


class TestCreateProjectApi:
    def test_authenticated_user_can_create_project(self, client, make_auth_headers):
        _, headers = make_auth_headers()

        response = _post_json(
            client,
            "/api/projects",
            {
                "title": "Repair Cafe",
                "description": "Monthly community fix-it table.",
                "points_target": 180,
                "deadline_at": _future_deadline(),
            },
            headers,
        )

        assert response.status_code == 201
        data = response.get_json()["data"]
        assert data["title"] == "Repair Cafe"
        assert data["points_target"] == 180

    def test_unauthenticated_user_cannot_create_project(self, client):
        response = _post_json(
            client,
            "/api/projects",
            {
                "title": "Repair Cafe",
                "points_target": 180,
                "deadline_at": _future_deadline(),
            },
        )
        assert response.status_code == 401


class TestProjectDetailApi:
    def test_returns_project_detail_with_recent_contributions(self, client, make_auth_headers):
        _, creator_headers = make_auth_headers()
        _, supporter_headers = make_auth_headers(points=200)
        project = _create_project(client, creator_headers)
        contribute = _post_json(
            client,
            f"/api/projects/{project['id']}/contributions",
            {"points": 40},
            supporter_headers,
        )
        assert contribute.status_code == 201

        response = client.get(f"/api/projects/{project['id']}")

        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["id"] == project["id"]
        assert len(data["recent_contributions"]) == 1
        assert data["recent_contributions"][0]["points"] == 40


class TestProjectContributionApi:
    def test_authenticated_user_can_contribute_points(self, client, make_auth_headers):
        _, creator_headers = make_auth_headers()
        _, supporter_headers = make_auth_headers(points=300)
        project = _create_project(client, creator_headers, points_target=200)

        response = _post_json(
            client,
            f"/api/projects/{project['id']}/contributions",
            {"points": 50},
            supporter_headers,
        )

        assert response.status_code == 201
        data = response.get_json()["data"]
        assert data["project"]["points_raised"] == 50
        assert data["viewer_current_points"] == 250

    def test_contribution_requires_authentication(self, client, make_auth_headers):
        _, creator_headers = make_auth_headers()
        project = _create_project(client, creator_headers)

        response = _post_json(
            client,
            f"/api/projects/{project['id']}/contributions",
            {"points": 20},
        )

        assert response.status_code == 401

    def test_insufficient_points_returns_402(self, client, make_auth_headers):
        _, creator_headers = make_auth_headers()
        _, supporter_headers = make_auth_headers(points=10)
        project = _create_project(client, creator_headers, points_target=200)

        response = _post_json(
            client,
            f"/api/projects/{project['id']}/contributions",
            {"points": 30},
            supporter_headers,
        )

        assert response.status_code == 402

    def test_cannot_overfund_project(self, client, make_auth_headers):
        _, creator_headers = make_auth_headers()
        _, supporter_headers = make_auth_headers(points=300)
        project = _create_project(client, creator_headers, points_target=50)

        response = _post_json(
            client,
            f"/api/projects/{project['id']}/contributions",
            {"points": 80},
            supporter_headers,
        )

        assert response.status_code == 409

    def test_completion_notifies_creator_and_distinct_contributors(self, client, make_auth_headers):
        _, creator_headers = make_auth_headers(username="creator", points=300)
        _, supporter_headers = make_auth_headers(username="supporter", points=300)
        _, finisher_headers = make_auth_headers(username="finisher", points=300)
        project = _create_project(client, creator_headers, points_target=60)

        first = _post_json(
            client,
            f"/api/projects/{project['id']}/contributions",
            {"points": 10},
            creator_headers,
        )
        assert first.status_code == 201

        second = _post_json(
            client,
            f"/api/projects/{project['id']}/contributions",
            {"points": 15},
            supporter_headers,
        )
        assert second.status_code == 201

        third = _post_json(
            client,
            f"/api/projects/{project['id']}/contributions",
            {"points": 5},
            supporter_headers,
        )
        assert third.status_code == 201

        final = _post_json(
            client,
            f"/api/projects/{project['id']}/contributions",
            {"points": 30},
            finisher_headers,
        )
        assert final.status_code == 201
        assert final.get_json()["data"]["project"]["status"] == "completed"

        creator_notifications = _get_notifications(client, creator_headers)
        supporter_notifications = _get_notifications(client, supporter_headers)
        finisher_notifications = _get_notifications(client, finisher_headers)

        assert len(creator_notifications) == 1
        assert len(supporter_notifications) == 1
        assert len(finisher_notifications) == 1
        assert creator_notifications[0]["event_type"] == "project_completed"
        assert supporter_notifications[0]["event_type"] == "project_completed"
        assert finisher_notifications[0]["event_type"] == "project_completed"
