from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any
from uuid import uuid4

from flask import current_app

_SESSION_STORE: dict[str, dict[str, Any]] = {}
_SESSION_LOCK = Lock()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _ensure_location_state() -> dict[str, Any]:
    return {
        "permission_state": "unknown",
        "location_source": "none",
        "coordinates": None,
        "manual_area": None,
        "normalized_area": None,
        "skip_nearby_search": False,
        "expires_at": None,
    }


def _ensure_session_defaults(session: dict[str, Any]) -> dict[str, Any]:
    session.setdefault("conversation_id", None)
    session.setdefault("recycling_case_id", None)
    return session


def create_or_get_session(session_id: str | None = None) -> dict[str, Any]:
    with _SESSION_LOCK:
        _cleanup_expired_sessions_locked()

        if session_id and session_id in _SESSION_STORE:
            _SESSION_STORE[session_id]["updated_at"] = _utc_now()
            return deepcopy(_ensure_session_defaults(_SESSION_STORE[session_id]))

        session = _build_session(session_id=session_id)
        _SESSION_STORE[session["session_id"]] = _ensure_session_defaults(session)
        return deepcopy(_SESSION_STORE[session["session_id"]])


def update_location_state(
    session_id: str,
    *,
    permission_state: str | None = None,
    location_source: str | None = None,
    coordinates: dict[str, float] | None = None,
    manual_area: str | None = None,
    normalized_area: str | None = None,
    skip_nearby_search: bool | None = None,
    ttl_seconds: int | None = None,
) -> dict[str, Any]:
    with _SESSION_LOCK:
        session = _SESSION_STORE.get(session_id)
        if session is None:
            session = _build_session(session_id=session_id)
            _SESSION_STORE[session_id] = session

        location_state = session.setdefault("location_state", _ensure_location_state())

        if permission_state is not None:
            location_state["permission_state"] = permission_state
        if location_source is not None:
            location_state["location_source"] = location_source
        if coordinates is not None:
            location_state["coordinates"] = coordinates
        if manual_area is not None:
            location_state["manual_area"] = manual_area
        if normalized_area is not None:
            location_state["normalized_area"] = normalized_area
        if skip_nearby_search is not None:
            location_state["skip_nearby_search"] = skip_nearby_search

        if ttl_seconds is not None:
            location_state["expires_at"] = _utc_now() + timedelta(seconds=ttl_seconds)

        session["updated_at"] = _utc_now()
        return deepcopy(session)


def set_workflow_reference(
    session_id: str,
    *,
    conversation_id: int | None = None,
    recycling_case_id: int | None = None,
) -> dict[str, Any]:
    with _SESSION_LOCK:
        session = _SESSION_STORE.get(session_id)
        if session is None:
            session = _build_session(session_id=session_id)
            _SESSION_STORE[session_id] = session

        if conversation_id is not None:
            session["conversation_id"] = conversation_id
        if recycling_case_id is not None:
            session["recycling_case_id"] = recycling_case_id

        session["updated_at"] = _utc_now()
        return deepcopy(_ensure_session_defaults(session))


def get_valid_location_state(session_id: str | None) -> dict[str, Any] | None:
    if not session_id:
        return None

    with _SESSION_LOCK:
        session = _SESSION_STORE.get(session_id)
        if session is None:
            return None

        location_state = session.get("location_state") or _ensure_location_state()
        expires_at = location_state.get("expires_at")
        if expires_at and isinstance(expires_at, datetime) and expires_at < _utc_now():
            session["location_state"] = _ensure_location_state()
            return None

        coordinates = location_state.get("coordinates")
        skip_nearby_search = bool(location_state.get("skip_nearby_search"))
        denied = location_state.get("permission_state") == "denied"

        if coordinates or skip_nearby_search or denied:
            return deepcopy(location_state)

        return None


def set_paused_context(session_id: str, paused_context: dict[str, Any] | None) -> dict[str, Any]:
    with _SESSION_LOCK:
        session = _SESSION_STORE.get(session_id)
        if session is None:
            session = _build_session(session_id=session_id)
            _SESSION_STORE[session_id] = session

        session["paused_context"] = paused_context
        session["updated_at"] = _utc_now()
        return deepcopy(session)


def get_paused_context(session_id: str | None) -> dict[str, Any] | None:
    if not session_id:
        return None

    with _SESSION_LOCK:
        session = _SESSION_STORE.get(session_id)
        if session is None:
            return None
        paused_context = session.get("paused_context")
        return deepcopy(paused_context) if paused_context else None


def clear_paused_context(session_id: str) -> dict[str, Any]:
    return set_paused_context(session_id, None)


def serialize_session(session: dict[str, Any]) -> dict[str, Any]:
    session = _ensure_session_defaults(deepcopy(session))
    location_state = deepcopy(session.get("location_state") or _ensure_location_state())
    expires_at = location_state.get("expires_at")
    if isinstance(expires_at, datetime):
        location_state["expires_at"] = _serialize_datetime(expires_at)

    return {
        "session_id": session.get("session_id"),
        "conversation_id": session.get("conversation_id"),
        "recycling_case_id": session.get("recycling_case_id"),
        "created_at": _serialize_datetime(session.get("created_at")),
        "updated_at": _serialize_datetime(session.get("updated_at")),
        "location_state": location_state,
        "paused_context": deepcopy(session.get("paused_context")),
    }


def _cleanup_expired_sessions_locked() -> None:
    max_idle_hours = int(current_app.config.get("AI_MANUAL_LOCATION_TTL_HOURS", 24))
    cutoff = _utc_now() - timedelta(hours=max_idle_hours)
    expired_session_ids = [
        session_id
        for session_id, session in _SESSION_STORE.items()
        if session.get("updated_at") and session["updated_at"] < cutoff
    ]

    for session_id in expired_session_ids:
        _SESSION_STORE.pop(session_id, None)


def _build_session(session_id: str | None = None) -> dict[str, Any]:
    new_session_id = session_id or str(uuid4())
    return {
        "session_id": new_session_id,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "location_state": _ensure_location_state(),
        "paused_context": None,
        "conversation_id": None,
        "recycling_case_id": None,
    }
