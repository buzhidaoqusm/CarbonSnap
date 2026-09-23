import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.project import Project
from app.models.user import User
from app.services.recommendation import project_recommendation_service


def _make_user(username: str = "ranker", email: str = "ranker@example.com") -> User:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"{username}_{suffix}",
        email=f"{suffix}_{email}",
        password_hash=generate_password_hash("password123"),
    )
    db.session.add(user)
    db.session.flush()
    return user


def _make_project(creator_id: int, title: str) -> Project:
    project = Project(
        creator_user_id=creator_id,
        title=title,
        description=f"{title} description",
        points_target=200,
        points_raised=0,
        deadline_at=datetime.now(UTC) + timedelta(days=12),
    )
    db.session.add(project)
    db.session.flush()
    return project


class TestProjectRecommendationService:
    def test_rank_projects_for_user_prefers_matching_topic(self, monkeypatch):
        creator = _make_user("creator", "creator@example.com")
        user = _make_user("viewer", "viewer@example.com")
        matching = _make_project(creator.id, "Riverside cleanup station")
        non_matching = _make_project(creator.id, "Battery swap shelf")

        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.has_sufficient_history",
            lambda user_id: True,
        )
        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.get_profile_snapshot",
            lambda user_id: {"community-cleanup": 0.9, "battery-recycling": 0.1},
        )
        monkeypatch.setattr(
            project_recommendation_service.preference_profile_repository,
            "list_content_topic_assignments_for_content_ids",
            lambda **kwargs: {
                matching.id: [SimpleNamespace(topic_id="community-cleanup", confidence_score=1.0)],
                non_matching.id: [
                    SimpleNamespace(topic_id="battery-recycling", confidence_score=1.0)
                ],
            },
        )
        monkeypatch.setattr(
            project_recommendation_service.behavior_event_repository,
            "list_behavior_target_ids_for_user",
            lambda *args, **kwargs: set(),
        )
        monkeypatch.setattr(
            project_recommendation_service.behavior_event_repository,
            "list_recent_topic_exposure_counts_for_user",
            lambda *args, **kwargs: {},
        )
        monkeypatch.setattr(
            project_recommendation_service.project_repository,
            "list_contribution_counts_for_project_ids",
            lambda project_ids: {},
        )
        monkeypatch.setattr(
            project_recommendation_service.project_repository,
            "list_unique_contributor_counts_for_project_ids",
            lambda project_ids: {},
        )

        ranked = project_recommendation_service.rank_projects_for_user(
            projects=[non_matching, matching],
            user_id=user.id,
        )

        assert ranked[0].id == matching.id

    def test_rank_projects_inserts_alternate_topic_before_third_consecutive_match(
        self, monkeypatch
    ):
        creator = _make_user("diversity-owner", "diversity-owner@example.com")
        viewer = _make_user("diversity-viewer", "diversity-viewer@example.com")
        cleanup_1 = _make_project(creator.id, "Cleanup A")
        cleanup_2 = _make_project(creator.id, "Cleanup B")
        cleanup_3 = _make_project(creator.id, "Cleanup C")
        alternate = _make_project(creator.id, "Battery station")

        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.has_sufficient_history",
            lambda user_id: True,
        )
        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.get_profile_snapshot",
            lambda user_id: {"community-cleanup": 0.8, "battery-recycling": 0.1},
        )
        monkeypatch.setattr(
            project_recommendation_service.preference_profile_repository,
            "list_content_topic_assignments_for_content_ids",
            lambda **kwargs: {
                cleanup_1.id: [SimpleNamespace(topic_id="community-cleanup", confidence_score=0.9)],
                cleanup_2.id: [SimpleNamespace(topic_id="community-cleanup", confidence_score=0.8)],
                cleanup_3.id: [SimpleNamespace(topic_id="community-cleanup", confidence_score=0.7)],
                alternate.id: [
                    SimpleNamespace(topic_id="battery-recycling", confidence_score=0.95)
                ],
            },
        )
        monkeypatch.setattr(
            project_recommendation_service.behavior_event_repository,
            "list_behavior_target_ids_for_user",
            lambda *args, **kwargs: set(),
        )
        monkeypatch.setattr(
            project_recommendation_service.behavior_event_repository,
            "list_recent_topic_exposure_counts_for_user",
            lambda *args, **kwargs: {"community-cleanup": 3},
        )
        monkeypatch.setattr(
            project_recommendation_service.project_repository,
            "list_contribution_counts_for_project_ids",
            lambda project_ids: {},
        )
        monkeypatch.setattr(
            project_recommendation_service.project_repository,
            "list_unique_contributor_counts_for_project_ids",
            lambda project_ids: {},
        )

        ranked = project_recommendation_service.rank_projects_for_user(
            projects=[cleanup_3, alternate, cleanup_2, cleanup_1],
            user_id=viewer.id,
        )

        assert [project.id for project in ranked[:3]] == [cleanup_1.id, cleanup_2.id, alternate.id]
