"""The streaming AI routes: chat, image analysis, resuming after the
location step, and the completion-photo audit.

A body that does not parse is a JSON 400 before any frame is sent; after
the heartbeat, failures arrive as an error frame (see app.api.ai.sse).
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.ai.payloads import parse_audit, parse_chat, parse_recycling, parse_session_id
from app.api.ai.sse import sse_response
from app.api.deps import CurrentUserId, DbSession
from app.schemas.ai_chat import AuditIn, ChatIn, RecyclingIn, ResumeIn
from app.services.ai.ai_conversation_service import stream_routed_chat_message
from app.services.ai.recycling_analysis_service import (
    stream_recycling_analysis,
    stream_recycling_resume,
)
from app.services.ai.recycling_audit_service import stream_recycling_audit

router = APIRouter(prefix="/api/ai", tags=["ai"])

_SSE: dict[int | str, dict[str, Any]] = {
    200: {"content": {"text/event-stream": {}}, "description": "Server-sent events."}
}


def _sent(body: BaseModel | None) -> dict[str, Any]:
    # Only the keys the client sent, as request.get_json() had them.
    return body.model_dump(exclude_unset=True) if body else {}


@router.post("/chat/stream", responses=_SSE)
def chat_stream(user_id: CurrentUserId, session: DbSession, body: ChatIn | None = None):
    parsed = parse_chat(_sent(body))
    return sse_response(lambda: stream_routed_chat_message(session, user_id=user_id, **parsed))


@router.post("/analyze-image", responses=_SSE)
def analyze_image(user_id: CurrentUserId, session: DbSession, body: RecyclingIn | None = None):
    parsed = parse_recycling(_sent(body))
    return sse_response(lambda: stream_recycling_analysis(session, user_id=user_id, **parsed))


@router.post("/chat/resume", responses=_SSE)
def chat_resume(user_id: CurrentUserId, session: DbSession, body: ResumeIn | None = None):
    session_id = parse_session_id(_sent(body))
    return sse_response(
        lambda: stream_recycling_resume(session, session_id=session_id, user_id=user_id)
    )


@router.post("/audit-recycling", responses=_SSE)
def audit_recycling(user_id: CurrentUserId, session: DbSession, body: AuditIn | None = None):
    parsed = parse_audit(_sent(body))
    return sse_response(lambda: stream_recycling_audit(session, user_id=user_id, **parsed))
