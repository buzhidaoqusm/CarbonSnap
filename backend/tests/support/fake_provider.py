"""An OpenAI-compatible provider on a local port, for tests of the LLM gateway.

Real sockets rather than a mocked transport, so a test can see what a mock
hides: how many TCP connections the client opened (one per client port).
Responses are instant; ``fail_next(503)`` makes the next requests fail.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


@dataclass
class ProviderRequest:
    path: str
    payload: dict[str, Any]
    client_port: int


@dataclass
class FakeProvider:
    model: str
    reply: str = "ok reply"
    requests: list[ProviderRequest] = field(default_factory=list)
    failures: list[int] = field(default_factory=list)
    # Stream chunks sent before the connection is dropped; None streams fully.
    stream_cut_after: int | None = None
    server: ThreadingHTTPServer | None = None

    @property
    def base_url(self) -> str:
        assert self.server is not None
        return f"http://127.0.0.1:{self.server.server_address[1]}/v1"

    @property
    def connections(self) -> int:
        return len({request.client_port for request in self.requests})

    def fail_next(self, status: int, times: int = 1) -> None:
        self.failures.extend([status] * times)


def _handler(provider: FakeProvider) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: object) -> None:
            pass

        def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802 - stdlib hook
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
            provider.requests.append(ProviderRequest(self.path, payload, self.client_address[1]))

            if provider.failures:
                status = provider.failures.pop(0)
                self._send_json({"error": {"message": f"injected {status}"}}, status=status)
                return
            if self.path.endswith("/embeddings"):
                self._send_json(
                    {
                        "object": "list",
                        "model": payload["model"],
                        "data": [
                            {"object": "embedding", "index": i, "embedding": [0.1, 0.2]}
                            for i, _ in enumerate(payload["input"])
                        ],
                        "usage": {"prompt_tokens": 3, "total_tokens": 3},
                    }
                )
            elif payload.get("stream"):
                self._stream(payload)
            else:
                self._send_json(
                    {
                        "id": "chatcmpl-1",
                        "object": "chat.completion",
                        "created": 0,
                        "model": provider.model,
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": provider.reply},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"prompt_tokens": 11, "completion_tokens": 2, "total_tokens": 13},
                    }
                )

        def _stream(self, payload: dict[str, Any]) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

            def chunk(choices: list[dict[str, Any]], usage: dict[str, int] | None = None) -> None:
                body = {
                    "id": "chatcmpl-1",
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": provider.model,
                    "choices": choices,
                }
                if usage is not None:
                    body["usage"] = usage
                self._write(f"data: {json.dumps(body)}\n\n".encode())

            words = provider.reply.split(" ")
            for index, word in enumerate(words):
                if provider.stream_cut_after is not None and index == provider.stream_cut_after:
                    self.wfile.flush()
                    self.close_connection = True
                    self.connection.shutdown(2)
                    return
                text = word if index == 0 else f" {word}"
                chunk([{"index": 0, "delta": {"content": text}, "finish_reason": None}])
            chunk([{"index": 0, "delta": {}, "finish_reason": "stop"}])
            if (payload.get("stream_options") or {}).get("include_usage"):
                chunk([], usage={"prompt_tokens": 11, "completion_tokens": len(words)})
            self._write(b"data: [DONE]\n\n")
            self._write(b"")

        def _write(self, data: bytes) -> None:
            self.wfile.write(f"{len(data):X}\r\n".encode() + data + b"\r\n")
            self.wfile.flush()

    return Handler


def start(model: str) -> FakeProvider:
    provider = FakeProvider(model=model)
    provider.server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(provider))
    provider.server.daemon_threads = True
    # A cut stream leaves the handler writing to a closed socket; that is the
    # point of the test, not an error to print.
    provider.server.handle_error = lambda request, client_address: None  # type: ignore[method-assign]
    threading.Thread(
        target=provider.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
    ).start()
    return provider


def stop(provider: FakeProvider) -> None:
    assert provider.server is not None
    provider.server.shutdown()
    provider.server.server_close()
