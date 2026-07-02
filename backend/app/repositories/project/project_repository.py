from __future__ import annotations

from sqlalchemy import case, func, select

from app.extensions.db import db
from app.models.project import Project, ProjectContribution
from app.models.user import User


def create_project(
    *,
    creator_user_id: int,
    title: str,
    description: str | None,
    cover_image_url: str | None,
    points_target: int,
    deadline_at,
) -> Project:
    project = Project(
        creator_user_id=creator_user_id,
        title=title,
        description=description,
        cover_image_url=cover_image_url,
        points_target=points_target,
        deadline_at=deadline_at,
    )
    db.session.add(project)
    return project


def get_project_by_id(project_id: int) -> Project | None:
    return db.session.get(Project, project_id)


def list_projects_page(page: int, per_page: int) -> tuple[list[Project], int]:
    fundraising_first = case((Project.status == "fundraising", 0), else_=1)
    base = select(Project)
    total = db.session.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.session.scalars(
        base.order_by(
            fundraising_first.asc(),
            Project.deadline_at.asc(),
            Project.created_at.desc(),
            Project.id.desc(),
        )
        .limit(per_page)
        .offset((page - 1) * per_page)
    ).all()
    return list(items), total


def list_all_projects() -> list[Project]:
    fundraising_first = case((Project.status == "fundraising", 0), else_=1)
    rows = db.session.scalars(
        select(Project).order_by(
            fundraising_first.asc(),
            Project.deadline_at.asc(),
            Project.created_at.desc(),
            Project.id.desc(),
        )
    ).all()
    return list(rows)


def list_all_projects_excluding_creator(*, creator_user_id: int) -> list[Project]:
    fundraising_first = case((Project.status == "fundraising", 0), else_=1)
    rows = db.session.scalars(
        select(Project)
        .where(Project.creator_user_id != creator_user_id)
        .order_by(
            fundraising_first.asc(),
            Project.deadline_at.asc(),
            Project.created_at.desc(),
            Project.id.desc(),
        )
    ).all()
    return list(rows)


def count_projects_by_status(status: str) -> int:
    return db.session.scalar(select(func.count(Project.id)).where(Project.status == status)) or 0


def sum_points_raised() -> int:
    return int(db.session.scalar(select(func.coalesce(func.sum(Project.points_raised), 0))) or 0)


def create_contribution(*, project_id: int, user_id: int, points: int) -> ProjectContribution:
    contribution = ProjectContribution(
        project_id=project_id,
        user_id=user_id,
        points=points,
    )
    db.session.add(contribution)
    return contribution


def list_recent_contributions(
    project_id: int,
    *,
    limit: int = 10,
) -> list[tuple[ProjectContribution, str]]:
    rows = db.session.execute(
        select(ProjectContribution, User.username)
        .join(User, User.id == ProjectContribution.user_id)
        .where(ProjectContribution.project_id == project_id)
        .order_by(ProjectContribution.created_at.desc(), ProjectContribution.id.desc())
        .limit(limit)
    ).all()
    return [(row[0], row[1]) for row in rows]


def count_contributions(project_id: int) -> int:
    return (
        db.session.scalar(
            select(func.count(ProjectContribution.id)).where(ProjectContribution.project_id == project_id)
        )
        or 0
    )


def count_unique_contributors(project_id: int) -> int:
    return (
        db.session.scalar(
            select(func.count(func.distinct(ProjectContribution.user_id))).where(
                ProjectContribution.project_id == project_id
            )
        )
        or 0
    )


def list_distinct_contributor_user_ids(project_id: int) -> list[int]:
    rows = db.session.scalars(
        select(func.distinct(ProjectContribution.user_id)).where(
            ProjectContribution.project_id == project_id
        )
    ).all()
    return [int(user_id) for user_id in rows if user_id is not None]


def list_creator_usernames(user_ids: list[int]) -> dict[int, str]:
    normalized_ids = [int(user_id) for user_id in user_ids if user_id is not None]
    if not normalized_ids:
        return {}
    rows = db.session.execute(
        select(User.id, User.username).where(User.id.in_(normalized_ids))
    ).all()
    return {int(user_id): username for user_id, username in rows}


def list_contribution_counts_for_project_ids(project_ids: list[int]) -> dict[int, int]:
    normalized_ids = [int(project_id) for project_id in project_ids if project_id is not None]
    if not normalized_ids:
        return {}
    rows = db.session.execute(
        select(ProjectContribution.project_id, func.count(ProjectContribution.id))
        .where(ProjectContribution.project_id.in_(normalized_ids))
        .group_by(ProjectContribution.project_id)
    ).all()
    return {int(project_id): int(count) for project_id, count in rows if project_id is not None}


def list_unique_contributor_counts_for_project_ids(project_ids: list[int]) -> dict[int, int]:
    normalized_ids = [int(project_id) for project_id in project_ids if project_id is not None]
    if not normalized_ids:
        return {}
    rows = db.session.execute(
        select(ProjectContribution.project_id, func.count(func.distinct(ProjectContribution.user_id)))
        .where(ProjectContribution.project_id.in_(normalized_ids))
        .group_by(ProjectContribution.project_id)
    ).all()
    return {int(project_id): int(count) for project_id, count in rows if project_id is not None}
