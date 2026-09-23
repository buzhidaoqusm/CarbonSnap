"""A fake OpenAI-compatible provider for load testing.

Benchmarks must be repeatable and free. Pointing the backend at a real provider
would make every run depend on someone else's queue depth and cost money per
iteration, so the load tests talk to this instead: it streams a fixed number of
tokens at a fixed rate, which makes the latency numbers a property of *our*
server rather than of the provider.

Standard library only, so it runs anywhere with a Python 3 interpreter and no
install step:

    python tools/fake_llm/server.py

Then point the backend at it:

    OPENROUTER_BASE_URL=http://127.0.0.1:9800/v1
    OPENROUTER_API_KEY=fake
"""

from __future__ import annotations

import json
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Rough stand-ins for a mid-size hosted model. Override per scenario.
FIRST_TOKEN_MS = int(os.getenv("FAKE_LLM_FIRST_TOKEN_MS", "400"))
TOKEN_INTERVAL_MS = int(os.getenv("FAKE_LLM_TOKEN_INTERVAL_MS", "25"))
TOKEN_COUNT = int(os.getenv("FAKE_LLM_TOKEN_COUNT", "120"))
EMBEDDING_DIM = int(os.getenv("FAKE_LLM_EMBEDDING_DIM", "1024"))
PORT = int(os.getenv("PORT", "9800"))
# One line per request, to see how many provider calls a single chat turn makes.
LOG_REQUESTS = os.getenv("FAKE_LLM_LOG", "").lower() in {"1", "true", "yes"}

_WORDS = (
    "Rinse the bottle, remove the cap, and put it in the plastics bin. "
    "Caps are usually a different polymer, so they are sorted separately. "
    "Local rules vary, so check your council's guidance before dropping off. "
).split()


def _tokens(count: int) -> list[str]:
    return [_WORDS[i % len(_WORDS)] + " " for i in range(count)]


def _vector_for(text: object) -> list[float]:
    # Deterministic, so repeated runs retrieve the same neighbours.
    seed = abs(hash(str(text)))
    return [((seed >> (i % 32)) & 0xFF) / 255.0 for i in range(EMBEDDING_DIM)]


class FakeProviderHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003 - stdlib hook
        pass  # Keep the load-test console readable.

    # -- helpers ---------------------------------------------------------
    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return {}

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- routes ----------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 - stdlib hook
        if self.path.rstrip("/") == "/health":
            self._send_json(
                {
                    "status": "ok",
                    "first_token_ms": FIRST_TOKEN_MS,
                    "token_interval_ms": TOKEN_INTERVAL_MS,
                    "token_count": TOKEN_COUNT,
                }
            )
            return
        self._send_json({"error": {"message": "not found"}}, status=404)

    def do_POST(self) -> None:  # noqa: N802 - stdlib hook
        path = self.path.split("?", 1)[0].rstrip("/")
        payload = self._read_json()
        if LOG_REQUESTS:
            self._log_request(path, payload)

        if path.endswith("/chat/completions"):
            if payload.get("stream"):
                self._stream_completion(payload)
            else:
                self._complete(payload)
            return

        if path.endswith("/embeddings"):
            raw_input = payload.get("input")
            items = raw_input if isinstance(raw_input, list) else [raw_input]
            self._send_json(
                {
                    "object": "list",
                    "model": payload.get("model") or "fake-embedding",
                    "data": [
                        {"object": "embedding", "index": i, "embedding": _vector_for(item)}
                        for i, item in enumerate(items)
                    ],
                    "usage": {"prompt_tokens": len(items), "total_tokens": len(items)},
                }
            )
            return

        self._send_json({"error": {"message": f"unhandled path {path}"}}, status=404)

    def _log_request(self, path: str, payload: dict) -> None:
        messages = payload.get("messages") or []
        system = next((m.get("content") for m in messages if m.get("role") == "system"), "")
        print(
            json.dumps(
                {
                    "path": path,
                    "stream": bool(payload.get("stream")),
                    "response_format": (payload.get("response_format") or {}).get("type"),
                    "tools": len(payload.get("tools") or []),
                    "system": str(system)[:100],
                }
            ),
            flush=True,
        )

    def _complete(self, payload: dict) -> None:
        time.sleep((FIRST_TOKEN_MS + TOKEN_INTERVAL_MS * TOKEN_COUNT) / 1000)
        self._send_json(
            {
                "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": payload.get("model") or "fake-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "".join(_tokens(TOKEN_COUNT)).strip(),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 64,
                    "completion_tokens": TOKEN_COUNT,
                    "total_tokens": 64 + TOKEN_COUNT,
                },
            }
        )

    def _stream_completion(self, payload: dict) -> None:
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        created = int(time.time())
        model = payload.get("model") or "fake-model"

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        def frame(delta: dict, finish_reason: str | None = None) -> None:
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
            }
            self._write_chunk(f"data: {json.dumps(chunk)}\n\n".encode())

        try:
            time.sleep(FIRST_TOKEN_MS / 1000)
            frame({"role": "assistant", "content": ""})
            for token in _tokens(TOKEN_COUNT):
                time.sleep(TOKEN_INTERVAL_MS / 1000)
                frame({"content": token})
            frame({}, finish_reason="stop")
            self._write_chunk(b"data: [DONE]\n\n")
            self._write_chunk(b"")  # terminating zero-length chunk
        except (BrokenPipeError, ConnectionResetError):
            pass  # The client hung up mid-stream; nothing to clean up.

    def _write_chunk(self, data: bytes) -> None:
        self.wfile.write(f"{len(data):X}\r\n".encode())
        self.wfile.write(data + b"\r\n")
        self.wfile.flush()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), FakeProviderHandler)
    print(
        f"fake LLM on :{PORT} "
        f"(first token {FIRST_TOKEN_MS}ms, {TOKEN_COUNT} tokens @ {TOKEN_INTERVAL_MS}ms)",
        flush=True,
    )
    server.serve_forever()
