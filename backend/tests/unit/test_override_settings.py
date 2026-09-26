from __future__ import annotations

import pytest

from app.core.config import get_settings


def test_override_reaches_settings_and_legacy_config(app, override_settings):
    override_settings(ai_decision_engine_mode="compat", osm_overpass_fallback_urls_json='["x"]')

    assert get_settings().ai_decision_engine_mode == "compat"
    assert app.config["AI_DECISION_ENGINE_MODE"] == "compat"
    # Derived keys follow the raw setting they come from.
    assert app.config["OSM_OVERPASS_FALLBACK_URLS"] == ["x"]


def test_override_does_not_touch_flask_extension_keys(app, override_settings):
    before = app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    override_settings(ai_trace_enabled=False)
    assert app.config["JWT_ACCESS_TOKEN_EXPIRES"] == before


def test_override_is_undone_after_the_test(app):
    # Runs after the tests above: nothing they set may leak.
    assert get_settings().ai_decision_engine_mode == "llm_first"
    assert app.config["AI_DECISION_ENGINE_MODE"] == "llm_first"


def test_unknown_setting_name_is_rejected(override_settings):
    with pytest.raises(AssertionError, match="ai_trace_enabeld"):
        override_settings(ai_trace_enabeld=False)
