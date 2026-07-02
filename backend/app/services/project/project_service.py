from __future__ import annotations

from datetime import datetime, timezone
from math import ceil

from app.extensions.db import db
from app.repositories.ledger.ledger_repository import InsufficientPointsError, spend_points
from app.repositories.project import project_repository
from app.models.user import User
from app.services.ai import memory_service
from app.services.notification import notification_service
from app.services.recommendation import behavior_event_service, preference_profile_service, topic_mapping_service
from app.services.recommendation.project_recommendation_service import rank_projects_for_user


class ProjectError(Exception):
    def __init__(self, message: str, code: int = 40001, http_status: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_deadline(deadline_at: str | None) -> datetime:
    raw = str(deadline_at or "").strip()
    if not raw:
        raise ProjectError("Field 'deadline_at' is required.")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProjectError("Field 'deadline_at' must be a valid ISO datetime.") from exc
    return _ensure_aware_utc(parsed)


def _is_expired(project) -> bool:
    deadline = _ensure_aware_utc(project.deadline_at)
    if deadline is None:
        return False
    return _utc_now() > deadline and str(project.status or "") != "completed"


def _days_left(project) -> int:
    deadline = _ensure_aware_utc(project.deadline_at)
    if deadline is None:
        return 0
    remaining_seconds = (deadline - _utc_now()).total_seconds()
    if remaining_seconds <= 0:
        return 0
    return int(ceil(remaining_seconds / 86400.0))


def _serialize_contribution(contribution, contributor_username: str) -> dict:
    return {
        "id": contribution.id,
        "project_id": contribution.project_id,
        "user_id": contribution.user_id,
        "contributor_username": contributor_username,
        "points": contribution.points,
        "created_at": contribution.created_at.isoformat(),
    }


def _serialize_project(
    project,
    *,
    creator_username: str | None = None,
    include_recent_contributions: bool = False,
    contribution_count: int | None = None,
    contributor_count: int | None = None,
) -> dict:
    points_target = max(int(project.points_target or 0), 1)
    points_raised = max(int(project.points_raised or 0), 0)
    progress_ratio = min(round(points_raised / points_target, 4), 1.0)
    payload = {
        "id": project.id,
        "creator_user_id": project.creator_user_id,
        "creator_username": creator_username or f"User {project.creator_user_id}",
        "title": project.title,
        "description": project.description,
        "cover_image_url": project.cover_image_url or None,
        "points_target": points_target,
        "points_raised": points_raised,
        "points_remaining": max(points_target - points_raised, 0),
        "progress_ratio": progress_ratio,
        "status": project.status,
        "deadline_at": project.deadline_at.isoformat(),
        "created_at": project.created_at.isoformat(),
        "days_left": _days_left(project),
        "is_expired": _is_expired(project),
        "contribution_count": int(contribution_count or 0),
        "contributor_count": int(contributor_count or 0),
    }
    if include_recent_contributions:
        payload["recent_contributions"] = [
            _serialize_contribution(contribution, username)
            for contribution, username in project_repository.list_recent_contributions(project.id, limit=12)
        ]
    return payload


def _refresh_recommendation_state(user_id: int) -> None:
    preference_profile_service.recompute_user_preference_profiles(user_id)
    memory_service.rebuild_user_preferences_summary(user_id)


def create_project(
    *,
    creator_user_id: int,
    title: str,
    description: str | None,
    cover_image_url: str | None,
    points_target: int,
    deadline_at: str,
) -> dict:
    normalized_title = str(title or "").strip()
    if not normalized_title:
        raise ProjectError("Field 'title' is required.")
    if int(points_target or 0) <= 0:
        raise ProjectError("'points_target' must be a positive integer.")
    parsed_deadline = _parse_deadline(deadline_at)
    if parsed_deadline <= _utc_now():
        raise ProjectError("Field 'deadline_at' must be in the future.")

    normalized_cover = (str(cover_image_url).strip() or None) if cover_image_url else None

    project = project_repository.create_project(
        creator_user_id=creator_user_id,
        title=normalized_title,
        description=(str(description).strip() or None) if description is not None else None,
        cover_image_url=normalized_cover,
        points_target=int(points_target),
        deadline_at=parsed_deadline,
    )
    db.session.commit()
    topic_mapping_service.refresh_project_topics(
        project_id=project.id,
        title=project.title,
        description=project.description,
    )
    try:
        behavior_event_service.record_project_create(user_id=creator_user_id, project_id=project.id)
        _refresh_recommendation_state(creator_user_id)
    except Exception:
        pass
    creator_map = project_repository.list_creator_usernames([creator_user_id])
    return _serialize_project(
        project,
        creator_username=creator_map.get(creator_user_id),
        contribution_count=0,
        contributor_count=0,
    )


def list_projects(page: int, per_page: int, *, viewer_user_id: int | None = None) -> dict:
    if viewer_user_id is not None:
        all_items = project_repository.list_all_projects()
        total = len(all_items)
        own_items = [item for item in all_items if int(item.creator_user_id) == int(viewer_user_id)]
        candidate_items = [item for item in all_items if int(item.creator_user_id) != int(viewer_user_id)]
        try:
            ranked_candidate_items = rank_projects_for_user(projects=candidate_items, user_id=viewer_user_id)
        except Exception:
            ranked_candidate_items = candidate_items
        ordered_items = own_items + ranked_candidate_items
        start = max((page - 1) * per_page, 0)
        items = ordered_items[start : start + per_page]
    else:
        items, total = project_repository.list_projects_page(page, per_page)
    creator_map = project_repository.list_creator_usernames([item.creator_user_id for item in items])
    contribution_counts = project_repository.list_contribution_counts_for_project_ids([item.id for item in items])
    contributor_counts = project_repository.list_unique_contributor_counts_for_project_ids([item.id for item in items])
    serialized_items = [
        _serialize_project(
            item,
            creator_username=creator_map.get(item.creator_user_id),
            contribution_count=contribution_counts.get(item.id, 0),
            contributor_count=contributor_counts.get(item.id, 0),
        )
        for item in items
    ]
    return {
        "items": serialized_items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "summary": {
            "fundraising_count": project_repository.count_projects_by_status("fundraising"),
            "completed_count": project_repository.count_projects_by_status("completed"),
            "points_raised_total": project_repository.sum_points_raised(),
        },
    }


def get_project(project_id: int, *, viewer_user_id: int | None = None) -> dict:
    project = project_repository.get_project_by_id(project_id)
    if project is None:
        raise ProjectError("Project not found.", code=40400, http_status=404)
    if viewer_user_id is not None and viewer_user_id != project.creator_user_id:
        try:
            behavior_event_service.record_project_view(user_id=viewer_user_id, project_id=project.id)
            _refresh_recommendation_state(viewer_user_id)
        except Exception:
            pass
    creator_map = project_repository.list_creator_usernames([project.creator_user_id])
    return _serialize_project(
        project,
        creator_username=creator_map.get(project.creator_user_id),
        include_recent_contributions=True,
        contribution_count=project_repository.count_contributions(project.id),
        contributor_count=project_repository.count_unique_contributors(project.id),
    )


def contribute_to_project(*, project_id: int, user_id: int, points: int) -> dict:
    project = project_repository.get_project_by_id(project_id)
    if project is None:
        raise ProjectError("Project not found.", code=40400, http_status=404)
    if int(points or 0) <= 0:
        raise ProjectError("'points' must be a positive integer.")
    if str(project.status or "") == "completed":
        raise ProjectError("This project is already fully funded.", code=40901, http_status=409)
    if _is_expired(project):
        raise ProjectError("This project has passed its deadline.", code=40902, http_status=409)

    points_remaining = max(int(project.points_target or 0) - int(project.points_raised or 0), 0)
    if points_remaining <= 0:
        project.status = "completed"
        db.session.commit()
        raise ProjectError("This project is already fully funded.", code=40901, http_status=409)
    if int(points) > points_remaining:
        raise ProjectError(
            f"Contribution exceeds the remaining target. Maximum allowed is {points_remaining} points.",
            code=40903,
            http_status=409,
        )

    try:
        spend_txn = spend_points(
            user_id=user_id,
            points=int(points),
            source_type="project",
        )
    except InsufficientPointsError:
        raise ProjectError("Insufficient points for this contribution.", code=40200, http_status=402)

    contribution = project_repository.create_contribution(
        project_id=project.id,
        user_id=user_id,
        points=int(points),
    )
    db.session.flush()
    spend_txn.source_id = contribution.id
    project.points_raised = int(project.points_raised or 0) + int(points)
    just_completed = False
    if project.points_raised >= int(project.points_target or 0):
        project.points_raised = int(project.points_target or 0)
        if project.status != "completed":
            just_completed = True
        project.status = "completed"
    db.session.commit()

    if just_completed:
        recipient_ids = {
            int(project.creator_user_id),
            *project_repository.list_distinct_contributor_user_ids(project.id),
        }
        for recipient_user_id in recipient_ids:
            notification_service.on_project_completed(
                recipient_user_id=recipient_user_id,
                project_id=project.id,
                project_title=project.title,
            )

    try:
        behavior_event_service.record_project_contribute(
            user_id=user_id,
            project_id=project.id,
            contribution_id=contribution.id,
        )
        _refresh_recommendation_state(user_id)
    except Exception:
        pass

    creator_map = project_repository.list_creator_usernames([project.creator_user_id])
    contribution_username = project_repository.list_creator_usernames([user_id]).get(user_id, f"User {user_id}")
    viewer = db.session.get(User, user_id)
    return {
        "project": _serialize_project(
            project,
            creator_username=creator_map.get(project.creator_user_id),
            include_recent_contributions=True,
            contribution_count=project_repository.count_contributions(project.id),
            contributor_count=project_repository.count_unique_contributors(project.id),
        ),
        "contribution": _serialize_contribution(contribution, contribution_username),
        "viewer_current_points": int(viewer.current_points if viewer is not None else 0),
    }
