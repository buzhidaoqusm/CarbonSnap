"""What creating, viewing and funding a project writes besides the project.

The service swallows errors from these writes (behaviour events, topics,
preference profiles, the memory summary), so a route that cannot reach the
database for them still answers 200. These tests are what notices.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.recommendation import (
    ContentTopicAssignment,
    UserBehaviorEvent,
    UserPreferenceProfile,
)
from app.models.user import User
from tests.support.database import db


@pytest.fixture(autouse=True)
def _keyword_topics(llm_unavailable):
    # Topics come from keyword recall, then an LLM picks among the candidates.
    # With the provider down the best keyword candidate is used, which keeps
    # the topic deterministic.
    return


PROJECT = {
    "title": "Plastic bottle recycling drive",
    "description": "Collect plastic bottles for recycling.",
    "points_target": 100,
}


def _create(client, headers) -> int:
    body = {**PROJECT, "deadline_at": (datetime.now(UTC) + timedelta(days=10)).isoformat()}
    response = client.post("/api/projects", json=body, headers=headers)
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _events(user_id: int) -> list[tuple[str, str, int]]:
    rows = db.session.scalars(
        select(UserBehaviorEvent)
        .where(UserBehaviorEvent.user_id == user_id)
        .order_by(UserBehaviorEvent.id)
    )
    return [(e.domain, e.action_type, e.target_id) for e in rows]


def _profile_keys(user_id: int) -> set[str]:
    rows = db.session.scalars(
        select(UserPreferenceProfile).where(UserPreferenceProfile.user_id == user_id)
    )
    return {p.profile_key for p in rows}


def _memory_summary(user_id: int) -> dict:
    db.session.expire_all()
    raw = db.session.get(User, user_id).preferences_json
    return json.loads(raw) if raw else {}


def test_create_assigns_topics_and_records_the_creator(client, make_auth_headers):
    creator_id, headers = make_auth_headers()

    project_id = _create(client, headers)

    topics = db.session.scalars(
        select(ContentTopicAssignment.topic_id).where(
            ContentTopicAssignment.content_type == "project",
            ContentTopicAssignment.content_id == project_id,
        )
    ).all()
    assert topics == ["plastic-recycling"]
    assert _events(creator_id) == [("project", "project_create", project_id)]
    assert "plastic-recycling" in _profile_keys(creator_id)
    assert _memory_summary(creator_id)


def test_viewing_someone_elses_project_is_recorded(client, make_auth_headers):
    _, creator_headers = make_auth_headers()
    viewer_id, viewer_headers = make_auth_headers()
    project_id = _create(client, creator_headers)

    response = client.get(f"/api/projects/{project_id}", headers=viewer_headers)

    assert response.status_code == 200
    assert _events(viewer_id) == [("project", "view", project_id)]
    assert "plastic-recycling" in _profile_keys(viewer_id)
    assert _memory_summary(viewer_id)


def test_viewing_your_own_project_is_not_recorded(client, make_auth_headers):
    creator_id, headers = make_auth_headers()
    project_id = _create(client, headers)

    client.get(f"/api/projects/{project_id}", headers=headers)

    assert _events(creator_id) == [("project", "project_create", project_id)]


def test_contributing_is_recorded(client, make_auth_headers):
    _, creator_headers = make_auth_headers()
    backer_id, backer_headers = make_auth_headers(points=50)
    project_id = _create(client, creator_headers)

    response = client.post(
        f"/api/projects/{project_id}/contributions", json={"points": 20}, headers=backer_headers
    )

    assert response.status_code == 201
    assert _events(backer_id) == [("project", "project_contribute", project_id)]
    assert "plastic-recycling" in _profile_keys(backer_id)
    assert _memory_summary(backer_id)
