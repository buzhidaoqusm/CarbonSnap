from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectContribution
from app.models.user import User


def create_project(
    session: Session,
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
    session.add(project)
    return project


def get_project_by_id(session: Session, project_id: int) -> Project | None:
    return session.get(Project, project_id)


def get_project_for_update(session: Session, project_id: int) -> Project | None:
    """Read the project and lock its row until the transaction ends, so two
    contributions cannot both pass the remaining-target check."""
    return session.scalar(
        select(Project)
        .where(Project.id == project_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def _default_order() -> tuple:
    """Fundraising first, then the soonest deadline: the order of every list."""
    fundraising_first = case((Project.status == "fundraising", 0), else_=1)
    return (
        fundraising_first.asc(),
        Project.deadline_at.asc(),
        Project.created_at.desc(),
        Project.id.desc(),
    )


def list_projects_page(session: Session, page: int, per_page: int) -> tuple[list[Project], int]:
    total = count_projects(session)
    items = session.scalars(
        select(Project).order_by(*_default_order()).limit(per_page).offset((page - 1) * per_page)
    ).all()
    return list(items), total


def count_projects(session: Session) -> int:
    return session.scalar(select(func.count(Project.id))) or 0


def list_projects_by_creator(session: Session, *, creator_user_id: int) -> list[Project]:
    return list(
        session.scalars(
            select(Project)
            .where(Project.creator_user_id == creator_user_id)
            .order_by(*_default_order())
        ).all()
    )


def list_projects_excluding_creator(
    session: Session, *, creator_user_id: int, limit: int, offset: int = 0
) -> list[Project]:
    """Other people's projects in the default order: the ranking candidates,
    and from `offset` on, the pages past them."""
    if limit <= 0:
        return []
    return list(
        session.scalars(
            select(Project)
            .where(Project.creator_user_id != creator_user_id)
            .order_by(*_default_order())
            .limit(limit)
            .offset(offset)
        ).all()
    )


def count_projects_by_status(session: Session, status: str) -> int:
    return session.scalar(select(func.count(Project.id)).where(Project.status == status)) or 0


def sum_points_raised(session: Session) -> int:
    return int(session.scalar(select(func.coalesce(func.sum(Project.points_raised), 0))) or 0)


def create_contribution(
    session: Session, *, project_id: int, user_id: int, points: int
) -> ProjectContribution:
    contribution = ProjectContribution(
        project_id=project_id,
        user_id=user_id,
        points=points,
    )
    session.add(contribution)
    return contribution


def list_recent_contributions(
    session: Session,
    project_id: int,
    *,
    limit: int = 10,
) -> list[tuple[ProjectContribution, str]]:
    rows = session.execute(
        select(ProjectContribution, User.username)
        .join(User, User.id == ProjectContribution.user_id)
        .where(ProjectContribution.project_id == project_id)
        .order_by(ProjectContribution.created_at.desc(), ProjectContribution.id.desc())
        .limit(limit)
    ).all()
    return [(row[0], row[1]) for row in rows]


def count_contributions(session: Session, project_id: int) -> int:
    return (
        session.scalar(
            select(func.count(ProjectContribution.id)).where(
                ProjectContribution.project_id == project_id
            )
        )
        or 0
    )


def count_unique_contributors(session: Session, project_id: int) -> int:
    return (
        session.scalar(
            select(func.count(func.distinct(ProjectContribution.user_id))).where(
                ProjectContribution.project_id == project_id
            )
        )
        or 0
    )


def list_distinct_contributor_user_ids(session: Session, project_id: int) -> list[int]:
    rows = session.scalars(
        select(func.distinct(ProjectContribution.user_id)).where(
            ProjectContribution.project_id == project_id
        )
    ).all()
    return [int(user_id) for user_id in rows if user_id is not None]


def list_creator_usernames(session: Session, user_ids: list[int]) -> dict[int, str]:
    normalized_ids = [int(user_id) for user_id in user_ids if user_id is not None]
    if not normalized_ids:
        return {}
    rows = session.execute(select(User.id, User.username).where(User.id.in_(normalized_ids))).all()
    return {int(user_id): username for user_id, username in rows}


def list_contribution_counts_for_project_ids(
    session: Session, project_ids: list[int]
) -> dict[int, int]:
    normalized_ids = [int(project_id) for project_id in project_ids if project_id is not None]
    if not normalized_ids:
        return {}
    rows = session.execute(
        select(ProjectContribution.project_id, func.count(ProjectContribution.id))
        .where(ProjectContribution.project_id.in_(normalized_ids))
        .group_by(ProjectContribution.project_id)
    ).all()
    return {int(project_id): int(count) for project_id, count in rows if project_id is not None}


def list_unique_contributor_counts_for_project_ids(
    session: Session, project_ids: list[int]
) -> dict[int, int]:
    normalized_ids = [int(project_id) for project_id in project_ids if project_id is not None]
    if not normalized_ids:
        return {}
    rows = session.execute(
        select(
            ProjectContribution.project_id, func.count(func.distinct(ProjectContribution.user_id))
        )
        .where(ProjectContribution.project_id.in_(normalized_ids))
        .group_by(ProjectContribution.project_id)
    ).all()
    return {int(project_id): int(count) for project_id, count in rows if project_id is not None}
