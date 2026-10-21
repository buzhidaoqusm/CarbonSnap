"""One record per provider attempt: what it was for, where it went, how it went.

Logged under ``app.llm`` as a ``key=value`` line, with the fields also on the
log record as ``llm_call`` for code that wants them structured. Cost is left
out on purpose: it needs a price per model, which the tracing backend brings.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

logger = logging.getLogger("app.llm")


@dataclass(frozen=True)
class CallRecord:
    purpose: str
    provider: str
    model: str
    outcome: str
    latency_ms: int
    first_chunk_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    fallback_from: str | None = None


def record(call: CallRecord) -> None:
    fields = asdict(call)
    line = " ".join(f"{name}={'-' if value is None else value}" for name, value in fields.items())
    logger.info("llm_call %s", line, extra={"llm_call": fields})
