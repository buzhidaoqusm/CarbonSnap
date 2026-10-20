"""The streaming AI routes, still on Flask until they move to FastAPI."""

import json
from collections.abc import Callable, Generator
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.ai.payloads import (
    GENERIC_ERROR_MESSAGE,
    parse_audit,
    parse_chat,
    parse_recycling,
    parse_session_id,
)
from app.api.errors import ApiError
from app.extensions.db import db
from app.services.ai.ai_conversation_service import stream_routed_chat_message
from app.services.ai.openrouter_service import OpenRouterConfigError
from app.services.ai.recycling_analysis_service import (
    stream_recycling_analysis,
    stream_recycling_resume,
)
from app.services.ai.recycling_audit_service import stream_recycling_audit

ai_bp = Blueprint("ai", __name__)


def _json_sse_response(
    event_generator: Callable[[], Generator[dict[str, Any], None, None]],
) -> Response:
    def generate():
        yield b'data: {"type":"heartbeat","stream_stage":"accepted"}\n\n'
        try:
            for event in event_generator():
                payload = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                yield payload.encode("utf-8")
        except OpenRouterConfigError as exc:
            error_event = {"type": "error", "code": 50000, "message": str(exc)}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n".encode()
        except Exception:
            current_app.logger.exception("AI stream failed.")
            error_event = {"type": "error", "code": 50000, "message": GENERIC_ERROR_MESSAGE}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n".encode()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        direct_passthrough=True,
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _error_response(exc: ApiError):
    return jsonify({"code": exc.code, "message": exc.message, "data": {}}), exc.http_status


def _body() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


@ai_bp.post("/ai/chat/stream")
@jwt_required()
def ai_chat_stream():
    try:
        parsed = parse_chat(_body())
    except ApiError as exc:
        return _error_response(exc)

    user_id = int(get_jwt_identity())
    return _json_sse_response(
        lambda: stream_routed_chat_message(db.session, user_id=user_id, **parsed)
    )


@ai_bp.post("/ai/analyze-image")
@jwt_required()
def ai_analyze_image():
    try:
        parsed = parse_recycling(_body())
    except ApiError as exc:
        return _error_response(exc)

    user_id = int(get_jwt_identity())
    return _json_sse_response(
        lambda: stream_recycling_analysis(db.session, user_id=user_id, **parsed)
    )


@ai_bp.post("/ai/chat/resume")
@jwt_required()
def ai_chat_resume():
    try:
        session_id = parse_session_id(_body())
    except ApiError as exc:
        return _error_response(exc)

    user_id = int(get_jwt_identity())
    return _json_sse_response(
        lambda: stream_recycling_resume(db.session, session_id=session_id, user_id=user_id)
    )


@ai_bp.post("/ai/audit-recycling")
@jwt_required()
def ai_audit_recycling():
    try:
        parsed = parse_audit(_body())
    except ApiError as exc:
        return _error_response(exc)

    user_id = int(get_jwt_identity())
    return _json_sse_response(lambda: stream_recycling_audit(db.session, user_id=user_id, **parsed))
