"""The LLM gateway: one client per provider, fallback, and a record per call.

Runs against fake providers on local ports (tests/support/fake_provider.py),
so connection reuse is measured on real sockets.
"""

from __future__ import annotations

import logging

import httpx
import openai
import pytest

from app.llm import gateway
from app.services.ai import openrouter_service
from tests.support import fake_provider

pytestmark = pytest.mark.real_llm_client

MESSAGES = [{"role": "user", "content": "How do I recycle a bottle?"}]


@pytest.fixture
def primary():
    provider = fake_provider.start("primary-model")
    yield provider
    fake_provider.stop(provider)


@pytest.fixture
def backup():
    provider = fake_provider.start("backup-model")
    yield provider
    fake_provider.stop(provider)


@pytest.fixture
def providers(primary, backup, override_settings):
    override_settings(
        llm_provider="openrouter",
        openrouter_base_url=primary.base_url,
        openrouter_api_key="primary-key",
        openrouter_model="primary-model",
        openrouter_site_name="",
        llm_fallback_provider="qwen",
        qwen_base_url=backup.base_url,
        qwen_api_key="backup-key",
        qwen_model="backup-model",
        ai_llm_max_retries=0,
    )
    return primary, backup


@pytest.fixture
def calls(caplog):
    caplog.set_level(logging.INFO, logger="app.llm")

    def records() -> list[dict]:
        return [r.llm_call for r in caplog.records if hasattr(r, "llm_call")]

    return records


def test_calls_share_one_connection(providers):
    # Regression: every call built a new client, with a new connection pool,
    # so each one paid for a new TCP (and, to a real provider, TLS) handshake.
    primary, _ = providers
    for _ in range(5):
        openrouter_service.complete_text(user_message="hi")

    assert len(primary.requests) == 5
    assert primary.connections == 1


@pytest.mark.parametrize("status", [503, 429, 401])
def test_a_failed_call_moves_to_the_fallback(providers, calls, status):
    primary, backup = providers
    primary.fail_next(status)

    reply = gateway.chat_sync(MESSAGES, purpose="answer")

    assert reply.provider.name == "qwen"
    assert reply.completion.model == "backup-model"
    assert backup.requests[0].payload["model"] == "backup-model"
    failed, succeeded = calls()
    assert failed["provider"] == "openrouter" and failed["outcome"] != "ok"
    assert succeeded["provider"] == "qwen" and succeeded["outcome"] == "ok"
    assert succeeded["fallback_from"] == "openrouter"


def test_an_unreachable_provider_moves_to_the_fallback(providers, override_settings):
    _, backup = providers
    fake_provider.stop(providers[0])  # nothing listens on the primary's port now

    reply = gateway.chat_sync(MESSAGES, purpose="answer")

    assert reply.provider.name == "qwen"
    assert len(backup.requests) == 1


def test_a_refused_request_does_not_fall_back(providers):
    primary, backup = providers
    primary.fail_next(400)

    with pytest.raises(openai.BadRequestError):
        gateway.chat_sync(MESSAGES, purpose="answer")
    assert backup.requests == []


def test_auxiliary_calls_do_not_fall_back(providers):
    # Each has a fallback of its own; a second provider would double the wait.
    primary, backup = providers
    primary.fail_next(503)

    with pytest.raises(openai.InternalServerError):
        gateway.chat_sync(MESSAGES, purpose="router", auxiliary=True)
    assert backup.requests == []


def test_without_a_fallback_provider_the_error_is_the_primarys(providers, override_settings):
    primary, _ = providers
    override_settings(llm_fallback_provider="")
    primary.fail_next(503)

    with pytest.raises(openai.InternalServerError):
        gateway.chat_sync(MESSAGES, purpose="answer")


def test_embeddings_stay_on_the_primary(providers):
    # Another provider's model would put the vectors in another space.
    primary, backup = providers
    primary.fail_next(503)

    with pytest.raises(openai.InternalServerError):
        gateway.embed_sync(["bottle"], model="text-embedding-v3")
    assert backup.requests == []


def test_a_call_is_recorded_with_its_usage(providers, calls):
    gateway.chat_sync(MESSAGES, purpose="title", auxiliary=True)

    (record,) = calls()
    assert record["purpose"] == "title"
    assert record["provider"] == "openrouter"
    assert record["model"] == "primary-model"
    assert record["outcome"] == "ok"
    assert record["prompt_tokens"] == 11 and record["completion_tokens"] == 2
    assert record["latency_ms"] >= 0
    assert record["fallback_from"] is None


def test_a_stream_that_fails_to_open_moves_to_the_fallback(providers, calls):
    primary, backup = providers
    primary.reply = backup.reply = "one two three"
    primary.fail_next(503)

    stream = gateway.open_stream_sync(MESSAGES, purpose="answer")
    text = "".join(c.choices[0].delta.content or "" for c in stream if c.choices)

    assert stream.provider.name == "qwen"
    assert text == "one two three"
    record = calls()[-1]
    assert record["outcome"] == "ok"
    assert record["completion_tokens"] == 3  # from the usage chunk after the finish
    assert record["first_chunk_ms"] is not None


def test_a_stream_that_breaks_midway_does_not_fall_back(providers, calls):
    primary, backup = providers
    primary.reply = "one two three four"
    primary.stream_cut_after = 2

    stream = gateway.open_stream_sync(MESSAGES, purpose="answer")
    received = []
    # The SDK wraps errors raised while opening a stream, not those while
    # reading it: a dropped connection mid-stream surfaces as httpx's own.
    with pytest.raises(httpx.RemoteProtocolError):
        for chunk in stream:
            received.append(chunk.choices[0].delta.content)

    assert received == ["one", " two"]
    assert backup.requests == []
    assert calls()[-1]["outcome"] != "ok"


def test_a_stream_closed_by_its_reader_is_recorded_as_closed(providers, calls):
    primary, _ = providers
    primary.reply = "one two three"

    chunks = iter(gateway.open_stream_sync(MESSAGES, purpose="answer"))
    next(chunks)
    chunks.close()  # what the SSE layer does when the user hangs up

    assert calls()[-1]["outcome"] == "closed"


@pytest.mark.anyio
async def test_the_async_twins_fall_back_and_reuse_their_connection(providers, calls):
    primary, backup = providers
    primary.reply = backup.reply = "one two"
    primary.fail_next(503)

    reply = await gateway.chat(MESSAGES, purpose="answer")
    stream = await gateway.open_stream(MESSAGES, purpose="answer")
    text = "".join([c.choices[0].delta.content or "" async for c in stream if c.choices])
    embedded = await gateway.embed(["bottle"], model="text-embedding-v3")

    assert reply.provider.name == "qwen"
    assert text == "one two"  # the primary is healthy again
    assert len(embedded.data) == 1
    assert primary.connections == 1
    assert [r["outcome"] for r in calls()][1:] == ["ok", "ok", "ok"]


@pytest.fixture
def anyio_backend():
    return "asyncio"
