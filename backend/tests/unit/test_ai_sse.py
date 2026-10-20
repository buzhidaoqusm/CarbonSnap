"""sse_response: what happens around the events, driven over raw ASGI.

TestClient reads a response to the end, so it can neither hang up half way
nor keep a stream open while another request runs; these tests speak ASGI
to a small app instead.
"""

from __future__ import annotations

import threading
import time

import anyio
import pytest
from fastapi import Depends, FastAPI

from app.api.ai import sse

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _request(path: str) -> dict:
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("test", 1),
        "server": ("test", 80),
    }


async def _call(app, path: str, *, hang_up_after_frames: int | None = None) -> list[bytes]:
    """Run one request; with hang_up_after_frames, disconnect after that many
    body chunks, as a browser does when the tab closes."""
    bodies: list[bytes] = []
    hung_up = anyio.Event()
    sent_request = False

    async def receive():
        nonlocal sent_request
        if not sent_request:
            sent_request = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await hung_up.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.body" and message.get("body"):
            bodies.append(message["body"])
            if hang_up_after_frames is not None and len(bodies) >= hang_up_after_frames:
                hung_up.set()

    await app(_request(path), receive, send)
    return bodies


def _app(make_events, *, log: list[str]) -> FastAPI:
    app = FastAPI()

    def session():
        log.append("session: open")
        yield "session"
        log.append("session: closed")

    @app.get("/stream")
    def stream(db=Depends(session)):
        return sse.sse_response(lambda: make_events(db))

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return app


async def test_frames_follow_the_heartbeat():
    log: list[str] = []
    app = _app(lambda db: iter([{"type": "delta", "content": "hi"}]), log=log)

    bodies = await _call(app, "/stream")

    assert bodies == [sse.HEARTBEAT, b'data: {"type": "delta", "content": "hi"}\n\n']


async def test_a_client_that_hangs_up_closes_the_service_generator():
    log: list[str] = []

    def events(db):
        try:
            for n in range(50):
                time.sleep(0.02)
                yield {"type": "delta", "content": str(n)}
        finally:
            # The service's own cleanup still has its session.
            log.append(f"generator: finally ({db})")

    app = _app(events, log=log)

    started = time.perf_counter()
    bodies = await _call(app, "/stream", hang_up_after_frames=2)
    took = time.perf_counter() - started

    # Heartbeat and one event; the stream stops within a step or two, not
    # after all fifty.
    assert len(bodies) <= 4
    assert took < 0.5
    assert log == ["session: open", "generator: finally (session)", "session: closed"]


async def test_a_full_stream_closes_the_generator_before_the_session():
    log: list[str] = []

    def events(db):
        try:
            yield {"type": "done"}
        finally:
            log.append("generator: finally")

    await _call(_app(events, log=log), "/stream")

    assert log == ["session: open", "generator: finally", "session: closed"]


async def test_busy_streams_leave_the_other_routes_their_threads(override_settings):
    override_settings(ai_stream_threads=2)
    release = threading.Event()
    log: list[str] = []

    def events(db):
        release.wait(5)
        yield {"type": "done"}

    app = _app(events, log=log)
    async with anyio.create_task_group() as tg:
        for _ in range(3):  # one more stream than there are stream threads
            tg.start_soon(_call, app, "/stream")
        await anyio.sleep(0.2)
        assert sse.stream_limiter().borrowed_tokens == 2

        started = time.perf_counter()
        await _call(app, "/ping")
        assert time.perf_counter() - started < 0.2

        release.set()
