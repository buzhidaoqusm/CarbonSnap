"""Reading the AI request bodies, shared by the Flask and FastAPI routes.

Each parser takes the JSON body as a dict (only the keys that were sent) and
raises ApiError with the message the frontend has always shown. Values are
read loosely, as the Flask routes did: a number or null becomes text.
"""

from typing import Any

from app.api.errors import ApiError

GENERIC_ERROR_MESSAGE = "The AI service is temporarily unavailable. Please try again."


def _invalid(message: str) -> ApiError:
    return ApiError(40001, message, 400)


def _optional_int(value: Any, field: str) -> int | None:
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise _invalid(f"Field '{field}' must be an integer when provided.") from exc


def parse_chat(payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message", "")).strip()
    history = payload.get("history", [])
    image_data_url = payload.get("image")
    client_context = payload.get("client_context")

    if not message and not str(image_data_url or "").strip():
        raise _invalid("Field 'message' or 'image' is required.")
    if history is not None and not isinstance(history, list):
        raise _invalid("Field 'history' must be a list when provided.")
    if image_data_url is not None and not isinstance(image_data_url, str):
        raise _invalid("Field 'image' must be a base64 data URL string when provided.")
    if client_context is not None and not isinstance(client_context, dict):
        raise _invalid("Field 'client_context' must be an object when provided.")

    return {
        "message": message,
        "history": history,
        "image_data_url": image_data_url,
        "conversation_id": _optional_int(payload.get("conversation_id"), "conversation_id"),
        "client_context": client_context,
    }


def parse_recycling(payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message", "")).strip()
    prompt = str(payload.get("prompt", "")).strip()
    image_data_url = payload.get("image") or payload.get("image_url")
    raw_session_id = payload.get("session_id")
    if raw_session_id in (None, "", "None", "null"):
        session_id = None
    else:
        session_id = str(raw_session_id).strip() or None

    if image_data_url is not None and not isinstance(image_data_url, str):
        raise _invalid("Field 'image' must be a base64 data URL string when provided.")

    return {
        "message": message or prompt or "Please analyze this recycling item.",
        "image_data_url": image_data_url,
        "session_id": session_id,
        "conversation_id": _optional_int(payload.get("conversation_id"), "conversation_id"),
    }


def parse_audit(payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message", "")).strip()
    image_data_url = payload.get("image") or payload.get("image_url")

    if image_data_url is None:
        raise _invalid("Field 'image' is required.")
    if not isinstance(image_data_url, str):
        raise _invalid("Field 'image' must be a base64 data URL string when provided.")
    raw_conversation_id: Any = payload.get("conversation_id")
    try:
        conversation_id = int(raw_conversation_id)
    except (TypeError, ValueError) as exc:
        raise _invalid("Field 'conversation_id' is required.") from exc

    return {
        "conversation_id": conversation_id,
        "recycling_case_id": _optional_int(payload.get("recycling_case_id"), "recycling_case_id"),
        "message": message or "Please audit this completion photo.",
        "image_data_url": image_data_url,
    }


def parse_session_id(payload: dict[str, Any]) -> str:
    session_id = str(payload.get("session_id", "")).strip()
    if not session_id:
        raise _invalid("Field 'session_id' is required.")
    return session_id
