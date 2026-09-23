from datetime import UTC, datetime, timedelta

import pytest

from app.extensions.db import db
from app.models.notification import Notification
from app.models.project import Project
from app.models.user import User
from app.services.project import project_service
from app.services.project.project_service import ProjectError


def _future_deadline(days: int = 10) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def test_create_project_returns_serialized_project(app, make_user):
    creator_id, _ = make_user(points=100)

    with app.app_context():
        result = project_service.create_project(
            creator_user_id=creator_id,
            title="Neighborhood Compost Corner",
            description="A small shared composting station for our block.",
            cover_image_url=None,
            points_target=240,
            deadline_at=_future_deadline(),
        )

        assert result["title"] == "Neighborhood Compost Corner"
        assert result["points_target"] == 240
        assert result["points_raised"] == 0
        assert result["progress_ratio"] == 0.0
        assert result["status"] == "fundraising"


def test_contribute_to_project_deducts_points_and_marks_completed(app, make_user):
    creator_id, _ = make_user(username="creator", email="creator@example.com", points=0)
    supporter_id, _ = make_user(username="supporter", email="supporter@example.com", points=180)

    with app.app_context():
        created = project_service.create_project(
            creator_user_id=creator_id,
            title="Park Tool Library",
            description="Shared repair tools for the neighborhood.",
            cover_image_url=None,
            points_target=120,
            deadline_at=_future_deadline(),
        )

        contribution = project_service.contribute_to_project(
            project_id=created["id"],
            user_id=supporter_id,
            points=120,
        )

        project = db.session.get(Project, created["id"])
        supporter = db.session.get(User, supporter_id)
        notifications = db.session.query(Notification).all()

        assert contribution["project"]["status"] == "completed"
        assert contribution["project"]["points_raised"] == 120
        assert contribution["viewer_current_points"] == 60
        assert project.status == "completed"
        assert project.points_raised == 120
        assert supporter.current_points == 60
        # Completion notifies the creator and every distinct contributor.
        assert {n.event_type for n in notifications} == {"project_completed"}
        assert {n.recipient_user_id for n in notifications} == {creator_id, supporter_id}


def test_contribute_to_project_rejects_expired_project(app, make_user):
    creator_id, _ = make_user(
        username="creator-expired", email="creator-expired@example.com", points=0
    )
    supporter_id, _ = make_user(
        username="supporter-expired",
        email="supporter-expired@example.com",
        points=100,
    )

    with app.app_context():
        project = Project(
            creator_user_id=creator_id,
            title="Expired project",
            description="Too late",
            points_target=80,
            deadline_at=datetime.now(UTC) - timedelta(days=1),
        )
        db.session.add(project)
        db.session.commit()

        with pytest.raises(ProjectError, match="passed its deadline"):
            project_service.contribute_to_project(
                project_id=project.id,
                user_id=supporter_id,
                points=20,
            )


def test_contribute_to_project_rejects_points_above_remaining(app, make_user):
    creator_id, _ = make_user(
        username="creator-remaining", email="creator-remaining@example.com", points=0
    )
    supporter_id, _ = make_user(
        username="supporter-remaining",
        email="supporter-remaining@example.com",
        points=500,
    )

    with app.app_context():
        created = project_service.create_project(
            creator_user_id=creator_id,
            title="Bike Fix Day",
            description="Community repair workshop.",
            cover_image_url=None,
            points_target=100,
            deadline_at=_future_deadline(),
        )
        db.session.get(Project, created["id"]).points_raised = 80
        db.session.commit()

        with pytest.raises(ProjectError, match="Maximum allowed is 20"):
            project_service.contribute_to_project(
                project_id=created["id"],
                user_id=supporter_id,
                points=30,
            )
