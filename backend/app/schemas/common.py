"""The response envelope every endpoint returns."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Envelope[T](BaseModel):
    """{"code": 0, "message": "ok", "data": ...}; code is non-zero on errors."""

    code: int = 0
    message: str = "ok"
    data: T


def ok[T](data: T) -> Envelope[T]:
    return Envelope[T](data=data)


def error_body(code: int, message: str) -> dict[str, Any]:
    return {"code": code, "message": message, "data": {}}
