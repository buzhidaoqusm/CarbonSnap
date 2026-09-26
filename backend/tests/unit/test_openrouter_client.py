from __future__ import annotations

from app.services.ai import openrouter_service


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
