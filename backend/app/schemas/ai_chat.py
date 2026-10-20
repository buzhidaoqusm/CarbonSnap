from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ConversationOut(BaseModel):
    id: int
    user_id: int
    title: str | None
    status: str
    current_pending_action: str | None
    # The recycling flow's saved state; its shape depends on the step.
    session_context_json: Any
    # Naive ISO 8601 (datetime.isoformat()), as the frontend has always had.
    last_message_at: str | None
    created_at: str | None
    updated_at: str | None


class ConversationPage(BaseModel):
    items: list[ConversationOut]
    total: int
    page: int
    per_page: int


class ConversationMessages(BaseModel):
    conversation: ConversationOut
    # Messages carry decision traces and analysis payloads whose shape depends
    # on the path that answered; P2's graph will settle them.
    items: list[dict[str, Any]]
    total: int
    pending_recycling_case: dict[str, Any] | None


class DeletedConversation(BaseModel):
    deleted_conversation_id: int


# Request bodies: Any everywhere, read by app.api.ai.payloads with the old
# messages. Only the keys that were sent are passed on (exclude_unset).


class ChatIn(BaseModel):
    message: Any = None
    history: Any = None
    image: Any = None
    conversation_id: Any = None
    client_context: Any = None


class LocationContextIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    session_id: Any = None
    conversation_id: Any = None
    permission_state: Any = None
    browser_location: Any = None
    manual_area: Any = None
    skip_nearby_search: Any = None
