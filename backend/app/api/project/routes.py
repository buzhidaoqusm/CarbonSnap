"""Community projects funded with points."""

from typing import Annotated

from fastapi import APIRouter

from app.api.deps import CurrentUserId, DbSession, OptionalUserId, Pagination, pagination
from app.api.errors import ApiError
from app.schemas.common import Envelope, ok
from app.schemas.project import (
    ContributionIn,
    ContributionResult,
    ProjectDetail,
    ProjectIn,
    ProjectOut,
    ProjectPage,
    UploadIn,
    UploadResult,
)
from app.services.ai.image_storage_service import ImageStorageError, store_data_url_image
from app.services.project import project_service
from app.services.project.project_service import ProjectError

router = APIRouter(prefix="/api/projects", tags=["project"])

# Twelve cards fill the project grid.
ProjectPaging = Annotated[Pagination, pagination(default_per_page=12)]


def _api_error(exc: ProjectError) -> ApiError:
    return ApiError(exc.code, exc.message, exc.http_status)


def _as_int(value: int | str, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(40001, f"'{field}' must be an integer.") from exc


@router.post("/uploads", status_code=201, response_model=Envelope[UploadResult])
def upload_project_image(_: CurrentUserId, body: UploadIn | None = None):
    image = (body or UploadIn()).image
    if not isinstance(image, str):
        raise ApiError(40001, "Field 'image' must be a base64 data URL string.")
    try:
        url = store_data_url_image(image, namespace="project")
    except ImageStorageError as exc:
        raise ApiError(40001, str(exc)) from exc
    return ok(UploadResult(url=url))


@router.get("", response_model=Envelope[ProjectPage])
def list_projects(session: DbSession, viewer: OptionalUserId, paging: ProjectPaging):
    return ok(
        project_service.list_projects(session, paging.page, paging.per_page, viewer_user_id=viewer)
    )


@router.post("", status_code=201, response_model=Envelope[ProjectOut])
def create_project(user_id: CurrentUserId, session: DbSession, body: ProjectIn | None = None):
    body = body or ProjectIn()
    points_target = _as_int(body.points_target, "points_target")
    try:
        result = project_service.create_project(
            session,
            creator_user_id=user_id,
            title=body.title.strip(),
            description=body.description or None,
            cover_image_url=body.cover_image_url or None,
            points_target=points_target,
            deadline_at=body.deadline_at,
        )
    except ProjectError as exc:
        raise _api_error(exc) from exc
    return ok(result)


@router.get("/{project_id}", response_model=Envelope[ProjectDetail])
def get_project(project_id: int, session: DbSession, viewer: OptionalUserId):
    try:
        return ok(project_service.get_project(session, project_id, viewer_user_id=viewer))
    except ProjectError as exc:
        raise _api_error(exc) from exc


@router.post(
    "/{project_id}/contributions", status_code=201, response_model=Envelope[ContributionResult]
)
def contribute_to_project(
    project_id: int, user_id: CurrentUserId, session: DbSession, body: ContributionIn | None = None
):
    points = _as_int((body or ContributionIn()).points, "points")
    try:
        result = project_service.contribute_to_project(
            session, project_id=project_id, user_id=user_id, points=points
        )
    except ProjectError as exc:
        raise _api_error(exc) from exc
    return ok(result)
