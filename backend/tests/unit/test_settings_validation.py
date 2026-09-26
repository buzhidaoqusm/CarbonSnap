"""What Settings rejects or normalises at startup.

Callers used to guard each read themselves (fall back on a bad mode, clamp a
threshold, treat blank as unset). Those rules now live in Settings, so a bad
value stops the app at startup instead of misbehaving mid-request, and every
caller can trust what it reads.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _settings(monkeypatch, **env: str) -> Settings:
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return Settings(_env_file=None)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("name", "value"),
    [
        # Booleans: the old loader silently used the default.
        ("AI_TRACE_ENABLED", "maybe"),
        # Modes and provider: the old readers fell back to a default, so a typo
        # such as LLM_PROVIDER=qwne quietly called OpenRouter instead.
        ("AI_DECISION_ENGINE_MODE", "rollbackish"),
        ("AI_TOOL_SELECTION_MODE", "banana"),
        ("LLM_PROVIDER", "qwne"),
        # Numbers out of range: the old readers clamped or defaulted them.
        ("AI_DECISION_CONFIDENCE_THRESHOLD", "bad-value"),
        ("AI_DECISION_CONFIDENCE_THRESHOLD", "-1"),
        ("AI_DECISION_CONFIDENCE_THRESHOLD", "1.5"),
        ("AI_DEMO_REPLAY_CHUNK_SIZE", "0"),
        ("AI_LLM_TIMEOUT_SECONDS", "0"),
        ("OSM_OVERPASS_MAX_ATTEMPTS_PER_ENDPOINT", "0"),
    ],
)
def test_invalid_value_fails_at_startup(monkeypatch, name, value):
    with pytest.raises(ValidationError, match=name.lower()):
        _settings(monkeypatch, **{name: value})


@pytest.mark.parametrize(
    ("name", "value", "field", "expected"),
    [
        ("AI_DECISION_ENGINE_VERSION", "   ", "ai_decision_engine_version", "decision-engine-v2"),
        ("LLM_PROVIDER", "  ", "llm_provider", "openrouter"),
        ("AI_DECISION_ENGINE_MODE", " Shadow ", "ai_decision_engine_mode", "shadow"),
        ("AI_TOOL_SELECTION_MODE", "", "ai_tool_selection_mode", ""),
    ],
)
def test_blank_and_padded_values_are_normalised(monkeypatch, name, value, field, expected):
    assert getattr(_settings(monkeypatch, **{name: value}), field) == expected


def test_settings_cannot_be_changed_at_runtime():
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        settings.ai_llm_timeout_seconds = 1  # type: ignore[misc]


def test_env_file_is_read_and_real_environment_wins(monkeypatch, tmp_path):
    # load_app_settings no longer calls load_dotenv: Settings reads ENV_FILE
    # itself. Real environment variables still take precedence, as before.
    from app.core.config import _load_settings, clear_settings_cache

    env_file = tmp_path / "test.env"
    env_file.write_text("AI_MAP_SEARCH_LIMIT=5\nAI_MAP_SEARCH_RADIUS_METERS=900\n")
    monkeypatch.setenv("ENV_FILE", str(env_file))
    monkeypatch.delenv("AI_MAP_SEARCH_LIMIT", raising=False)
    monkeypatch.setenv("AI_MAP_SEARCH_RADIUS_METERS", "1200")

    clear_settings_cache()
    try:
        settings = _load_settings()
    finally:
        clear_settings_cache()

    assert settings.ai_map_search_limit == 5
    assert settings.ai_map_search_radius_meters == 1200
