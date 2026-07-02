from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.ai.memory_service import (
    create_manual_memory_item,
    delete_memory_item,
    list_memory_payload,
    serialize_memory_item,
    update_manual_memory_item,
)

ai_memory_bp = Blueprint("ai_memory", __name__)


def _error_response(code: int, message: str, status_code: int):
    return jsonify({"code": code, "message": message, "data": {}}), status_code


def _parse_memory_payload():
    payload = request.get_json(silent=True) or {}
    memory_type = str(payload.get("memory_type", "")).strip()
    memory_key = str(payload.get("memory_key", "")).strip()
    value = payload.get("value")

    if not memory_type:
        return None, _error_response(40001, "Field 'memory_type' is required.", 400)
    if not memory_key:
        return None, _error_response(40001, "Field 'memory_key' is required.", 400)
    if not isinstance(value, dict) or not value:
        return None, _error_response(40001, "Field 'value' must be a non-empty object.", 400)

    return {
        "memory_type": memory_type,
        "memory_key": memory_key,
        "value": value,
    }, None


@ai_memory_bp.get("/ai/memory")
@jwt_required()
def get_ai_memory():
    user_id = int(get_jwt_identity())
    return jsonify({"code": 0, "message": "ok", "data": list_memory_payload(user_id)})


@ai_memory_bp.post("/ai/memory")
@jwt_required()
def create_ai_memory():
    parsed, error_response = _parse_memory_payload()
    if error_response:
        return error_response

    user_id = int(get_jwt_identity())
    try:
        item = create_manual_memory_item(user_id=user_id, **parsed)
    except ValueError as exc:
        return _error_response(40001, str(exc), 400)

    return jsonify(
        {
            "code": 0,
            "message": "ok",
            "data": {
                "item": serialize_memory_item(item),
                "summary": list_memory_payload(user_id)["summary"],
            },
        }
    )


@ai_memory_bp.patch("/ai/memory/<int:item_id>")
@jwt_required()
def update_ai_memory(item_id: int):
    payload = request.get_json(silent=True) or {}
    user_id = int(get_jwt_identity())

    try:
        item = update_manual_memory_item(
            item_id=item_id,
            user_id=user_id,
            memory_type=str(payload["memory_type"]).strip() if "memory_type" in payload else None,
            memory_key=str(payload["memory_key"]).strip() if "memory_key" in payload else None,
            value=payload.get("value") if "value" in payload else None,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        return _error_response(40400 if status_code == 404 else 40001, message, status_code)

    return jsonify(
        {
            "code": 0,
            "message": "ok",
            "data": {
                "item": serialize_memory_item(item),
                "summary": list_memory_payload(user_id)["summary"],
            },
        }
    )


@ai_memory_bp.delete("/ai/memory/<int:item_id>")
@jwt_required()
def delete_ai_memory(item_id: int):
    user_id = int(get_jwt_identity())
    try:
        item = delete_memory_item(item_id=item_id, user_id=user_id)
    except ValueError as exc:
        return _error_response(40400, str(exc), 404)

    return jsonify(
        {
            "code": 0,
            "message": "ok",
            "data": {
                "item": serialize_memory_item(item),
                "summary": list_memory_payload(user_id)["summary"],
            },
        }
    )
