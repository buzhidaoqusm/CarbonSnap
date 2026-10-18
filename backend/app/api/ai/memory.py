"""What the assistant remembers about a user: the items and their summary."""

from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUserId, DbSession
from app.api.errors import ApiError
from app.models.user import User
from app.schemas.ai_memory import MemoryChange, MemoryIn, MemoryList, MemoryPatchIn
from app.schemas.common import Envelope, ok
from app.services.ai.memory_service import (
    create_manual_memory_item,
    delete_memory_item,
    list_memory_payload,
    serialize_memory_item,
    update_manual_memory_item,
)

router = APIRouter(prefix="/api/ai/memory", tags=["ai memory"])


def _text(body: MemoryIn | MemoryPatchIn, field: str) -> str | None:
    """The field as the Flask routes read it: None when absent, str() of
    whatever was sent otherwise, so a null arrives as "None"."""
    if field not in body.model_fields_set:
        return None
    return str(getattr(body, field)).strip()


def _change(session: DbSession, user_id: int, item) -> dict[str, Any]:
    return {
        "item": serialize_memory_item(item),
        "summary": list_memory_payload(session, user_id)["summary"],
    }


@router.get("", response_model=Envelope[MemoryList])
def get_memory(user_id: CurrentUserId, session: DbSession):
    # A deleted user's token gets an empty list, as before.
    return ok(list_memory_payload(session, user_id))


@router.post("", response_model=Envelope[MemoryChange])
def create_memory(user_id: CurrentUserId, session: DbSession, body: MemoryIn | None = None):
    body = body or MemoryIn()
    memory_type = _text(body, "memory_type") or ""
    memory_key = _text(body, "memory_key") or ""
    if not memory_type:
        raise ApiError(40001, "Field 'memory_type' is required.")
    if not memory_key:
        raise ApiError(40001, "Field 'memory_key' is required.")
    if not isinstance(body.value, dict) or not body.value:
        raise ApiError(40001, "Field 'value' must be a non-empty object.")
    # A deleted user's token: the insert would break the user foreign key.
    if session.get(User, user_id) is None:
        raise ApiError(40400, "User not found.", 404)

    try:
        item = create_manual_memory_item(
            session,
            user_id=user_id,
            memory_type=memory_type,
            memory_key=memory_key,
            value=body.value,
        )
    except ValueError as exc:
        raise ApiError(40001, str(exc)) from exc
    return ok(_change(session, user_id, item))


@router.patch("/{item_id}", response_model=Envelope[MemoryChange])
def update_memory(
    item_id: int, user_id: CurrentUserId, session: DbSession, body: MemoryPatchIn | None = None
):
    body = body or MemoryPatchIn()
    try:
        item = update_manual_memory_item(
            session,
            item_id=item_id,
            user_id=user_id,
            # Blank keeps the stored value: the service falls back on falsy.
            memory_type=_text(body, "memory_type"),
            memory_key=_text(body, "memory_key"),
            value=body.value if "value" in body.model_fields_set else None,
        )
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise ApiError(40400, message, 404) from exc
        raise ApiError(40001, message) from exc
    return ok(_change(session, user_id, item))


@router.delete("/{item_id}", response_model=Envelope[MemoryChange])
def delete_memory(item_id: int, user_id: CurrentUserId, session: DbSession):
    try:
        item = delete_memory_item(session, item_id=item_id, user_id=user_id)
    except ValueError as exc:
        raise ApiError(40400, str(exc), 404) from exc
    return ok(_change(session, user_id, item))
