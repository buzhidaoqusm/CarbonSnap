from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, send_file

uploads_bp = Blueprint("uploads", __name__)


@uploads_bp.get("/uploads/<path:relative_path>")
def get_uploaded_file(relative_path: str):
    upload_root = Path(current_app.config["UPLOAD_ROOT"]).resolve()
    candidate = (upload_root / relative_path).resolve()

    if not str(candidate).startswith(str(upload_root)) or not candidate.is_file():
        return {"code": 40400, "message": "Uploaded file not found.", "data": {}}, 404

    return send_file(candidate)
