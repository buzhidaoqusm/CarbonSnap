"""Error responses for the FastAPI routes, in the same envelope as success.

The frontend reads "message" from any non-2xx body, so FastAPI's defaults
({"detail": ...}, and 422 for validation) are replaced here.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import error_body


class ApiError(Exception):
    """An expected failure: the envelope code, its message and HTTP status."""

    def __init__(self, code: int, message: str, http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class Unauthorized(ApiError):
    def __init__(self, message: str = "Authentication required."):
        super().__init__(40100, message, 401)


def _api_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    headers = {"WWW-Authenticate": "Bearer"} if exc.http_status == 401 else None
    return JSONResponse(
        error_body(exc.code, exc.message), status_code=exc.http_status, headers=headers
    )


def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    # The same 400 the Flask routes return for bad input. The first error
    # names the field, e.g. "path.notification_id: Input should be a valid integer".
    assert isinstance(exc, RequestValidationError)
    first = exc.errors()[0]
    where = ".".join(str(part) for part in first["loc"])
    return JSONResponse(error_body(40000, f"{where}: {first['msg']}"), status_code=400)


def _http_error(_: Request, exc: Exception) -> JSONResponse:
    # Starlette's own 404/405 for paths a FastAPI router owns.
    assert isinstance(exc, StarletteHTTPException)
    code = exc.status_code * 100
    return JSONResponse(
        error_body(code, str(exc.detail)), status_code=exc.status_code, headers=exc.headers
    )


def install_error_handlers(api: FastAPI) -> None:
    api.add_exception_handler(ApiError, _api_error)
    api.add_exception_handler(RequestValidationError, _validation_error)
    api.add_exception_handler(StarletteHTTPException, _http_error)
