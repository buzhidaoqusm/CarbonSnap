"""The AI routes that answer with one JSON body: chat without streaming, the
location step, and the conversation history."""

import logging
from typing import Any

from fastapi import APIRouter

from app.api.ai.payloads import GENERIC_ERROR_MESSAGE, parse_chat
from app.api.deps import CurrentUserId, DbSession, PageParams
from app.api.errors import ApiError
from app.schemas.ai_chat import (
    ChatIn,
    ConversationMessages,
    ConversationPage,
    DeletedConversation,
    LocationContextIn,
)
from app.schemas.common import Envelope, ok
from app.services.ai.ai_conversation_service import (
    complete_routed_chat_message,
    delete_user_conversation,
    get_conversation_messages,
    list_user_conversations,
)
from app.services.ai.openrouter_service import OpenRouterConfigError
from app.services.ai.recycling_analysis_service import store_location_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _not_found(exc: ValueError) -> ApiError:
    return ApiError(40400, str(exc), 404)


# The reply's decision and trace depend on the path that answered (graph
# agent, tool calling or rules); P2's graph will settle them.
@router.post("/chat", response_model=Envelope[dict[str, Any]])
def chat(user_id: CurrentUserId, session: DbSession, body: ChatIn | None = None):
    parsed = parse_chat(body.model_dump(exclude_unset=True) if body else {})
    try:
        result = complete_routed_chat_message(
            session,
            user_id=user_id,
            message=parsed["message"],
            history=parsed["history"],
            image_data_url=parsed["image_data_url"],
            conversation_id=parsed["conversation_id"],
            client_context=parsed["client_context"],
        )
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise _not_found(exc) from exc
        raise ApiError(40001, str(exc)) from exc
    except OpenRouterConfigError as exc:
        raise ApiError(50000, str(exc), 500) from exc
    except Exception as exc:
        # Details stay in the log: provider errors can name internals.
        logger.exception("AI request failed.")
        raise ApiError(50000, GENERIC_ERROR_MESSAGE, 502) from exc
    return ok(result)


@router.post("/location-context", response_model=Envelope[dict[str, Any]])
def location_context(
    user_id: CurrentUserId, session: DbSession, body: LocationContextIn | None = None
):
    payload = body.model_dump(exclude_unset=True) if body else {}
    try:
        result = store_location_context(session, payload, user_id=user_id)
    except ValueError as exc:
        raise ApiError(40001, str(exc)) from exc
    except Exception as exc:
        logger.exception("Location context update failed.")
        raise ApiError(50000, GENERIC_ERROR_MESSAGE, 502) from exc
    return ok(result)


@router.get("/conversations", response_model=Envelope[ConversationPage])
def conversations(user_id: CurrentUserId, session: DbSession, paging: PageParams):
    return ok(
        list_user_conversations(
            session, user_id=user_id, page=paging.page, per_page=paging.per_page
        )
    )


@router.get(
    "/conversations/{conversation_id}/messages", response_model=Envelope[ConversationMessages]
)
def conversation_messages(conversation_id: int, user_id: CurrentUserId, session: DbSession):
    try:
        return ok(
            get_conversation_messages(session, user_id=user_id, conversation_id=conversation_id)
        )
    except ValueError as exc:
        raise _not_found(exc) from exc


@router.delete("/conversations/{conversation_id}", response_model=Envelope[DeletedConversation])
def delete_conversation(conversation_id: int, user_id: CurrentUserId, session: DbSession):
    try:
        return ok(
            delete_user_conversation(session, user_id=user_id, conversation_id=conversation_id)
        )
    except ValueError as exc:
        raise _not_found(exc) from exc
