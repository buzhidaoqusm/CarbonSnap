"""Which providers a call may use, and one client per provider per process.

Building an ``OpenAI`` client builds an SSL context and an HTTP connection
pool, about 26 ms; building one per call also meant a new TCP and TLS
handshake per call, since each pool started empty. Clients are now cached on
the values that configure them, so a settings change in a test gets a new
client and an unchanged configuration reuses the old one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from anyio.lowlevel import RunVar
from openai import AsyncOpenAI, OpenAI, Timeout

from app.core.config import get_settings

# Reaching the provider should take well under a second; waiting the full read
# timeout to learn it is unreachable only holds the caller longer.
LLM_CONNECT_TIMEOUT_SECONDS = 5.0


class LLMConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    api_key: str
    model: str
    extra_headers: dict[str, str] = field(default_factory=dict, hash=False)


def _provider(name: str) -> Provider:
    config = get_settings()
    if name == "qwen":
        return Provider("qwen", config.qwen_base_url, config.qwen_api_key, config.qwen_model)

    headers: dict[str, str] = {}
    if config.openrouter_site_url:
        headers["HTTP-Referer"] = config.openrouter_site_url
    if config.openrouter_site_name:
        headers["X-OpenRouter-Title"] = config.openrouter_site_name
    return Provider(
        "openrouter",
        config.openrouter_base_url,
        config.openrouter_api_key,
        config.openrouter_model,
        headers,
    )


def chain(*, fallback: bool) -> list[Provider]:
    """The primary provider, then the fallback one if configured and wanted."""
    providers = [_provider(get_settings().llm_provider)]
    name = get_settings().llm_fallback_provider
    if fallback and name and name != providers[0].name:
        backup = _provider(name)
        if backup.api_key:
            providers.append(backup)
    return providers


def _timeout(seconds: float) -> Timeout:
    return Timeout(seconds, connect=LLM_CONNECT_TIMEOUT_SECONDS)


def _client_key(provider: Provider) -> tuple[str, str, float, int]:
    # Checked here rather than in chain(), so a test that replaces the client
    # factories needs no key.
    if not provider.api_key:
        raise LLMConfigError(f"{provider.name.upper()} API key is not configured.")
    # Set on the client so every call gets it; without it the SDK waits up to
    # 600 s. For streams the read timeout bounds the gap between chunks, not
    # the whole response, so long answers are not cut off.
    config = get_settings()
    return (
        provider.base_url,
        provider.api_key,
        config.ai_llm_timeout_seconds,
        config.ai_llm_max_retries,
    )


@lru_cache(maxsize=8)
def _cached_sync_client(base_url: str, api_key: str, timeout: float, retries: int) -> OpenAI:
    return OpenAI(
        base_url=base_url, api_key=api_key, timeout=_timeout(timeout), max_retries=retries
    )


def sync_client(provider: Provider) -> OpenAI:
    return _cached_sync_client(*_client_key(provider))


# An async connection pool belongs to the event loop that opened its
# connections, so each loop (one in production, one per async test) gets its
# own clients.
_ASYNC_CLIENTS: RunVar[dict[tuple[str, str, float, int], AsyncOpenAI]] = RunVar("llm_async_clients")


def async_client(provider: Provider) -> AsyncOpenAI:
    try:
        clients = _ASYNC_CLIENTS.get()
    except LookupError:
        clients = {}
        _ASYNC_CLIENTS.set(clients)
    key = _client_key(provider)
    if key not in clients:
        base_url, api_key, timeout, retries = key
        clients[key] = AsyncOpenAI(
            base_url=base_url, api_key=api_key, timeout=_timeout(timeout), max_retries=retries
        )
    return clients[key]


def auxiliary_timeout() -> Timeout:
    return _timeout(get_settings().ai_llm_aux_timeout_seconds)
