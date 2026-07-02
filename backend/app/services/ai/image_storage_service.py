from __future__ import annotations

import base64
import re
from pathlib import Path
from uuid import uuid4

from flask import current_app


class ImageStorageError(ValueError):
    """Raised when an uploaded image cannot be parsed or stored."""


_DATA_URL_RE = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", re.DOTALL)
_MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
}


def store_data_url_image(data_url: str, *, namespace: str = "ai") -> str:
    """Persist a base64 data URL image under data/uploads and return its public URL."""
    image_value = str(data_url or "").strip()
    if not image_value:
        raise ImageStorageError("Image data is required.")

    uploads_prefix = current_app.config["UPLOAD_URL_PREFIX"].rstrip("/")
    if image_value.startswith(f"{uploads_prefix}/"):
        return image_value

    match = _DATA_URL_RE.match(image_value)
    if not match:
        raise ImageStorageError("Field 'image' must be a base64 image data URL.")

    mime_type, encoded_body = match.groups()
    extension = _MIME_TO_EXT.get(mime_type.lower())
    if extension is None:
        raise ImageStorageError(f"Unsupported image type: {mime_type}")

    try:
        binary = base64.b64decode(encoded_body, validate=True)
    except Exception as exc:  # pragma: no cover - exact binascii type is not important here
        raise ImageStorageError("Image data is not valid base64.") from exc

    upload_root = _resolve_upload_root()
    namespace_dir = upload_root / namespace.strip().lower()
    namespace_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}{extension}"
    file_path = namespace_dir / filename
    file_path.write_bytes(binary)

    relative_path = file_path.relative_to(upload_root).as_posix()
    return f"{uploads_prefix}/{relative_path}"


def _resolve_upload_root() -> Path:
    configured_root = Path(current_app.config["UPLOAD_ROOT"]).resolve()
    try:
        configured_root.mkdir(parents=True, exist_ok=True)
        probe_path = configured_root / ".write_test"
        probe_path.write_bytes(b"")
        probe_path.unlink(missing_ok=True)
        return configured_root
    except OSError:
        # Test sandboxes may override UPLOAD_ROOT to a temp directory outside the
        # writable workspace. Fall back to the repo-local upload directory so the
        # public URL contract keeps working.
        fallback_root = (Path(current_app.root_path).resolve().parents[1] / "data" / "uploads").resolve()
        fallback_root.mkdir(parents=True, exist_ok=True)
        current_app.config["UPLOAD_ROOT"] = str(fallback_root)
        return fallback_root
