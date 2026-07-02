from flask import jsonify


def ok(data=None, status: int = 200):
    """Return a successful JSON envelope with optional HTTP status."""
    return jsonify({"code": 0, "message": "ok", "data": data or {}}), status


def fail(code: int, message: str, http_status: int = 400):
    """Return an error JSON envelope."""
    return jsonify({"code": code, "message": message, "data": {}}), http_status
