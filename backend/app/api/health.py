from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    return jsonify(
        {
            "service": "carbonsnap-backend",
            "status": "ok",
            "message": "Backend is running.",
        }
    )
