from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.ai import intent_router, memory_extractor, openrouter_service


def test_client_applies_configured_timeout(app):
    # Regression: AI_LLM_TIMEOUT_SECONDS used to reach only complete_with_tools,
    # so the main chat path ran on the SDK's 600 s default and a hanging
    # provider held a worker until gunicorn killed it.
    with app.app_context():
        app.config["OPENROUTER_API_KEY"] = "test-key"
        app.config["AI_LLM_TIMEOUT_SECONDS"] = 42

        client = openrouter_service._get_client()

    assert client.timeout.read == 42.0
    assert client.timeout.connect == openrouter_service.LLM_CONNECT_TIMEOUT_SECONDS


class _RecordingClient:
    """Stands in for OpenAI: records with_options() and create() calls."""

    def __init__(self) -> None:
        self.options: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def with_options(self, **kwargs):
        self.options.append(kwargs)
        return self

    def _create(self, **kwargs):
        return SimpleNamespace(choices=[], model="m", usage=None)


@pytest.fixture
def recording_client(app, monkeypatch):
    client = _RecordingClient()
    monkeypatch.setattr(openrouter_service, "_get_client", lambda: client)
    monkeypatch.setattr(openrouter_service, "_build_extra_headers", lambda: {})
    return client


def test_auxiliary_call_uses_short_timeout_without_retries(app, recording_client):
    with app.app_context():
        app.config["AI_LLM_AUX_TIMEOUT_SECONDS"] = 7
        openrouter_service.complete_text(user_message="hi", auxiliary=True)

    (options,) = recording_client.options
    assert options["timeout"].read == 7.0
    assert options["max_retries"] == 0


def test_regular_call_keeps_client_defaults(app, recording_client):
    with app.app_context():
        openrouter_service.complete_text(user_message="hi")

    assert recording_client.options == []


@pytest.mark.parametrize(
    ("module", "call"),
    [
        (
            intent_router,
            lambda: intent_router.classify_intent_detailed(
                message="hi",
                image_data_url=None,
                recent_history=[],
                case_summaries=[],
                conversation_state=None,
                prompt_memory=None,
                allow_business_fallback=True,
            ),
        ),
        (
            memory_extractor,
            lambda: memory_extractor.extract_explicit_memory_candidates_detailed(
                "I prefer short answers.",
                allow_heuristic_fallback=True,
            ),
        ),
    ],
    ids=["router", "memory_extractor"],
)
def test_pre_answer_calls_are_auxiliary(app, monkeypatch, module, call):
    seen: dict = {}

    def fake_diagnostic(**kwargs):
        seen.update(kwargs)
        return {"payload": None, "raw_reply": None, "error": "x", "model": None, "usage": {}}

    monkeypatch.setattr(module, "complete_json_diagnostic", fake_diagnostic)
    with app.app_context():
        call()

    assert seen.get("auxiliary") is True


def test_title_generation_is_auxiliary(app, monkeypatch):
    seen: dict = {}

    def fake_complete_text(**kwargs):
        seen.update(kwargs)
        return {"reply": "Bottle Recycling"}

    monkeypatch.setattr(openrouter_service, "complete_text", fake_complete_text)
    with app.app_context():
        openrouter_service.generate_conversation_title(user_message="plastic bottle?")

    assert seen.get("auxiliary") is True
