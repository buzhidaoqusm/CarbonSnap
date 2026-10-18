"""Files users uploaded: avatars and the images in posts, projects and chats."""

from email.utils import parsedate
from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse

from app.api.errors import ApiError
from app.core.config import get_settings

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

# Browsers revalidate on every use, so a replaced file shows up at once; an
# unchanged one costs a 304.
CACHE_CONTROL = "no-cache"


def _not_modified(request: Request, response: FileResponse) -> bool:
    # FileResponse sets ETag and Last-Modified but, unlike StaticFiles, never
    # answers the conditional headers. Same rules: If-None-Match wins.
    if if_none_match := request.headers.get("if-none-match"):
        tags = [tag.strip().removeprefix("W/") for tag in if_none_match.split(",")]
        return if_none_match.strip() == "*" or response.headers["etag"] in tags
    if_modified_since = parsedate(request.headers.get("if-modified-since", ""))
    last_modified = parsedate(response.headers["last-modified"])
    return (
        if_modified_since is not None
        and last_modified is not None
        and (if_modified_since >= last_modified)
    )


# FastAPI, unlike Flask, does not answer HEAD on a GET route; it gets its own,
# kept out of the docs so the two do not share an operation id.
@router.get("/{relative_path:path}", response_class=FileResponse)
@router.head("/{relative_path:path}", include_in_schema=False)
def get_uploaded_file(relative_path: str, request: Request):
    upload_root = Path(get_settings().upload_root).resolve()
    # resolve() collapses ".." and symlinks, and an absolute relative_path
    # replaces the root altogether, so only the resolved path can be checked.
    candidate = (upload_root / relative_path).resolve()

    # is_relative_to compares whole path segments: "uploads_backup" is not
    # inside "uploads", which a string prefix check would have let through.
    if not candidate.is_relative_to(upload_root) or not candidate.is_file():
        raise ApiError(40400, "Uploaded file not found.", 404)

    response = FileResponse(
        candidate, stat_result=candidate.stat(), headers={"cache-control": CACHE_CONTROL}
    )
    if _not_modified(request, response):
        return Response(
            status_code=304,
            headers={
                name: response.headers[name] for name in ("etag", "last-modified", "cache-control")
            },
        )
    return response
