"""Calls whose reply must be one JSON object of a given shape.

The shape is a Pydantic model. Its JSON Schema goes to the provider as a
strict ``json_schema`` response format, and the reply is validated against
the same model, so a provider that ignores the format is caught here too.

For strict mode every model sets ``extra="forbid"`` (``additionalProperties:
false``) and gives no field a default (every property ``required``); a value
that may be absent is typed ``X | None`` and sent as null.

A failed reply raises ``StructuredOutputError`` with one of three reasons:
``no_reply`` (empty content), ``invalid_json``, or ``schema_mismatch`` (JSON
that does not fit the model). Nothing is dug out of surrounding prose.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from pydantic import BaseModel, ValidationError

from app.llm import gateway


class StructuredOutputError(ValueError):
    def __init__(self, reason: str, raw: str | None, reply: gateway.Reply) -> None:
        super().__init__(reason)
        self.reason = reason
        self.raw = raw
        self.reply = reply


class Structured[T: BaseModel](NamedTuple):
    value: T
    raw: str
    reply: gateway.Reply


def response_format(output: type[BaseModel]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": output.__name__,
            "strict": True,
            "schema": output.model_json_schema(),
        },
    }


def _parse[T: BaseModel](output: type[T], reply: gateway.Reply) -> Structured[T]:
    choices = reply.completion.choices or []
    raw = choices[0].message.content if choices else None
    if not raw or not raw.strip():
        raise StructuredOutputError("no_reply", raw, reply)
    try:
        value = output.model_validate_json(raw)
    except ValidationError as exc:
        not_json = any(error["type"] == "json_invalid" for error in exc.errors())
        raise StructuredOutputError(
            "invalid_json" if not_json else "schema_mismatch", raw, reply
        ) from exc
    return Structured(value, raw, reply)


def structured_sync[T: BaseModel](
    messages: list[dict[str, Any]], output: type[T], *, purpose: str, auxiliary: bool = False
) -> Structured[T]:
    reply = gateway.chat_sync(
        messages, purpose=purpose, auxiliary=auxiliary, response_format=response_format(output)
    )
    return _parse(output, reply)


async def structured[T: BaseModel](
    messages: list[dict[str, Any]], output: type[T], *, purpose: str, auxiliary: bool = False
) -> Structured[T]:
    reply = await gateway.chat(
        messages, purpose=purpose, auxiliary=auxiliary, response_format=response_format(output)
    )
    return _parse(output, reply)
