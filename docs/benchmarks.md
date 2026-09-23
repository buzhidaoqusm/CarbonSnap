# Benchmarks

Baseline numbers for the refactor in [REFACTOR_ROADMAP.md](REFACTOR_ROADMAP.md).
Everything here is measured, not estimated. If a number is missing, it has not
been run yet.

## What is being measured, and why

`/api/ai/chat/stream` holds a connection open for the entire model response.
Under gunicorn's **sync** workers, one in-flight stream occupies one worker for
its whole duration, so the ceiling on concurrent conversations is the worker
count — not CPU, not memory. `backend/gunicorn.conf.py` sets
`workers = min(3, cpu_count)`, which puts that ceiling at **3**.

That is the claim the baseline has to prove before P1 (async migration) can
claim to have fixed it.

Metrics:

| Metric | Meaning |
|---|---|
| `ttft` p50 / p95 | time to the first content token — what a user perceives as latency |
| `stream` p50 / p95 | time until the stream closes |
| error rate | share of requests that failed or closed without a token |
| max stable concurrency | highest user count where the error rate stays at 0 and p95 ttft stays within 2x the single-user value |

## Method

The provider is [`tools/fake_llm/server.py`](../tools/fake_llm/server.py), not a
real one: repeatable, free, and it makes the numbers a property of this server
rather than of someone else's queue. Defaults are 400 ms to first token, then
120 tokens at 25 ms — about 3.4 s per response.

```bash
# 1. Stack with the fake provider
docker compose --profile bench up -d --build

# 2. Point the API at it (until this is the default in compose)
#    OPENROUTER_BASE_URL=http://fake-llm:9800/v1
#    OPENROUTER_API_KEY=fake

# 3. Load test, one run per user count
uv run --with locust locust -f tools/load_test/locustfile.py \
    --host http://127.0.0.1:5000 \
    --headless --users 20 --spawn-rate 2 --run-time 2m
```

Each user registers a throwaway account, then loops: POST a prompt, read the
SSE stream to `done`, wait 1–3 s.

Run the same scenario, on the same machine, with the same fake-provider timings
before and after each change. Record the hardware.

## Results

### Baseline — Flask 3.1 + gunicorn sync workers (pre-P1)

Not yet measured. Requires a Linux host or Docker: gunicorn does not run on
Windows, so the local dev machine cannot produce this number directly.

| Users | ttft p50 | ttft p95 | stream p50 | stream p95 | errors | notes |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 3 | | | | | | at the worker ceiling |
| 10 | | | | | | queueing expected |
| 20 | | | | | | |

Hardware: _to fill in_
Commit: _to fill in_

### After P1 — FastAPI + uvicorn (async)

Pending P1.

| Users | ttft p50 | ttft p95 | stream p50 | stream p95 | errors |
|---|---|---|---|---|---|
| 1 | | | | | |
| 20 | | | | | |
| 50 | | | | | |
| 100 | | | | | |
