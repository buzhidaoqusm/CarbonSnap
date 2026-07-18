from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.ai import openrouter_service


class _FakeCompletionsClient:
    def __init__(self, response: object) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


class _FakeChatClient:
    def __init__(self, response: object) -> None:
        self.completions = _FakeCompletionsClient(response)


class _FakeClient:
    def __init__(self, response: object) -> None:
        self.chat = _FakeChatClient(response)


def _make_function_call(call_id: str, name: str, arguments: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _make_completion(
    *,
    content: str | None,
    tool_calls: list[SimpleNamespace] | None,
    finish_reason: str | None = "stop",
    model: str = "openai/gpt-5.2",
    prompt_tokens: int | None = 10,
    completion_tokens: int | None = 5,
    total_tokens: int | None = 15,
) -> SimpleNamespace:
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    return SimpleNamespace(choices=[choice], model=model, usage=usage)


@pytest.fixture()
def patch_headers(monkeypatch):
    monkeypatch.setattr(openrouter_service, "_build_extra_headers", lambda: {})


def _install_client(monkeypatch, response: object) -> _FakeClient:
    fake_client = _FakeClient(response)
    monkeypatch.setattr(openrouter_service, "_get_client", lambda: fake_client)
    return fake_client


def test_tool_calls_are_parsed_and_raw_message_keeps_original_arguments(app, monkeypatch, patch_headers):
    raw_arguments = '{"location": "Dublin", "count": 2}'
    tool_call = _make_function_call("call_1", "get_weather", raw_arguments)
    completion = _make_completion(content=None, tool_calls=[tool_call])
    fake_client = _install_client(monkeypatch, completion)

    with app.app_context():
        result = openrouter_service.complete_with_tools(
            messages=[{"role": "user", "content": "weather?"}],
        )

    assert result["content"] is None
    assert len(result["tool_calls"]) == 1
    parsed = result["tool_calls"][0]
    assert parsed["id"] == "call_1"
    assert parsed["name"] == "get_weather"
    assert parsed["arguments"] == {"location": "Dublin", "count": 2}

    raw_message = result["raw_message"]
    assert raw_message["role"] == "assistant"
    assert raw_message["content"] is None
    assert raw_message["tool_calls"] == [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "get_weather", "arguments": raw_arguments},
        }
    ]
    assert fake_client.chat.completions.calls[0]["messages"] == [
        {"role": "user", "content": "weather?"}
    ]


def test_plain_text_reply_has_no_tool_calls(app, monkeypatch, patch_headers):
    completion = _make_completion(content="Hello there", tool_calls=None)
    _install_client(monkeypatch, completion)

    with app.app_context():
        result = openrouter_service.complete_with_tools(
            messages=[{"role": "user", "content": "hi"}],
        )

    assert result["content"] == "Hello there"
    assert result["tool_calls"] == []
    assert "tool_calls" not in result["raw_message"]
    assert result["raw_message"] == {"role": "assistant", "content": "Hello there"}


def test_tools_none_omits_tools_and_tool_choice_from_payload(app, monkeypatch, patch_headers):
    completion = _make_completion(content="ok", tool_calls=None)
    fake_client = _install_client(monkeypatch, completion)

    with app.app_context():
        openrouter_service.complete_with_tools(
            messages=[{"role": "user", "content": "hi"}],
            tools=None,
        )

    captured_kwargs = fake_client.chat.completions.calls[0]
    assert "tools" not in captured_kwargs
    assert "tool_choice" not in captured_kwargs


def test_empty_tools_list_omits_tools_and_tool_choice_from_payload(app, monkeypatch, patch_headers):
    completion = _make_completion(content="ok", tool_calls=None)
    fake_client = _install_client(monkeypatch, completion)

    with app.app_context():
        openrouter_service.complete_with_tools(
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
        )

    captured_kwargs = fake_client.chat.completions.calls[0]
    assert "tools" not in captured_kwargs
    assert "tool_choice" not in captured_kwargs


def test_non_empty_tools_are_included_with_tool_choice(app, monkeypatch, patch_headers):
    completion = _make_completion(content="ok", tool_calls=None)
    fake_client = _install_client(monkeypatch, completion)

    tools = [
        {
            "type": "function",
            "function": {"name": "get_weather", "parameters": {}},
        }
    ]

    with app.app_context():
        openrouter_service.complete_with_tools(
            messages=[{"role": "user", "content": "hi"}],
            tools=tools,
            tool_choice="required",
        )

    captured_kwargs = fake_client.chat.completions.calls[0]
    assert captured_kwargs["tools"] == tools
    assert captured_kwargs["tool_choice"] == "required"


def test_malformed_tool_call_arguments_parse_to_empty_dict(app, monkeypatch, patch_headers):
    tool_call = _make_function_call("call_2", "get_weather", "{not-valid-json")
    completion = _make_completion(content=None, tool_calls=[tool_call])
    _install_client(monkeypatch, completion)

    with app.app_context():
        result = openrouter_service.complete_with_tools(
            messages=[{"role": "user", "content": "weather?"}],
        )

    assert result["tool_calls"][0]["arguments"] == {}
    assert result["raw_message"]["tool_calls"][0]["function"]["arguments"] == "{not-valid-json"


def test_explicit_timeout_is_passed_through(app, monkeypatch, patch_headers):
    completion = _make_completion(content="ok", tool_calls=None)
    fake_client = _install_client(monkeypatch, completion)

    with app.app_context():
        openrouter_service.complete_with_tools(
            messages=[{"role": "user", "content": "hi"}],
            timeout=12.5,
        )

    captured_kwargs = fake_client.chat.completions.calls[0]
    assert captured_kwargs["timeout"] == 12.5


def test_default_timeout_falls_back_to_app_config(app, monkeypatch, patch_headers):
    completion = _make_completion(content="ok", tool_calls=None)
    fake_client = _install_client(monkeypatch, completion)

    with app.app_context():
        app.config["AI_LLM_TIMEOUT_SECONDS"] = 42
        try:
            openrouter_service.complete_with_tools(
                messages=[{"role": "user", "content": "hi"}],
            )
        finally:
            app.config.pop("AI_LLM_TIMEOUT_SECONDS", None)

    captured_kwargs = fake_client.chat.completions.calls[0]
    assert captured_kwargs["timeout"] == 42.0


def test_usage_model_and_finish_reason_are_reported(app, monkeypatch, patch_headers):
    completion = _make_completion(
        content="ok",
        tool_calls=None,
        finish_reason="stop",
        model="openai/gpt-5.2",
        prompt_tokens=3,
        completion_tokens=4,
        total_tokens=7,
    )
    _install_client(monkeypatch, completion)

    with app.app_context():
        result = openrouter_service.complete_with_tools(
            messages=[{"role": "user", "content": "hi"}],
        )

    assert result["finish_reason"] == "stop"
    assert result["model"] == "openai/gpt-5.2"
    assert result["usage"] == {
        "prompt_tokens": 3,
        "completion_tokens": 4,
        "total_tokens": 7,
    }


def test_no_choices_defaults_to_empty_content_and_tool_calls(app, monkeypatch, patch_headers):
    completion = SimpleNamespace(choices=[], model="openai/gpt-5.2", usage=None)
    _install_client(monkeypatch, completion)

    with app.app_context():
        result = openrouter_service.complete_with_tools(
            messages=[{"role": "user", "content": "hi"}],
        )

    assert result["content"] == ""
    assert result["tool_calls"] == []
    assert result["finish_reason"] is None
    assert result["raw_message"] == {"role": "assistant", "content": None}
