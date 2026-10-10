from __future__ import annotations

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: int
    event_type: str
    source_type: str
    source_id: int
    title: str
    body: str
    source_url: str
    is_read: bool
    # ISO 8601 in UTC with a "Z" suffix, as the frontend expects.
    created_at: str


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    total: int
    page: int
    per_page: int
    unread_count: int


class UnreadCount(BaseModel):
    unread_count: int


class MarkAllResult(BaseModel):
    updated: int
