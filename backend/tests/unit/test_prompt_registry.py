from __future__ import annotations

import pytest

from app.services.ai.prompt_registry import (
    get_prompt_definition,
    get_prompt_version,
    list_prompt_definitions,
)


def test_get_prompt_definition_returns_router_version():
    prompt = get_prompt_definition("router")

    assert prompt["name"] == "router"
    assert prompt["version"] == "router-v1"
    assert prompt["purpose"]
    assert prompt["input_schema"]
    assert prompt["output_schema"]


def test_get_prompt_version_returns_answer_version():
    assert get_prompt_version("general_chat_answer") == "general-chat-answer-v1"


def test_get_prompt_definition_returns_copy():
    prompt = get_prompt_definition("router")
    prompt["version"] = "mutated"

    assert get_prompt_definition("router")["version"] == "router-v1"


def test_list_prompt_definitions_is_sorted_by_name():
    names = [item["name"] for item in list_prompt_definitions()]

    assert names == sorted(names)
    assert {"router", "general_chat_answer"}.issubset(names)


def test_unknown_prompt_raises_key_error():
    with pytest.raises(KeyError):
        get_prompt_definition("missing_prompt")
