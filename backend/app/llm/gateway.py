"""Every LLM call goes through here: provider fallback and a usage record.

Retries within a provider are the SDK's: it already backs off exponentially on
connection errors, timeouts, 408, 409, 429 and 5xx, and honours Retry-After.
Retrying again out here would multiply the attempts, which is how three
retries on each of three calls once outlived the worker timeout. What the SDK
cannot do is move to another provider, so that is the loop below.

A call falls back when the provider failed it, and not when the request
itself was refused (400, 413, 422): another provider would refuse it too.
Three kinds of call never fall back:

- auxiliary ones (routing, memory extraction, titles): each has a fallback of
  its own, and a second provider would double the wait before the answer;
- embeddings: another provider's model puts vectors in another space, so they
  could not be compared with the stored index;
- a stream that has started: what the user already has came from one model.

Each function has a sync twin for the callers that run in threads.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Iterator
from types import TracebackType
from typing import Any, NamedTuple

from openai import APIConnectionError, APIStatusError
from openai.types import CreateEmbeddingResponse
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from app.llm import providers, usage
from app.llm.providers import Provider

_REQUEST_REFUSED = frozenset({400, 413, 422})


def should_fall_back(exc: BaseException) -> bool:
    if isinstance(exc, APIConnectionError):  # includes timeouts
        return True
    return isinstance(exc, APIStatusError) and exc.status_code not in _REQUEST_REFUSED


class Reply(NamedTuple):
    completion: ChatCompletion
    provider: Provider


class _Attempt:
    """One provider's try. Used as ``with attempt:`` around the request.

    A failure is recorded on the way out; if another provider may still be
    tried, the exception is swallowed and ``failed`` set, so the caller's loop
    moves on. Otherwise it propagates as it was.
    """

    def __init__(
        self, purpose: str, provider: Provider, *, fallback_from: str | None, last: bool
    ) -> None:
        self.purpose = purpose
        self.provider = provider
        self.fallback_from = fallback_from
        self.last = last
        self.failed = False
        self.started = time.perf_counter()

    def __enter__(self) -> _Attempt:
        self.started = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if exc is None:
            return False
        self.record(outcome=type(exc).__name__)
        if self.last or not should_fall_back(exc):
            return False
        self.failed = True
        return True

    def options(self) -> dict[str, Any]:
        options: dict[str, Any] = {"model": self.provider.model}
        if self.provider.extra_headers:
            options["extra_headers"] = self.provider.extra_headers
        return options

    # An auxiliary call is abandoned rather than retried: the caller has a
    # fallback. with_options() keeps the client's connection pool.

    def sync_client(self, *, auxiliary: bool = False) -> Any:
        client = providers.sync_client(self.provider)
        if auxiliary:
            return client.with_options(timeout=providers.auxiliary_timeout(), max_retries=0)
        return client

    def async_client(self, *, auxiliary: bool = False) -> Any:
        client = providers.async_client(self.provider)
        if auxiliary:
            return client.with_options(timeout=providers.auxiliary_timeout(), max_retries=0)
        return client

    def record(
        self,
        *,
        outcome: str,
        model: str | None = None,
        usage_info: Any = None,
        first_chunk_ms: int | None = None,
    ) -> None:
        usage.record(
            usage.CallRecord(
                purpose=self.purpose,
                provider=self.provider.name,
                model=model or self.provider.model,
                outcome=outcome,
                latency_ms=round((time.perf_counter() - self.started) * 1000),
                first_chunk_ms=first_chunk_ms,
                prompt_tokens=getattr(usage_info, "prompt_tokens", None),
                completion_tokens=getattr(usage_info, "completion_tokens", None),
                fallback_from=self.fallback_from,
            )
        )


def _attempts(purpose: str, chain: list[Provider]) -> Iterator[_Attempt]:
    previous: str | None = None
    for index, provider in enumerate(chain):
        yield _Attempt(purpose, provider, fallback_from=previous, last=index == len(chain) - 1)
        previous = provider.name


def _chain(*, auxiliary: bool = False) -> list[Provider]:
    return providers.chain(fallback=not auxiliary)


# -- chat -----------------------------------------------------------------


def chat_sync(
    messages: list[dict[str, Any]], *, purpose: str, auxiliary: bool = False, **request: Any
) -> Reply:
    for attempt in _attempts(purpose, _chain(auxiliary=auxiliary)):
        with attempt:
            completion = attempt.sync_client(auxiliary=auxiliary).chat.completions.create(
                messages=messages, **attempt.options(), **request
            )
        if attempt.failed:
            continue
        attempt.record(
            outcome="ok",
            model=getattr(completion, "model", None),
            usage_info=getattr(completion, "usage", None),
        )
        return Reply(completion, attempt.provider)
    raise AssertionError("the last attempt raises instead of failing over")


async def chat(
    messages: list[dict[str, Any]], *, purpose: str, auxiliary: bool = False, **request: Any
) -> Reply:
    for attempt in _attempts(purpose, _chain(auxiliary=auxiliary)):
        with attempt:
            completion = await attempt.async_client(auxiliary=auxiliary).chat.completions.create(
                messages=messages, **attempt.options(), **request
            )
        if attempt.failed:
            continue
        attempt.record(
            outcome="ok",
            model=getattr(completion, "model", None),
            usage_info=getattr(completion, "usage", None),
        )
        return Reply(completion, attempt.provider)
    raise AssertionError("the last attempt raises instead of failing over")


# -- streams --------------------------------------------------------------
#
# Opening a stream returns once the provider has accepted the request, which
# is the last point a failure can move to another provider. The record is
# written when the stream ends, closed or not, with the usage the provider
# sends in its last chunk.

_STREAM_REQUEST = {"stream": True, "stream_options": {"include_usage": True}}


class _StreamTally:
    def __init__(self, attempt: _Attempt) -> None:
        self.attempt = attempt
        self.outcome = "ok"
        self.model: str | None = None
        self.usage: Any = None
        self.first_chunk_ms: int | None = None

    def saw(self, chunk: ChatCompletionChunk) -> None:
        if self.first_chunk_ms is None:
            self.first_chunk_ms = round((time.perf_counter() - self.attempt.started) * 1000)
        self.model = self.model or getattr(chunk, "model", None)
        self.usage = getattr(chunk, "usage", None) or self.usage

    def failed(self, exc: BaseException) -> None:
        self.outcome = "closed" if isinstance(exc, GeneratorExit) else type(exc).__name__

    def record(self) -> None:
        self.attempt.record(
            outcome=self.outcome,
            model=self.model,
            usage_info=self.usage,
            first_chunk_ms=self.first_chunk_ms,
        )


class SyncStream:
    def __init__(self, response: Any, attempt: _Attempt) -> None:
        self._response = response
        self._tally = _StreamTally(attempt)
        self.provider = attempt.provider

    def __iter__(self) -> Iterator[ChatCompletionChunk]:
        try:
            for chunk in self._response:
                self._tally.saw(chunk)
                yield chunk
        except BaseException as exc:
            self._tally.failed(exc)
            raise
        finally:
            close = getattr(self._response, "close", None)
            if close is not None:
                close()
            self._tally.record()


class AsyncStream:
    def __init__(self, response: Any, attempt: _Attempt) -> None:
        self._response = response
        self._tally = _StreamTally(attempt)
        self.provider = attempt.provider

    async def __aiter__(self) -> AsyncIterator[ChatCompletionChunk]:
        try:
            async for chunk in self._response:
                self._tally.saw(chunk)
                yield chunk
        except BaseException as exc:
            self._tally.failed(exc)
            raise
        finally:
            close = getattr(self._response, "close", None)
            if close is not None:
                await close()
            self._tally.record()


def open_stream_sync(messages: list[dict[str, Any]], *, purpose: str, **request: Any) -> SyncStream:
    for attempt in _attempts(purpose, _chain()):
        with attempt:
            response = attempt.sync_client().chat.completions.create(
                messages=messages, **attempt.options(), **_STREAM_REQUEST, **request
            )
        if attempt.failed:
            continue
        return SyncStream(response, attempt)
    raise AssertionError("the last attempt raises instead of failing over")


async def open_stream(
    messages: list[dict[str, Any]], *, purpose: str, **request: Any
) -> AsyncStream:
    for attempt in _attempts(purpose, _chain()):
        with attempt:
            response = await attempt.async_client().chat.completions.create(
                messages=messages, **attempt.options(), **_STREAM_REQUEST, **request
            )
        if attempt.failed:
            continue
        return AsyncStream(response, attempt)
    raise AssertionError("the last attempt raises instead of failing over")


# -- embeddings -----------------------------------------------------------


def embed_sync(
    inputs: list[str], *, model: str, purpose: str = "embedding"
) -> CreateEmbeddingResponse:
    (attempt,) = _attempts(purpose, providers.chain(fallback=False))
    with attempt:
        response = attempt.sync_client().embeddings.create(
            input=inputs, **{**attempt.options(), "model": model}
        )
    attempt.record(outcome="ok", model=model, usage_info=getattr(response, "usage", None))
    return response


async def embed(
    inputs: list[str], *, model: str, purpose: str = "embedding"
) -> CreateEmbeddingResponse:
    (attempt,) = _attempts(purpose, providers.chain(fallback=False))
    with attempt:
        response = await attempt.async_client().embeddings.create(
            input=inputs, **{**attempt.options(), "model": model}
        )
    attempt.record(outcome="ok", model=model, usage_info=getattr(response, "usage", None))
    return response
