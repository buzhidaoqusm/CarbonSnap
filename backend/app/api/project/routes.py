from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.ai.image_storage_service import ImageStorageError, store_data_url_image
from app.services.project import project_service
from app.services.project.project_service import ProjectError
from app.utils.response import fail, ok

project_bp = Blueprint("project", __name__)


def _current_user_id() -> int:
    return int(get_jwt_identity())


def _optional_current_user_id() -> int | None:
    identity = get_jwt_identity()
    if identity is None:
        return None
    return int(identity)


def _parse_pagination() -> tuple[int, int]:
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = min(100, max(1, int(request.args.get("per_page", 12))))
    except (TypeError, ValueError):
        per_page = 12
    return page, per_page


@project_bp.post("/projects/uploads")
@jwt_required()
def upload_project_image():
    body = request.get_json(silent=True) or {}
    image_data_url = body.get("image")

    if image_data_url is None or not isinstance(image_data_url, str):
        return fail(40001, "Field 'image' must be a base64 data URL string.")

    try:
        image_url = store_data_url_image(image_data_url, namespace="project")
    except ImageStorageError as exc:
        return fail(40001, str(exc))

    return ok({"url": image_url}, status=201)


@project_bp.get("/projects")
@jwt_required(optional=True)
def list_projects():
    page, per_page = _parse_pagination()
    return ok(project_service.list_projects(page, per_page, viewer_user_id=_optional_current_user_id()))


@project_bp.post("/projects")
@jwt_required()
def create_project():
    body = request.get_json(silent=True) or {}
    title = str(body.get("title", "")).strip()
    deadline_at = body.get("deadline_at")
    try:
        points_target = int(body.get("points_target", 0))
    except (TypeError, ValueError):
        return fail(40001, "'points_target' must be an integer.")
    try:
        result = project_service.create_project(
            creator_user_id=_current_user_id(),
            title=title,
            description=body.get("description") or None,
            cover_image_url=body.get("cover_image_url") or None,
            points_target=points_target,
            deadline_at=deadline_at,
        )
    except ProjectError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result, status=201)


@project_bp.get("/projects/<int:project_id>")
@jwt_required(optional=True)
def get_project(project_id: int):
    try:
        return ok(project_service.get_project(project_id, viewer_user_id=_optional_current_user_id()))
    except ProjectError as exc:
        return fail(exc.code, exc.message, exc.http_status)


@project_bp.post("/projects/<int:project_id>/contributions")
@jwt_required()
def contribute_to_project(project_id: int):
    body = request.get_json(silent=True) or {}
    try:
        points = int(body.get("points", 0))
    except (TypeError, ValueError):
        return fail(40001, "'points' must be an integer.")
    try:
        result = project_service.contribute_to_project(
            project_id=project_id,
            user_id=_current_user_id(),
            points=points,
        )
    except ProjectError as exc:
        return fail(exc.code, exc.message, exc.http_status)
    return ok(result, status=201)
