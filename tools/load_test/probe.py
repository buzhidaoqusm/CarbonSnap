"""Targeted probes for the problems a locust summary hides.

locust answers "how slow is it under N users". These probes answer "why", one
problem at a time, so each fix later has a before/after number of its own:

  timeline    where a single chat turn spends its time (needs FAKE_LLM_LOG=1)
  blocking    does a cheap endpoint wait while chat streams are in flight
  disconnect  does the server keep working after the user closes the tab
              (built for gunicorn workers: it reads a busy worker off /api/health)
  abandon     how many provider calls still start after the user closes the tab
              (reads the fake provider's log; start the stack with FAKE_LLM_LOG=1)
  slow        what a hanging provider does to a worker

Run against the bench stack (docker-compose.bench.yml):

    uv run --no-project --with requests python tools/load_test/probe.py blocking
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
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


def _connections_by_state() -> str:
    query = (
        "select coalesce(state, '-') || '=' || count(*) from pg_stat_activity "
        "where datname = 'carbonsnap' group by state order by 1"
    )
    out = subprocess.run(
        ["docker", "exec", "carbonsnap-postgres-1", "psql", "-U", "carbonsnap", "-d", "carbonsnap",
         "-tA", "-c", query],
        capture_output=True, text=True, check=False,
    )
    return " ".join(out.stdout.split()) or out.stderr.strip()


def probe_blocking(streams: int) -> None:
    idle = [health_latency() for _ in range(5)]
    print(f"  /api/health idle:           median {fmt(statistics.median(idle))}")

    tokens = [register() for _ in range(streams)]
    results: list[dict] = []
    threads = [
        threading.Thread(target=lambda t=t: results.append(stream_turn(t))) for t in tokens
    ]
    for thread in threads:
        thread.start()
    time.sleep(3)  # every stream is past its first queries and waiting on the model

    during = [health_latency() for _ in range(3)]
    print(f"  /api/health with {streams} streams: max {fmt(max(during))}")
    print(f"  connections while streaming: {_connections_by_state()}")
    for thread in threads:
        thread.join()
    failed = [r for r in results if "done" not in r]
    print(f"  streams that did not finish: {len(failed)} of {streams}")
    if results:
        print(f"  slowest turn:                {fmt(max(r['closed'] for r in results))}")


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


def _provider_calls_since(since: dt.datetime) -> list[dt.datetime]:
    out = subprocess.run(
        ["docker", "logs", "--timestamps", "--since", since.isoformat(), "carbonsnap-fake-llm-1"],
        capture_output=True, text=True, check=False,
    )
    calls = []
    for line in (out.stdout + out.stderr).splitlines():
        stamp, _, rest = line.partition(" ")
        if '"path"' in rest:
            calls.append(dt.datetime.fromisoformat(stamp[:26] + "+00:00"))
    return calls


def probe_abandon() -> None:
    token = register()
    started = dt.datetime.now(dt.UTC)
    marks = stream_turn(token, abort_after=1.0)
    aborted = dt.datetime.now(dt.UTC)
    print(f"  client gave up after         {fmt(marks.get('aborted', marks['closed']))}")
    time.sleep(25)  # a full turn is ~10 s; anything still running shows up by now
    calls = _provider_calls_since(started)
    later = [c for c in calls if c > aborted]
    print(f"  provider calls in the turn:  {len(calls)}")
    print(f"  ...started after the abort:  {len(later)}")


def probe_slow() -> None:
    token = register()
    marks = stream_turn(token)
    for key, value in sorted(marks.items(), key=lambda item: item[1]):
        print(f"  {key:<16} {fmt(value)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("probe", choices=["timeline", "blocking", "disconnect", "abandon", "slow"])
    parser.add_argument("--streams", type=int, default=3)
    args = parser.parse_args()

    print(f"[{args.probe}]")
    if args.probe == "timeline":
        probe_timeline()
    elif args.probe == "blocking":
        probe_blocking(args.streams)
    elif args.probe == "disconnect":
        probe_disconnect()
    elif args.probe == "abandon":
        probe_abandon()
    else:
        probe_slow()


if __name__ == "__main__":
    main()
