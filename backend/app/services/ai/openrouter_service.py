from __future__ import annotations

import json
import re
from collections.abc import Generator, Iterable
from typing import Any

from flask import current_app
from openai import OpenAI, Timeout

# Reaching the provider should take well under a second; waiting the full read
# timeout to learn it is unreachable only holds the worker longer.
LLM_CONNECT_TIMEOUT_SECONDS = 5.0


class OpenRouterConfigError(RuntimeError):
    pass


def _get_provider_name() -> str:
    provider = (
        str(current_app.config.get("LLM_PROVIDER", "openrouter") or "openrouter").strip().lower()
    )
    return provider or "openrouter"


def _get_provider_settings() -> dict[str, str]:
    provider = _get_provider_name()

    if provider == "qwen":
        return {
            "provider": "qwen",
            "api_key": str(current_app.config.get("QWEN_API_KEY", "") or "").strip(),
            "base_url": str(
                current_app.config.get(
                    "QWEN_BASE_URL",
                    "https://dashscope.aliyuncs.com/compatible-mode/v1",
                )
                or ""
            ).strip(),
            "model": str(current_app.config.get("QWEN_MODEL", "qwen-plus") or "").strip(),
        }

    return {
        "provider": "openrouter",
        "api_key": str(current_app.config.get("OPENROUTER_API_KEY", "") or "").strip(),
        "base_url": str(
            current_app.config.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1") or ""
        ).strip(),
        "model": str(current_app.config.get("OPENROUTER_MODEL", "openai/gpt-5.2") or "").strip(),
    }


def _get_client() -> OpenAI:
    settings = _get_provider_settings()
    api_key = settings["api_key"]
    if not api_key:
        raise OpenRouterConfigError(f"{settings['provider'].upper()} API key is not configured.")

    # Set on the client so every call gets it; without it the SDK waits up to
    # 600 s. For streams the read timeout bounds the gap between chunks, not
    # the whole response, so long answers are not cut off.
    read_timeout = float(current_app.config.get("AI_LLM_TIMEOUT_SECONDS", 60) or 60)
    return OpenAI(
        base_url=settings["base_url"],
        api_key=api_key,
        max_retries=int(current_app.config.get("AI_LLM_MAX_RETRIES", 2) or 0),
        timeout=Timeout(read_timeout, connect=LLM_CONNECT_TIMEOUT_SECONDS),
    )


def _build_extra_headers() -> dict[str, str]:
    if _get_provider_name() != "openrouter":
        return {}

    site_url = current_app.config.get("OPENROUTER_SITE_URL", "")
    site_name = current_app.config.get("OPENROUTER_SITE_NAME", "")

    extra_headers: dict[str, str] = {}
    if site_url:
        extra_headers["HTTP-Referer"] = site_url
    if site_name:
        extra_headers["X-OpenRouter-Title"] = site_name
    return extra_headers


def _sanitize_history(history: list[dict[str, Any]]) -> list[dict[str, str]]:
    allowed_roles = {"system", "user", "assistant"}
    cleaned_messages: list[dict[str, str]] = []

    for item in history:
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role in allowed_roles and content:
            cleaned_messages.append({"role": role, "content": content})

    return cleaned_messages


def history_from_message_records(messages: Iterable[Any]) -> list[dict[str, str]]:
    """Convert persisted message rows into OpenRouter chat history entries."""
    allowed_roles = {"system", "user", "assistant"}
    history: list[dict[str, str]] = []

    for item in messages:
        role = str(getattr(item, "role", "")).strip().lower()
        if role not in allowed_roles:
            continue

        content_text = getattr(item, "content_text", None)
        content_json = getattr(item, "content_json", None)
        content = (
            content_text if isinstance(content_text, str) and content_text.strip() else content_json
        )
        if not isinstance(content, str):
            continue

        cleaned = content.strip()
        if cleaned:
            history.append({"role": role, "content": cleaned})

    return history


def _build_user_content(
    user_message: str, image_data_url: str | None
) -> str | list[dict[str, Any]]:
    if not image_data_url:
        return user_message

    image_value = image_data_url.strip()
    if not image_value.startswith("data:image/"):
        raise ValueError("Field 'image' must be a base64 data URL like data:image/png;base64,...")

    text_value = str(user_message or "").strip() or "Please analyze this image."
    return [
        {"type": "text", "text": text_value},
        {"type": "image_url", "image_url": {"url": image_value}},
    ]


def build_messages(
    *,
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    system_prompt: str | None = None,
    prompt_memory: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []

    combined_system_prompt = _combine_system_prompt(
        system_prompt=system_prompt,
        prompt_memory=prompt_memory,
    )
    if combined_system_prompt:
        messages.append({"role": "system", "content": combined_system_prompt})

    if history:
        messages.extend(_sanitize_history(history))

    user_content = _build_user_content(user_message=user_message, image_data_url=image_data_url)
    messages.append({"role": "user", "content": user_content})
    return messages


def _normalize_embedding_input(text: str) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalized:
        raise ValueError("Embedding input must not be blank.")
    return normalized


def _get_embedding_model() -> str:
    model = str(current_app.config.get("FORUM_RAG_EMBEDDING_MODEL", "") or "").strip()
    if model:
        return model
    return "text-embedding-v3"


def _send_embedding_request(*, inputs: list[str], model: str | None = None) -> Any:
    client = _get_client()
    request_payload: dict[str, Any] = {
        "model": model or _get_embedding_model(),
        "input": inputs,
    }

    extra_headers = _build_extra_headers()
    if extra_headers:
        request_payload["extra_headers"] = extra_headers

    return client.embeddings.create(**request_payload)


def _parse_embedding_response(response: Any) -> list[list[float]]:
    data = getattr(response, "data", None)
    if not isinstance(data, list):
        raise ValueError("Embedding provider returned no embedding data.")

    ordered: list[list[float] | None] = [None] * len(data)
    for item in data:
        index = getattr(item, "index", None)
        embedding = getattr(item, "embedding", None)
        if index is None or not isinstance(embedding, list):
            continue

        try:
            ordered[int(index)] = [float(value) for value in embedding]
        except (TypeError, ValueError):
            continue

    embeddings = [item for item in ordered if item is not None]
    if len(embeddings) != len(data):
        raise ValueError("Embedding provider returned an incomplete embedding payload.")
    return embeddings


def embed_texts(
    texts: list[str],
    *,
    model: str | None = None,
) -> list[list[float]]:
    cleaned_inputs = [_normalize_embedding_input(text) for text in texts]
    if not cleaned_inputs:
        raise ValueError("At least one text is required for embedding.")

    response = _send_embedding_request(inputs=cleaned_inputs, model=model)
    return _parse_embedding_response(response)


def embed_text(
    text: str,
    *,
    model: str | None = None,
) -> list[float]:
    return embed_texts([text], model=model)[0]


def _combine_system_prompt(
    *,
    system_prompt: str | None = None,
    prompt_memory: dict[str, Any] | None = None,
) -> str | None:
    memory_block = ""
    if prompt_memory:
        compact_memory = {
            key: value for key, value in prompt_memory.items() if value not in (None, {}, [])
        }
        if compact_memory:
            memory_block = (
                "Memory summary: "
                f"{json.dumps(compact_memory, ensure_ascii=False, separators=(',', ':'))}"
            )

    parts = [part for part in [system_prompt, memory_block] if part]
    if not parts:
        return None
    return "\n\n".join(parts)


_BAD_TITLE_HINTS = {
    "rinse",
    "place",
    "remove",
    "check",
    "use",
    "call",
    "confirm",
    "separate",
    "clean",
    "identify",
    "consider",
    "retry",
    "skip",
    "enter",
    "allow",
    "proceed",
    "guide",
    "look",
    "let",
    "know",
}

_TITLE_SMALL_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "for",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def _clean_title_candidate(text: str) -> str:
    candidate = str(text or "").strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:[a-zA-Z]+)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
    candidate = candidate.splitlines()[0].strip()
    candidate = candidate.strip(" .,!?:;\"'`-_#")
    candidate = re.sub(r"\s+", " ", candidate)
    return candidate


def _to_title_case(text: str) -> str:
    words = text.split()
    converted: list[str] = []
    for index, word in enumerate(words):
        if not word:
            continue
        if word.isupper() and len(word) <= 5:
            converted.append(word)
            continue
        lowered = word.lower()
        if index > 0 and lowered in _TITLE_SMALL_WORDS:
            converted.append(lowered)
            continue
        converted.append(lowered.capitalize())
    return " ".join(converted)


def _is_valid_conversation_title(title: str) -> bool:
    candidate = _clean_title_candidate(title)
    if not candidate:
        return False
    if any(token in candidate for token in ("\n", ".", "!", "?", ":", ";", "(", ")", "#", "*")):
        return False

    words = candidate.split()
    if len(words) < 2 or len(words) > 5:
        return False

    lowered_words = [re.sub(r"[^a-z]", "", word.lower()) for word in words]
    if any(word in _BAD_TITLE_HINTS for word in lowered_words if word):
        return False

    lowered = candidate.lower()
    if lowered.startswith(
        ("how ", "what ", "why ", "when ", "where ", "can ", "should ", "please ")
    ):
        return False

    return True


def generate_conversation_title(
    *,
    user_message: str,
    image_data_url: str | None = None,
    fallback_title: str = "New chat",
) -> str:
    prompt = (
        "Generate a very short English chat title based only on the user's first request. "
        "Output only one title in Title Case. Use 2 to 5 words. "
        "Prefer an item-plus-intent title such as Tea Bottle Recycling, Plastic Bottle Recycling, "
        "or Glass Jar Recycling. Do not write a sentence, instruction, step, answer, or explanation. "
        "No quotes. No markdown. No punctuation."
    )

    try:
        response = complete_text(
            user_message=user_message,
            image_data_url=image_data_url,
            system_prompt=prompt,
        )
        title = _clean_title_candidate(str(response.get("reply", "")))
        if _is_valid_conversation_title(title):
            return _to_title_case(title)[:60]
    except Exception:
        pass

    normalized = " ".join(str(user_message or "").split())
    if normalized:
        cleaned = re.sub(r"[^A-Za-z0-9 ]+", " ", normalized).strip()
        lowered = cleaned.lower()
        if lowered.startswith(
            ("how ", "what ", "why ", "when ", "where ", "can ", "should ", "please ")
        ):
            return fallback_title
        if "bottle" in lowered:
            return "Bottle Recycling Help"
        if "aluminum can" in lowered or "metal can" in lowered or "tin can" in lowered:
            return "Can Recycling Help"
        if "paper" in lowered:
            return "Paper Recycling Help"
        if "plastic" in lowered:
            return "Plastic Recycling Help"
        if "glass" in lowered:
            return "Glass Recycling Help"
        words = cleaned.split()[:4]
        if len(words) >= 2:
            return _to_title_case(" ".join(words))[:60]
    return fallback_title


def _extract_delta_text(delta_content: Any) -> str:
    if isinstance(delta_content, str):
        return delta_content

    if isinstance(delta_content, list):
        parts: list[str] = []
        for item in delta_content:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type in {"text", "output_text"}:
                part = item.get("text") or item.get("content")
                if isinstance(part, str):
                    parts.append(part)
        return "".join(parts)

    return ""


def _send_completion_request(
    *,
    messages: list[dict[str, Any]],
    stream: bool,
) -> Any:
    client = _get_client()
    model = _get_provider_settings()["model"]

    request_payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }

    extra_headers = _build_extra_headers()
    if extra_headers:
        request_payload["extra_headers"] = extra_headers

    return client.chat.completions.create(**request_payload)


def complete_with_tools(
    *,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str = "auto",
    timeout: float | None = None,
) -> dict[str, Any]:
    client = _get_client()
    model = _get_provider_settings()["model"]

    request_payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    if tools:
        request_payload["tools"] = tools
        request_payload["tool_choice"] = tool_choice

    extra_headers = _build_extra_headers()
    if extra_headers:
        request_payload["extra_headers"] = extra_headers

    effective_timeout = (
        timeout
        if timeout is not None
        else float(current_app.config.get("AI_LLM_TIMEOUT_SECONDS", 60) or 60)
    )
    request_payload["timeout"] = effective_timeout

    completion = client.chat.completions.create(**request_payload)

    choices = getattr(completion, "choices", None) or []
    if choices:
        message = choices[0].message
        finish_reason = getattr(choices[0], "finish_reason", None) or None
        raw_content = getattr(message, "content", None)
        raw_tool_calls = getattr(message, "tool_calls", None) or []
    else:
        finish_reason = None
        raw_content = ""
        raw_tool_calls = []

    tool_calls: list[dict[str, Any]] = []
    for tool_call in raw_tool_calls:
        raw_arguments = tool_call.function.arguments
        try:
            parsed_arguments = json.loads(raw_arguments)
        except (TypeError, ValueError):
            parsed_arguments = {}
        tool_calls.append(
            {
                "id": tool_call.id,
                "name": tool_call.function.name,
                "arguments": parsed_arguments,
            }
        )

    if raw_content:
        content: str | None = str(raw_content)
    elif tool_calls:
        content = None
    else:
        content = raw_content

    usage = getattr(completion, "usage", None)
    result_model = getattr(completion, "model", None) or model

    raw_message: dict[str, Any] = {
        "role": "assistant",
        "content": raw_content or None,
    }
    if raw_tool_calls:
        raw_message["tool_calls"] = [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in raw_tool_calls
        ]

    return {
        "content": content,
        "tool_calls": tool_calls,
        "finish_reason": finish_reason,
        "model": result_model,
        "usage": {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        },
        "raw_message": raw_message,
    }


def complete_text(
    *,
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    system_prompt: str | None = None,
    prompt_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    messages = build_messages(
        user_message=user_message,
        history=history,
        image_data_url=image_data_url,
        system_prompt=system_prompt,
        prompt_memory=prompt_memory,
    )
    completion = _send_completion_request(messages=messages, stream=False)

    reply = ""
    if completion.choices:
        content = completion.choices[0].message.content
        reply = content if isinstance(content, str) else str(content)

    usage = getattr(completion, "usage", None)
    model = completion.model or _get_provider_settings()["model"]

    return {
        "reply": reply,
        "model": model,
        "usage": {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        },
    }


def complete_json(
    *,
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    system_prompt: str | None = None,
    prompt_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    diagnostic = complete_json_diagnostic(
        user_message=user_message,
        history=history,
        image_data_url=image_data_url,
        system_prompt=system_prompt,
        prompt_memory=prompt_memory,
    )
    payload = diagnostic.get("payload")
    if isinstance(payload, dict):
        return payload
    raise ValueError(str(diagnostic.get("error") or "Model did not return a valid JSON object."))


def complete_json_diagnostic(
    *,
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    system_prompt: str | None = None,
    prompt_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        response = complete_text(
            user_message=user_message,
            history=history,
            image_data_url=image_data_url,
            system_prompt=system_prompt,
            prompt_memory=prompt_memory,
        )
    except Exception as exc:
        return {
            "payload": None,
            "raw_reply": None,
            "error": f"provider_error:{exc.__class__.__name__}",
            "model": None,
            "usage": {},
        }

    raw_reply = str(response.get("reply", "") or "")
    try:
        payload = _parse_json_object(raw_reply)
        return {
            "payload": payload,
            "raw_reply": raw_reply,
            "error": None,
            "model": response.get("model"),
            "usage": response.get("usage", {}),
        }
    except Exception as exc:
        return {
            "payload": None,
            "raw_reply": raw_reply,
            "error": f"invalid_json:{exc.__class__.__name__}",
            "model": response.get("model"),
            "usage": response.get("usage", {}),
        }


def stream_text(
    *,
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    system_prompt: str | None = None,
    prompt_memory: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    model = _get_provider_settings()["model"]
    messages = build_messages(
        user_message=user_message,
        history=history,
        image_data_url=image_data_url,
        system_prompt=system_prompt,
        prompt_memory=prompt_memory,
    )

    yield {"type": "meta", "model": model}

    stream = _send_completion_request(messages=messages, stream=True)
    for chunk in stream:
        if not chunk.choices:
            continue

        choice = chunk.choices[0]
        delta = getattr(choice, "delta", None)
        if delta is not None:
            delta_text = _extract_delta_text(getattr(delta, "content", None))
            if delta_text:
                yield {"type": "delta", "content": delta_text}

        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason:
            yield {"type": "done", "finish_reason": finish_reason}
            return

    yield {"type": "done", "finish_reason": "stop"}


def chat_with_openrouter(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    system_prompt: str | None = None,
    prompt_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return complete_text(
        user_message=user_message,
        history=history,
        image_data_url=image_data_url,
        system_prompt=system_prompt,
        prompt_memory=prompt_memory,
    )


def stream_chat_with_openrouter(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    image_data_url: str | None = None,
    system_prompt: str | None = None,
    prompt_memory: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    yield from stream_text(
        user_message=user_message,
        history=history,
        image_data_url=image_data_url,
        system_prompt=system_prompt,
        prompt_memory=prompt_memory,
    )


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("Model did not return a valid JSON object.")
