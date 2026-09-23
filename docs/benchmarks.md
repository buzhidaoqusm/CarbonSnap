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
# 1. Stack with the fake provider. The bench overlay points the api at
#    fake-llm and keeps benchmark accounts in a throwaway volume, not ./data.
docker compose -f docker-compose.yml -f docker-compose.bench.yml --profile bench up -d --build

# 2. Load test, one run per user count (1, 3, 10, 20)
uv run --no-project --with locust locust -f tools/load_test/locustfile.py     --host http://127.0.0.1:5000     --headless --users 20 --spawn-rate 2 --run-time 2m --only-summary

# 3. Tear down, including the benchmark volume
docker compose -f docker-compose.yml -f docker-compose.bench.yml --profile bench down -v
```

Each user registers a throwaway account, then loops: POST a prompt, read the
SSE stream to `done`, wait 1–3 s.

Run the same scenario, on the same machine, with the same fake-provider timings
before and after each change. Record the hardware.

## Results

### Baseline — Flask 3.1 + gunicorn sync workers (pre-P1)

3 sync workers, fake provider at 400 ms first token + 120 × 25 ms. 2 minutes
per run, spawn rate 2/s, 1–3 s think time. All times in seconds; locust
rounds percentiles to two significant figures.

| Users | ttft p50 | ttft p95 | stream p50 | stream p95 | errors | turns/s | notes |
|---|---|---|---|---|---|---|---|
| 1 | 10 | 10 | 13 | 14 | 0 / 7 | 0.07 | |
| 3 | 10 | 10 | 13 | 13 | 0 / 21 | 0.18 | at the worker ceiling, no degradation yet |
| 10 | 36 | 48 | 39 | 50 | 0 / 24 | 0.20 | queueing: ttft 3.6x |
| 20 | 51 | 91 | 54 | 94 | 0 / 20 | 0.18 | ttft p95 9x |

**Max stable concurrency: 3** — exactly the worker count. From 3 users to 20,
throughput stays flat at ~0.2 turns/s (3 workers / ~13 s per turn) and all the
extra load turns into waiting.

What the table does not show on its own:

- **Non-AI endpoints queue too.** `POST /api/auth/register` takes 0.1–0.2 s at
  1–3 users and **10 s (p50) at 10 users, 14 s at 20**. It does no model work;
  it is stuck behind streams holding every worker. One slow feature takes the
  whole API down with it.
- **No errors, but only because `timeout = 600`.** Requests wait instead of
  failing. A user sees a 50–90 s spinner, not an error, so error rate alone
  would call this healthy.
- **ttft is 10 s even with one user.** A chat turn makes four provider calls in
  series, and three of them finish before the first token is sent:

  | # | Call | Mode | Blocks first token |
  |---|---|---|---|
  | 1 | decision router | non-streaming | yes |
  | 2 | long-term memory extraction | non-streaming | yes |
  | 3 | conversation title | non-streaming | yes |
  | 4 | answer | streaming | — |

  (Seen with `FAKE_LLM_LOG=1`.) That is 3 × 3.4 s + 0.4 s ≈ 10.6 s. Memory
  extraction and title generation do not need to be on that path; this is P2
  work, separate from the concurrency fix in P1.

Caveat: the fake provider answers every non-streaming call with prose, so the
router's JSON parse fails and the decision engine falls back to
`general_chat`. Every turn therefore takes the same path, which is what a
baseline wants, but it is not the recycling-analysis path.

Hardware: Intel i7-13700H (14C/20T), 16 GB RAM, Windows 11; Docker Desktop
VM with 20 CPUs / 8 GB. Load generator on the same machine.
Commit: `699fa5a` + the Dockerfile fixes in the same commit as these numbers.

### After P1 — FastAPI + uvicorn (async)

Pending P1.

| Users | ttft p50 | ttft p95 | stream p50 | stream p95 | errors |
|---|---|---|---|---|---|
| 1 | | | | | |
| 20 | | | | | |
| 50 | | | | | |
| 100 | | | | | |
