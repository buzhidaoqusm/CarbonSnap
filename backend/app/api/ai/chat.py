import json
from collections.abc import Callable, Generator
from typing import Any

from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.ai.ai_conversation_service import (
    complete_routed_chat_message,
    delete_user_conversation,
    get_conversation_messages,
    list_user_conversations,
    stream_routed_chat_message,
)
from app.services.ai.openrouter_service import OpenRouterConfigError
from app.services.ai.recycling_analysis_service import (
    store_location_context,
    stream_recycling_analysis,
    stream_recycling_resume,
)
from app.services.ai.recycling_audit_service import stream_recycling_audit

ai_bp = Blueprint("ai", __name__)


def _parse_pagination() -> tuple[int, int]:
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except (TypeError, ValueError):
        per_page = 20
    return page, per_page


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
        except Exception as exc:
            error_event = {"type": "error", "code": 50000, "message": f"AI stream failed: {exc}"}
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


def _parse_generic_chat_payload():
    payload = request.get_json(silent=True) or {}

    message = str(payload.get("message", "")).strip()
    history = payload.get("history", [])
    image_data_url = payload.get("image")
    has_image_payload = bool(str(image_data_url or "").strip())
    conversation_id = payload.get("conversation_id")
    client_context = payload.get("client_context")

    if not message and not has_image_payload:
        return None, _error_response(40001, "Field 'message' or 'image' is required.", 400)

    if history is not None and not isinstance(history, list):
        return None, _error_response(40001, "Field 'history' must be a list when provided.", 400)

    if image_data_url is not None and not isinstance(image_data_url, str):
        return None, _error_response(
            40001,
            "Field 'image' must be a base64 data URL string when provided.",
            400,
        )

    if client_context is not None and not isinstance(client_context, dict):
        return None, _error_response(
            40001,
            "Field 'client_context' must be an object when provided.",
            400,
        )

    if conversation_id in ("", None):
        parsed_conversation_id = None
    else:
        try:
            parsed_conversation_id = int(conversation_id)
        except (TypeError, ValueError):
            return None, _error_response(
                40001,
                "Field 'conversation_id' must be an integer when provided.",
                400,
            )

    return {
        "message": message,
        "history": history,
        "image": image_data_url,
        "conversation_id": parsed_conversation_id,
        "client_context": client_context,
    }, None


def _parse_recycling_payload():
    payload = request.get_json(silent=True) or {}

    message = str(payload.get("message", "")).strip()
    prompt = str(payload.get("prompt", "")).strip()
    image_data_url = payload.get("image") or payload.get("image_url")
    raw_session_id = payload.get("session_id")
    if raw_session_id in (None, "", "None", "null"):
        session_id = None
    else:
        session_id = str(raw_session_id).strip() or None
    conversation_id = payload.get("conversation_id")

    if image_data_url is not None and not isinstance(image_data_url, str):
        return None, _error_response(
            40001,
            "Field 'image' must be a base64 data URL string when provided.",
            400,
        )

    if conversation_id in ("", None):
        parsed_conversation_id = None
    else:
        try:
            parsed_conversation_id = int(conversation_id)
        except (TypeError, ValueError):
            return None, _error_response(
                40001,
                "Field 'conversation_id' must be an integer when provided.",
                400,
            )

    effective_message = message or prompt or "Please analyze this recycling item."
    return {
        "message": effective_message,
        "image": image_data_url,
        "session_id": session_id,
        "conversation_id": parsed_conversation_id,
    }, None


def _parse_audit_payload():
    payload = request.get_json(silent=True) or {}

    conversation_id = payload.get("conversation_id")
    recycling_case_id = payload.get("recycling_case_id")
    message = str(payload.get("message", "")).strip()
    image_data_url = payload.get("image") or payload.get("image_url")

    if image_data_url is None:
        return None, _error_response(40001, "Field 'image' is required.", 400)

    if not isinstance(image_data_url, str):
        return None, _error_response(
            40001,
            "Field 'image' must be a base64 data URL string when provided.",
            400,
        )

    try:
        parsed_conversation_id = int(conversation_id)
    except (TypeError, ValueError):
        return None, _error_response(40001, "Field 'conversation_id' is required.", 400)

    if recycling_case_id in ("", None):
        parsed_case_id = None
    else:
        try:
            parsed_case_id = int(recycling_case_id)
        except (TypeError, ValueError):
            return None, _error_response(
                40001,
                "Field 'recycling_case_id' must be an integer when provided.",
                400,
            )

    return {
        "conversation_id": parsed_conversation_id,
        "recycling_case_id": parsed_case_id,
        "message": message or "Please audit this completion photo.",
        "image": image_data_url,
    }, None


def _error_response(code: int, message: str, status_code: int):
    return jsonify({"code": code, "message": message, "data": {}}), status_code


@ai_bp.post("/ai/chat")
@jwt_required()
def ai_chat():
    parsed, error_response = _parse_generic_chat_payload()
    if error_response:
        return error_response

    user_id = int(get_jwt_identity())
    try:
        result = complete_routed_chat_message(
            user_id=user_id,
            message=parsed["message"],
            history=parsed["history"],
            image_data_url=parsed["image"],
            conversation_id=parsed["conversation_id"],
            client_context=parsed["client_context"],
        )
    except ValueError as exc:
        message = str(exc)
        http_status = 404 if "not found" in message.lower() else 400
        return _error_response(40001 if http_status == 400 else 40400, message, http_status)
    except OpenRouterConfigError as exc:
        return _error_response(50000, str(exc), 500)
    except Exception as exc:
        return _error_response(50000, f"AI request failed: {exc}", 502)

    return jsonify({"code": 0, "message": "ok", "data": result})


@ai_bp.post("/ai/chat/stream")
@jwt_required()
def ai_chat_stream():
    parsed, error_response = _parse_generic_chat_payload()
    if error_response:
        return error_response

    user_id = int(get_jwt_identity())
    return _json_sse_response(
        lambda: stream_routed_chat_message(
            user_id=user_id,
            message=parsed["message"],
            history=parsed["history"],
            image_data_url=parsed["image"],
            conversation_id=parsed["conversation_id"],
            client_context=parsed["client_context"],
        )
    )


@ai_bp.post("/ai/analyze-image")
def ai_analyze_image():
    parsed, error_response = _parse_recycling_payload()
    if error_response:
        return error_response

    return _json_sse_response(
        lambda: stream_recycling_analysis(
            message=parsed["message"],
            image_data_url=parsed["image"],
            session_id=parsed["session_id"],
            conversation_id=parsed["conversation_id"],
        )
    )


@ai_bp.post("/ai/location-context")
def ai_location_context():
    payload = request.get_json(silent=True) or {}
    try:
        result = store_location_context(payload)
    except ValueError as exc:
        return _error_response(40001, str(exc), 400)
    except Exception as exc:
        return _error_response(50000, f"Location context update failed: {exc}", 502)

    return jsonify({"code": 0, "message": "ok", "data": result})


@ai_bp.post("/ai/chat/resume")
def ai_chat_resume():
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("session_id", "")).strip()
    if not session_id:
        return _error_response(40001, "Field 'session_id' is required.", 400)

    return _json_sse_response(lambda: stream_recycling_resume(session_id=session_id))


@ai_bp.post("/ai/audit-recycling")
@jwt_required()
def ai_audit_recycling():
    parsed, error_response = _parse_audit_payload()
    if error_response:
        return error_response

    return _json_sse_response(
        lambda: stream_recycling_audit(
            conversation_id=parsed["conversation_id"],
            recycling_case_id=parsed["recycling_case_id"],
            message=parsed["message"],
            image_data_url=parsed["image"],
        )
    )


@ai_bp.get("/ai/conversations")
@jwt_required()
def ai_conversations():
    user_id = int(get_jwt_identity())
    page, per_page = _parse_pagination()
    return jsonify(
        {
            "code": 0,
            "message": "ok",
            "data": list_user_conversations(user_id=user_id, page=page, per_page=per_page),
        }
    )


@ai_bp.get("/ai/conversations/<int:conversation_id>/messages")
@jwt_required()
def ai_conversation_messages(conversation_id: int):
    user_id = int(get_jwt_identity())
    try:
        data = get_conversation_messages(user_id=user_id, conversation_id=conversation_id)
    except ValueError as exc:
        return _error_response(40400, str(exc), 404)
    return jsonify({"code": 0, "message": "ok", "data": data})


@ai_bp.delete("/ai/conversations/<int:conversation_id>")
@jwt_required()
def ai_delete_conversation(conversation_id: int):
    user_id = int(get_jwt_identity())
    try:
        data = delete_user_conversation(user_id=user_id, conversation_id=conversation_id)
    except ValueError as exc:
        return _error_response(40400, str(exc), 404)

    return jsonify({"code": 0, "message": "ok", "data": data})
