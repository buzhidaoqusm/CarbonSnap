from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.extensions.db import db
from app.models.memory import UserMemoryItem


def _utc_now() -> datetime:
    return datetime.now(UTC)


def list_active_memory_items(user_id: int) -> list[UserMemoryItem]:
    items = db.session.scalars(
        select(UserMemoryItem)
        .where(
            UserMemoryItem.user_id == user_id,
            UserMemoryItem.status == "active",
        )
        .order_by(
            UserMemoryItem.memory_type.asc(),
            UserMemoryItem.memory_key.asc(),
            UserMemoryItem.updated_at.desc(),
            UserMemoryItem.id.desc(),
        )
    ).all()
    return list(items)


def list_all_memory_items(user_id: int) -> list[UserMemoryItem]:
    items = db.session.scalars(
        select(UserMemoryItem)
        .where(UserMemoryItem.user_id == user_id)
        .order_by(UserMemoryItem.created_at.desc(), UserMemoryItem.id.desc())
    ).all()
    return list(items)


def get_memory_item(item_id: int, user_id: int) -> UserMemoryItem | None:
    return db.session.scalar(
        select(UserMemoryItem).where(
            UserMemoryItem.id == item_id,
            UserMemoryItem.user_id == user_id,
        )
    )


def create_memory_item(
    *,
    user_id: int,
    memory_type: str,
    memory_key: str,
    value_json: str,
    source_type: str,
    source_message_id: int | None = None,
    conversation_id: int | None = None,
) -> UserMemoryItem:
    item = UserMemoryItem(
        user_id=user_id,
        memory_type=memory_type,
        memory_key=memory_key,
        value_json=value_json,
        source_type=source_type,
        source_message_id=source_message_id,
        conversation_id=conversation_id,
    )
    db.session.add(item)
    db.session.commit()
    return item


def replace_memory_item(
    *,
    user_id: int,
    memory_type: str,
    memory_key: str,
    value_json: str,
    source_type: str,
    source_message_id: int | None = None,
    conversation_id: int | None = None,
) -> UserMemoryItem:
    active_items = db.session.scalars(
        select(UserMemoryItem).where(
            UserMemoryItem.user_id == user_id,
            UserMemoryItem.memory_type == memory_type,
            UserMemoryItem.memory_key == memory_key,
            UserMemoryItem.status == "active",
        )
    ).all()

    now = _utc_now()
    for existing in active_items:
        existing.status = "deleted"
        existing.updated_at = now

    item = UserMemoryItem(
        user_id=user_id,
        memory_type=memory_type,
        memory_key=memory_key,
        value_json=value_json,
        source_type=source_type,
        source_message_id=source_message_id,
        conversation_id=conversation_id,
        status="active",
        created_at=now,
        updated_at=now,
    )
    db.session.add(item)
    db.session.commit()
    return item


def update_memory_item(
    item_id: int,
    user_id: int,
    *,
    memory_type: str | None = None,
    memory_key: str | None = None,
    value_json: str | None = None,
) -> UserMemoryItem | None:
    item = get_memory_item(item_id, user_id)
    if item is None or item.status != "active":
        return None

    if memory_type is not None and memory_type != item.memory_type:
        item.memory_type = memory_type
    if memory_key is not None and memory_key != item.memory_key:
        item.memory_key = memory_key
    if value_json is not None:
        item.value_json = value_json

    item.updated_at = _utc_now()
    db.session.commit()
    return item


def soft_delete_memory_item(item_id: int, user_id: int) -> UserMemoryItem | None:
    item = get_memory_item(item_id, user_id)
    if item is None or item.status == "deleted":
        return None

    item.status = "deleted"
    item.updated_at = _utc_now()
    db.session.commit()
    return item
