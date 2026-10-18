from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class MemoryItemOut(BaseModel):
    id: int
    user_id: int
    memory_type: str
    memory_key: str
    value: dict[str, Any]
    source_type: str
    source_message_id: int | None
    conversation_id: int | None
    status: str
    # Naive ISO 8601 (datetime.isoformat()), as the frontend has always had.
    created_at: str | None
    updated_at: str | None


class ContentInterestPreferences(BaseModel):
    # Topic entries carry optional keys (event_count, source, ...) by topic.
    topics: list[dict[str, Any]]
    confidence_score: float


class MemorySummary(BaseModel):
    version: int
    updated_at: str
    content_interest_preferences: ContentInterestPreferences
    # The values are whatever the user or the chat stored for each key.
    action_preferences: dict[str, Any]


class MemoryList(BaseModel):
    summary: MemorySummary
    items: list[MemoryItemOut]


class MemoryChange(BaseModel):
    item: MemoryItemOut
    summary: MemorySummary


# Request bodies. Any, so the routes can keep the messages and the str()
# coercion the Flask routes had ("Unsupported memory_type: 5").


class MemoryIn(BaseModel):
    memory_type: Any = None
    memory_key: Any = None
    value: Any = None


class MemoryPatchIn(BaseModel):
    # Absent and null differ (null is sent on as "None"): see model_fields_set.
    memory_type: Any = None
    memory_key: Any = None
    value: Any = None
