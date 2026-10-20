"""Server-sent events for the AI routes.

The services produce their events with plain (blocking) generators. Each
step runs on a thread from STREAM_LIMITER, a pool of its own, so streams
waiting on the model cannot hold the threads every other sync route needs.
When the client goes away, Starlette stops reading and the background task
closes the service's generator at once, so its finally blocks run then
instead of whenever it is garbage-collected.
"""

import json
import logging
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

import anyio
from anyio.lowlevel import RunVar
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from app.api.ai.payloads import GENERIC_ERROR_MESSAGE
from app.core.config import get_settings
from app.services.ai.openrouter_service import OpenRouterConfigError

logger = logging.getLogger(__name__)

EventSource = Callable[[], Iterator[dict[str, Any]]]

# Byte for byte what the Flask route sent first; events after it use
# json.dumps' default separators.
HEARTBEAT = b'data: {"type":"heartbeat","stream_stage":"accepted"}\n\n'
HEADERS = {"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
_DONE = object()


# One per event loop, as anyio keeps its own default thread limiter.
_STREAM_LIMITER: RunVar[anyio.CapacityLimiter] = RunVar("ai_stream_limiter")


def stream_limiter() -> anyio.CapacityLimiter:
    try:
        return _STREAM_LIMITER.get()
    except LookupError:
        limiter = anyio.CapacityLimiter(get_settings().ai_stream_threads)
        _STREAM_LIMITER.set(limiter)
        return limiter


def _frame(event: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode()


def _error(message: str) -> bytes:
    return _frame({"type": "error", "code": 50000, "message": message})


async def _in_thread(fn: Callable[..., Any], *args: Any) -> Any:
    return await anyio.to_thread.run_sync(fn, *args, limiter=stream_limiter())


def sse_response(make_events: EventSource) -> StreamingResponse:
    started: list[Iterator[dict[str, Any]]] = []

    async def frames() -> AsyncIterator[bytes]:
        yield HEARTBEAT
        try:
            events = await _in_thread(make_events)
            started.append(events)
            while (event := await _in_thread(next, events, _DONE)) is not _DONE:
                yield _frame(event)
        except OpenRouterConfigError as exc:
            yield _error(str(exc))
        except Exception:
            # Details stay in the log: provider errors can name internals.
            logger.exception("AI stream failed.")
            yield _error(GENERIC_ERROR_MESSAGE)

    async def close() -> None:
        # Runs after the last frame and after a disconnect alike. No step is
        # in flight by then: a cancelled run_sync waits for its thread.
        for events in started:
            close_events = getattr(events, "close", None)
            if close_events is not None:
                await _in_thread(close_events)

    return StreamingResponse(
        frames(),
        media_type="text/event-stream",
        headers=HEADERS,
        background=BackgroundTask(close),
    )
