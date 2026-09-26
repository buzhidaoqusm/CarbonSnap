"""Targeted probes for the problems a locust summary hides.

locust answers "how slow is it under N users". These probes answer "why", one
problem at a time, so each fix later has a before/after number of its own:

  timeline    where a single chat turn spends its time (needs FAKE_LLM_LOG=1)
  blocking    does a cheap endpoint wait while chat streams are in flight
  disconnect  does the server keep working after the user closes the tab
  slow        what a hanging provider does to a worker

Run against the bench stack (docker-compose.bench.yml):

    uv run --no-project --with requests python tools/load_test/probe.py blocking
"""

from __future__ import annotations

import argparse
import json
import statistics
import threading
import time
import uuid

import requests

HOST = "http://127.0.0.1:5000"
PROMPT = "How do I recycle a plastic bottle?"


def register() -> str:
    suffix = uuid.uuid4().hex[:12]
    response = requests.post(
        f"{HOST}/api/auth/register",
        json={
            "username": f"probe_{suffix}",
            "email": f"probe_{suffix}@example.com",
            "password": "Load-test-password1",
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["data"]["access_token"]


def stream_turn(token: str, *, abort_after: float | None = None) -> dict:
    """One chat turn. Returns event arrival times relative to the request."""
    started = time.perf_counter()
    marks: dict[str, float] = {}
    # The server can go silent for seconds between events, so an abort cannot
    # wait for the next line: a read timeout drops the connection on time.
    read_timeout = abort_after if abort_after is not None else 900
    try:
        with requests.post(
            f"{HOST}/api/ai/chat/stream",
            json={"message": PROMPT},
            headers={"Authorization": f"Bearer {token}"},
            stream=True,
            timeout=(10, read_timeout),
        ) as response:
            marks["status"] = time.perf_counter() - started
            for raw in response.iter_lines():
                elapsed = time.perf_counter() - started
                if not raw.startswith(b"data: "):
                    continue
                event = json.loads(raw[6:])
                kind = event.get("type")
                key = f"first_{kind}" if kind in {"delta", "heartbeat"} else kind
                marks.setdefault(key, elapsed)
                if kind in {"done", "error"}:
                    break
    except requests.exceptions.ConnectionError:
        # requests surfaces a mid-body read timeout as a ConnectionError.
        marks["aborted"] = time.perf_counter() - started
    marks["closed"] = time.perf_counter() - started
    return marks


def health_latency() -> float:
    started = time.perf_counter()
    requests.get(f"{HOST}/api/health", timeout=900)
    return time.perf_counter() - started


def fmt(seconds: float) -> str:
    return f"{seconds * 1000:.0f} ms" if seconds < 1 else f"{seconds:.1f} s"


# -- probes ------------------------------------------------------------------


def probe_timeline() -> None:
    token = register()
    marks = stream_turn(token)
    for key, value in sorted(marks.items(), key=lambda item: item[1]):
        print(f"  {key:<16} {fmt(value)}")


def probe_blocking(streams: int) -> None:
    idle = [health_latency() for _ in range(5)]
    print(f"  /api/health idle:           median {fmt(statistics.median(idle))}")

    tokens = [register() for _ in range(streams)]
    threads = [threading.Thread(target=stream_turn, args=(t,)) for t in tokens]
    for thread in threads:
        thread.start()
    time.sleep(1)  # let every stream take a worker

    during = health_latency()
    print(f"  /api/health with {streams} streams: {fmt(during)}")
    for thread in threads:
        thread.join()


def probe_disconnect() -> None:
    token = register()
    marks = stream_turn(token, abort_after=1.0)
    print(f"  client gave up after        {fmt(marks.get('aborted', marks['closed']))}")
    # Is the worker still busy with the abandoned turn? A free worker answers
    # /api/health in milliseconds; take the other two workers out first so the
    # probe can only land on the abandoned one.
    others = [register() for _ in range(2)]
    threads = [threading.Thread(target=stream_turn, args=(t,)) for t in others]
    for thread in threads:
        thread.start()
    time.sleep(1)
    print(f"  /api/health right after:    {fmt(health_latency())}  (small = worker was freed)")
    for thread in threads:
        thread.join()


def probe_slow() -> None:
    token = register()
    marks = stream_turn(token)
    for key, value in sorted(marks.items(), key=lambda item: item[1]):
        print(f"  {key:<16} {fmt(value)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("probe", choices=["timeline", "blocking", "disconnect", "slow"])
    parser.add_argument("--streams", type=int, default=3)
    args = parser.parse_args()

    print(f"[{args.probe}]")
    if args.probe == "timeline":
        probe_timeline()
    elif args.probe == "blocking":
        probe_blocking(args.streams)
    elif args.probe == "disconnect":
        probe_disconnect()
    else:
        probe_slow()


if __name__ == "__main__":
    main()
