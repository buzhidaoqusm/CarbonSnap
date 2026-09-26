"""Pins what configuration loading produces, so rewriting it cannot drift.

The snapshot in tests/fixtures/config_snapshot.json was recorded from the
original os.getenv-based loader. Whatever replaces it must turn the same
environment into the same app.config values: defaults, explicit overrides,
blank values and malformed JSON, including the quirks (trimming, lowercasing,
blank-means-default) that callers have come to rely on.

To re-record after an intentional change:

    UPDATE_CONFIG_SNAPSHOT=1 uv run pytest tests/unit/test_config_parity.py
"""

from __future__ import annotations

import json
import os
from datetime import timedelta
from pathlib import Path

import pytest
from flask import Flask

from app.config.settings import load_app_settings
from app.core.config import clear_settings_cache

SNAPSHOT = Path(__file__).resolve().parents[1] / "fixtures" / "config_snapshot.json"
REPO_ROOT = Path(__file__).resolve().parents[3]

ENV_VARS = [
    "AI_AGENT_MAX_ITERATIONS",
    "AI_BROWSER_LOCATION_TTL_MINUTES",
    "AI_DECISION_CONFIDENCE_THRESHOLD",
    "AI_DECISION_ENGINE_MODE",
    "AI_DECISION_ENGINE_VERSION",
    "AI_DEMO_REPLAY_CHUNK_SIZE",
    "AI_DEMO_REPLAY_ENABLED",
    "AI_EMISSION_FACTORS_JSON",
    "AI_GRAPH_AGENT_ENABLED",
    "AI_LLM_AUX_TIMEOUT_SECONDS",
    "AI_LLM_MAX_RETRIES",
    "AI_LLM_TIMEOUT_SECONDS",
    "AI_MANUAL_LOCATION_TTL_HOURS",
    "AI_MAP_SEARCH_LIMIT",
    "AI_MAP_SEARCH_RADIUS_METERS",
    "AI_NEO4J_GRAPHRAG_ENABLED",
    "AI_OSM_RECYCLING_TAGS_JSON",
    "AI_PROMPTOPS_SHADOW_ENABLED",
    "AI_SHORT_TERM_MEMORY_TURNS",
    "AI_TOOL_CALLING_AGENT_ENABLED",
    "AI_TOOL_SELECTION_MODE",
    "AI_TOOL_SELECTION_SHADOW_LOG",
    "AI_TRACE_ENABLED",
    "AI_TRACE_INCLUDE_RETRIEVAL_EXCERPTS",
    "DATABASE_URL",
    "FORUM_RAG_CHUNK_OVERLAP_TOKENS",
    "FORUM_RAG_CHUNK_TARGET_TOKENS",
    "FORUM_RAG_EMBEDDING_MODEL",
    "FORUM_RAG_FAISS_DIR",
    "FORUM_RAG_FINAL_TOP_K",
    "FORUM_RAG_KEYWORD_TOP_K",
    "FORUM_RAG_VECTOR_TOP_K",
    "JWT_SECRET_KEY",
    "LLM_PROVIDER",
    "NEO4J_PASSWORD",
    "NEO4J_URI",
    "NEO4J_USERNAME",
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "OPENROUTER_MODEL",
    "OPENROUTER_SITE_NAME",
    "OPENROUTER_SITE_URL",
    "OSM_NOMINATIM_URL",
    "OSM_OVERPASS_CONNECT_TIMEOUT_SECONDS",
    "OSM_OVERPASS_FALLBACK_URLS_JSON",
    "OSM_OVERPASS_MAX_ATTEMPTS_PER_ENDPOINT",
    "OSM_OVERPASS_RETRY_BACKOFF_MS",
    "OSM_OVERPASS_TIMEOUT_SECONDS",
    "OSM_OVERPASS_URL",
    "OSM_USER_AGENT",
    "QWEN_API_KEY",
    "QWEN_BASE_URL",
    "QWEN_MODEL",
    "UPLOAD_ROOT",
    "UPLOAD_URL_PREFIX",
]

# Every variable set to a non-default value. Padding and odd casing check the
# trimming and lowercasing the old loader did.
OVERRIDES = {
    "AI_AGENT_MAX_ITERATIONS": " 7 ",
    "AI_BROWSER_LOCATION_TTL_MINUTES": "15",
    "AI_DECISION_CONFIDENCE_THRESHOLD": "0.8",
    "AI_DECISION_ENGINE_MODE": " COMPAT ",
    "AI_DECISION_ENGINE_VERSION": " decision-engine-v9 ",
    "AI_DEMO_REPLAY_CHUNK_SIZE": "64",
    "AI_DEMO_REPLAY_ENABLED": "on",
    "AI_EMISSION_FACTORS_JSON": '{"Plastic": 2, "default": "0.5"}',
    "AI_GRAPH_AGENT_ENABLED": "yes",
    "AI_LLM_AUX_TIMEOUT_SECONDS": "5",
    "AI_LLM_MAX_RETRIES": "0",
    "AI_LLM_TIMEOUT_SECONDS": "30.5",
    "AI_MANUAL_LOCATION_TTL_HOURS": "48",
    "AI_MAP_SEARCH_LIMIT": "3",
    "AI_MAP_SEARCH_RADIUS_METERS": "500",
    "AI_NEO4J_GRAPHRAG_ENABLED": "TRUE",
    "AI_OSM_RECYCLING_TAGS_JSON": (
        '[{"key": "amenity", "value": "bin"}, {"key": "only-key"}, "not-a-dict"]'
    ),
    "AI_PROMPTOPS_SHADOW_ENABLED": "1",
    "AI_SHORT_TERM_MEMORY_TURNS": "4",
    "AI_TOOL_CALLING_AGENT_ENABLED": "true",
    "AI_TOOL_SELECTION_MODE": " Shadow ",
    "AI_TOOL_SELECTION_SHADOW_LOG": " /var/log/shadow.jsonl ",
    "AI_TRACE_ENABLED": "off",
    "AI_TRACE_INCLUDE_RETRIEVAL_EXCERPTS": "no",
    "DATABASE_URL": "postgresql+psycopg://u:p@db:5432/app",
    "FORUM_RAG_CHUNK_OVERLAP_TOKENS": "10",
    "FORUM_RAG_CHUNK_TARGET_TOKENS": "200",
    "FORUM_RAG_EMBEDDING_MODEL": " embed-x ",
    "FORUM_RAG_FAISS_DIR": "<tmp>/faiss",
    "FORUM_RAG_FINAL_TOP_K": "2",
    "FORUM_RAG_KEYWORD_TOP_K": "5",
    "FORUM_RAG_VECTOR_TOP_K": "6",
    "JWT_SECRET_KEY": "s3cret",
    "LLM_PROVIDER": " Qwen ",
    "NEO4J_PASSWORD": " pw ",
    "NEO4J_URI": " bolt://neo:7687 ",
    "NEO4J_USERNAME": " neo ",
    "OPENROUTER_API_KEY": " or-key ",
    "OPENROUTER_BASE_URL": " https://or.example/v1 ",
    "OPENROUTER_MODEL": " model-x ",
    "OPENROUTER_SITE_NAME": " Site ",
    "OPENROUTER_SITE_URL": " https://site.example ",
    "OSM_NOMINATIM_URL": " https://nominatim.example ",
    "OSM_OVERPASS_CONNECT_TIMEOUT_SECONDS": "2",
    "OSM_OVERPASS_FALLBACK_URLS_JSON": (
        '["https://a.example", " ", "https://overpass.example/api", "https://b.example"]'
    ),
    "OSM_OVERPASS_MAX_ATTEMPTS_PER_ENDPOINT": "4",
    "OSM_OVERPASS_RETRY_BACKOFF_MS": "100",
    "OSM_OVERPASS_TIMEOUT_SECONDS": "12.5",
    "OSM_OVERPASS_URL": " https://overpass.example/api ",
    "OSM_USER_AGENT": " Agent/1 ",
    "QWEN_API_KEY": " qwen-key ",
    "QWEN_BASE_URL": " https://qwen.example/v1 ",
    "QWEN_MODEL": " qwen-max ",
    "UPLOAD_ROOT": "<tmp>/uploads",
    "UPLOAD_URL_PREFIX": " /files ",
}

# Blank values for the variables where the old loader treated blank sensibly
# (fell back to a default, or kept an empty string). Variables where blank
# crashed it, such as the integer ones without an `or` fallback, are left out.
BLANKS = dict.fromkeys(
    [
        "AI_AGENT_MAX_ITERATIONS",
        "AI_DECISION_ENGINE_MODE",
        "AI_DECISION_ENGINE_VERSION",
        "AI_DEMO_REPLAY_ENABLED",
        "AI_EMISSION_FACTORS_JSON",
        "AI_GRAPH_AGENT_ENABLED",
        "AI_LLM_AUX_TIMEOUT_SECONDS",
        "AI_LLM_MAX_RETRIES",
        "AI_LLM_TIMEOUT_SECONDS",
        "AI_OSM_RECYCLING_TAGS_JSON",
        "AI_TOOL_SELECTION_MODE",
        "AI_TRACE_ENABLED",
        "LLM_PROVIDER",
        "OPENROUTER_API_KEY",
        "OSM_OVERPASS_FALLBACK_URLS_JSON",
        "UPLOAD_URL_PREFIX",
    ],
    "",
)

MALFORMED_JSON = {
    "AI_EMISSION_FACTORS_JSON": "{not json",
    "AI_OSM_RECYCLING_TAGS_JSON": "[oops",
    "OSM_OVERPASS_FALLBACK_URLS_JSON": '{"not": "a list"}',
}

SCENARIOS = {
    "defaults": {},
    "overrides": OVERRIDES,
    "blanks": BLANKS,
    "malformed_json": MALFORMED_JSON,
}


def _normalize(value: object, tmp: Path) -> object:
    """Make values comparable across machines: no absolute paths, JSON types."""
    if isinstance(value, timedelta):
        return {"timedelta_seconds": value.total_seconds()}
    if isinstance(value, str):
        return value.replace(str(tmp), "<tmp>").replace(str(REPO_ROOT), "<repo>").replace("\\", "/")
    if isinstance(value, dict):
        return {key: _normalize(item, tmp) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item, tmp) for item in value]
    return value


def _load_config(monkeypatch, tmp_path: Path, env: dict[str, str]) -> dict[str, object]:
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    empty_env_file = tmp_path / "empty.env"
    empty_env_file.write_text("")
    monkeypatch.setenv("ENV_FILE", str(empty_env_file))
    for name, value in env.items():
        monkeypatch.setenv(name, value.replace("<tmp>", str(tmp_path)))

    # Settings are parsed once and cached; each scenario needs a fresh parse.
    clear_settings_cache()
    flask_app = Flask("config-parity")
    try:
        load_app_settings(flask_app)
    finally:
        clear_settings_cache()
    loaded = {key: flask_app.config[key] for key in sorted(flask_app.config)}
    # Only what load_app_settings owns: drop Flask's built-in defaults.
    baseline = Flask("baseline").config
    owned = {key: value for key, value in loaded.items() if key not in baseline}
    return {key: _normalize(value, tmp_path) for key, value in owned.items()}


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_config_matches_snapshot(scenario, monkeypatch, tmp_path):
    produced = _load_config(monkeypatch, tmp_path, SCENARIOS[scenario])

    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8")) if SNAPSHOT.exists() else {}
    if os.getenv("UPDATE_CONFIG_SNAPSHOT"):
        snapshot[scenario] = produced
        SNAPSHOT.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip("snapshot re-recorded")

    assert scenario in snapshot, "no snapshot recorded; run with UPDATE_CONFIG_SNAPSHOT=1"
    assert produced == snapshot[scenario]
