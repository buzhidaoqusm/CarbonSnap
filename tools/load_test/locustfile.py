"""Load test for the streaming chat endpoint.

What this measures, and why it is the number that matters: `/api/ai/chat/stream`
holds a connection open for the whole model response. Under gunicorn's sync
workers one in-flight stream occupies one worker for its entire duration, so the
ceiling on concurrent conversations is the worker count — not CPU. This test
makes that ceiling visible, and is re-run after the async migration (P1 in
docs/REFACTOR_ROADMAP.md) to show the difference.

Run against a stack whose provider is tools/fake_llm/server.py, otherwise the
numbers describe the provider instead of this server:

    uv run --with locust locust -f tools/load_test/locustfile.py \
        --host http://127.0.0.1:5000 --users 20 --spawn-rate 2 --run-time 2m

Reports two custom timings per request:
  ttft   time to the first content token (what a user perceives as latency)
  stream total time until the stream closes
"""

from __future__ import annotations

import json
import time
import uuid

from locust import HttpUser, between, events, task

PROMPTS = [
    "How do I recycle a plastic bottle?",
    "Is a greasy pizza box recyclable?",
    "What do I do with an old phone charger?",
    "Can I put broken glass in the glass bin?",
]


def _fire(name: str, start: float, exception: Exception | None = None) -> None:
    events.request.fire(
        request_type="SSE",
        name=name,
        response_time=(time.perf_counter() - start) * 1000,
        response_length=0,
        exception=exception,
    )


class ChatUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        """Register a throwaway account and keep its token for the session."""
        suffix = uuid.uuid4().hex[:12]
        credentials = {
            "username": f"load_{suffix}",
            "email": f"load_{suffix}@example.com",
            "password": "load-test-password",
        }
        response = self.client.post("/api/auth/register", json=credentials, name="/auth/register")
        if response.status_code >= 400:
            response = self.client.post(
                "/api/auth/login",
                json={"email": credentials["email"], "password": credentials["password"]},
                name="/auth/login",
            )
        self.token = (response.json().get("data") or {}).get("access_token", "")

    @task
    def stream_chat(self) -> None:
        prompt = PROMPTS[int(time.time() * 1000) % len(PROMPTS)]
        started = time.perf_counter()
        first_token_seen = False

        with self.client.post(
            "/api/ai/chat/stream",
            json={"message": prompt},
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "text/event-stream",
            },
            stream=True,
            catch_response=True,
            name="/ai/chat/stream",
        ) as response:
            if response.status_code != 200:
                response.failure(f"status {response.status_code}")
                return
            try:
                for raw_line in response.iter_lines():
                    if not raw_line or not raw_line.startswith(b"data: "):
                        continue
                    event = json.loads(raw_line[len(b"data: ") :])
                    if not first_token_seen and event.get("type") == "delta":
                        first_token_seen = True
                        _fire("ttft", started)
                    if event.get("type") == "error":
                        response.failure(event.get("message", "stream error"))
                        return
                    if event.get("type") == "done":
                        break
            except Exception as exc:  # noqa: BLE001 - report, don't crash the run
                response.failure(str(exc))
                _fire("stream", started, exception=exc)
                return

            if not first_token_seen:
                response.failure("stream closed before any token")
            else:
                response.success()
            _fire("stream", started)
