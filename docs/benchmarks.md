# Benchmarks

Baseline numbers for the refactor in [REFACTOR_ROADMAP.md](REFACTOR_ROADMAP.md).
Everything here is measured, not estimated. If a number is missing, it has not
been run yet.

## What is being measured, and why

`/api/ai/chat/stream` holds a connection open for the entire model response.
Under gunicorn's **sync** workers (the baseline), one in-flight stream
occupied one worker for its whole duration, so the ceiling on concurrent
conversations was the worker count — not CPU, not memory. The baseline ran
`workers = min(3, cpu_count)`, which put that ceiling at **3**.

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

# 3. Tear down, including the benchmark volumes (not the dev database)
docker compose -f docker-compose.yml -f docker-compose.bench.yml --profile bench down
docker volume rm carbonsnap_bench-data carbonsnap_bench-postgres-data
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

### P1 stage 1 — uvicorn, Flask behind FastAPI on a thread pool

No route has moved yet (2026-10-03). `app.main` puts FastAPI in front and runs
the Flask app through a2wsgi on a thread pool, served by uvicorn instead of
gunicorn's sync workers. A chat stream now holds one **thread**, not one
process. Same scenario and fake-provider timings as the baseline.

Defaults: **1 process × 40 threads** (`WEB_WORKERS=1`, `WSGI_THREADS=40`),
database pool sized to the thread count (40 + 5 overflow).

| Users | ttft p50 | ttft p95 | stream p50 | stream p95 | errors | turns/s | notes |
|---|---|---|---|---|---|---|---|
| 20 | 11 | 11 | 14 | 14 | 0 / 139 | 1.17 | same as one user |
| 40 | 11 | 12 | 14 | 14 | 0 / 267 | 2.22 | same as one user |
| 60 | 15 | 16 | 18 | 19 | 0 / 310 | 2.60 | past the 40 threads: requests wait ~4.6 s for one |

Against the baseline at 20 users: ttft p50 **51 s → 11 s**, p95 **91 s → 11 s**,
throughput **0.18 → 1.17 turns/s**. Throughput now tops out at ~2.6 turns/s,
i.e. threads ÷ seconds per turn (40 ÷ ~15). `/api/health` with 10 streams in
flight: **3 ms** (baseline: 12.8 s with 3). `POST /api/auth/register` at 40
users: 86 ms p50 (baseline: 14 s at 20). Memory: ~100 MB idle, ~245 MB after
the 40-user run, against 320 MB for the 3 idle gunicorn workers.

The concurrency gain comes from threads, not from FastAPI itself: gunicorn's
gthread workers would have bought much the same. FastAPI is there for typed
request/response models, dependency injection and, in P2, async streaming.

How the defaults were chosen — two configurations that did not work:

| Configuration | Users | ttft p50 / p95 | errors | turns/s | what went wrong |
|---|---|---|---|---|---|
| 3 processes × 10 threads | 10 | 11 / 11 | 0 | 0.61 | fine |
| 3 processes × 10 threads | 20 | 15 / 21 | 0 | 0.89 | queueing already |
| 3 processes × 10 threads | 40 | 21 / 47 | 0 | 0.95 | |
| 1 process × 40 threads, default pool (5 + 10) | 40 | 20 / 36 | **34% of chats** | 1.01 | `QueuePool limit ... connection timed out` |

- **Three processes share load unevenly.** They all accept on one socket, and
  locust users keep their connections alive, so a connection stays with
  whichever process took it. Under 20 users one of the three processes held
  no client connection at all (its socket count stayed at the idle level), so
  only ~20 of the 30 threads did any work. One process with more threads has
  no such problem, and three processes × 40 threads would need 135 database
  connections, past PostgreSQL's default of 100.
- **A chat turn keeps a database connection for its whole duration.** Its
  first query (the user's preference profiles) opens a transaction that stays
  open, idle, across the LLM calls: 11–20 connections sat "idle in
  transaction" at 20 users. With more threads than pooled connections, the
  extra threads waited 30 s for one and failed. The pool is now sized to the
  thread count; the real fix, ending the transaction before calling the
  model, belongs to P2 (issue 9 in [PERFORMANCE_ISSUES.md](PERFORMANCE_ISSUES.md)).

Reproduce (bench stack as above; `WEB_WORKERS` / `WSGI_THREADS` pick the
configuration):

```bash
WEB_WORKERS=3 WSGI_THREADS=10 docker compose -f docker-compose.yml -f docker-compose.bench.yml --profile bench up -d api
uv run --no-project --with locust locust -f tools/load_test/locustfile.py --host http://127.0.0.1:5000 --headless --users 40 --spawn-rate 2 --run-time 2m --only-summary
```

Commit: the stage 1 merge into `main` (`p1/asgi-shell`).
