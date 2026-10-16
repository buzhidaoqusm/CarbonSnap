from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ProjectOut(BaseModel):
    id: int
    creator_user_id: int
    creator_username: str
    title: str
    description: str | None
    cover_image_url: str | None
    points_target: int
    points_raised: int
    points_remaining: int
    progress_ratio: float
    status: str
    # Naive ISO 8601 (datetime.isoformat()), as the frontend has always had.
    deadline_at: str
    created_at: str
    days_left: int
    is_expired: bool
    contribution_count: int
    contributor_count: int


class ContributionOut(BaseModel):
    id: int
    project_id: int
    user_id: int
    contributor_username: str
    points: int
    created_at: str


class ProjectDetail(ProjectOut):
    recent_contributions: list[ContributionOut]


class ProjectSummary(BaseModel):
    fundraising_count: int
    completed_count: int
    points_raised_total: int


class ProjectPage(BaseModel):
    items: list[ProjectOut]
    total: int
    page: int
    per_page: int
    summary: ProjectSummary


class ContributionResult(BaseModel):
    project: ProjectDetail
    contribution: ContributionOut
    viewer_current_points: int


class UploadResult(BaseModel):
    url: str


# Request bodies. Numbers may arrive as strings ("120"), as the Flask routes
# accepted; the route converts them and keeps the old error messages.


class ProjectIn(BaseModel):
    title: str = ""
    description: str | None = None
    cover_image_url: str | None = None
    points_target: int | str = 0
    deadline_at: str | None = None


class ContributionIn(BaseModel):
    points: int | str = 0


class UploadIn(BaseModel):
    # Any, so a non-string gets the route's message rather than Pydantic's.
    image: Any = None
