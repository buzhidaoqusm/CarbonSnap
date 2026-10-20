from __future__ import annotations

import pytest

from app.core.config import get_settings


def test_override_reaches_settings(override_settings):
    override_settings(ai_decision_engine_mode="compat")

    assert get_settings().ai_decision_engine_mode == "compat"


def test_override_is_undone_after_the_test():
    # Runs after the test above: nothing it set may leak.
    assert get_settings().ai_decision_engine_mode == "llm_first"


def test_unknown_setting_name_is_rejected(override_settings):
    with pytest.raises(AssertionError, match="ai_trace_enabeld"):
        override_settings(ai_trace_enabeld=False)
