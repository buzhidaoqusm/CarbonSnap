"""How often the four JSON-returning calls on the chat path get usable JSON.

Runs evals/structured_output/cases.json against a real provider: one request
per case, paced under the free-model limit of 20 a minute. Works on the code
before and after structured outputs alike, so the same cases give both sides
of the comparison: it records every raw reply at the gateway, and classifies
it the same way whichever code produced it.

    LLM_PROVIDER=openrouter OPENROUTER_MODEL=nvidia/nemotron-3.5-super-vl:free \\
    LLM_FALLBACK_PROVIDER= AI_LLM_AUX_TIMEOUT_SECONDS=60 \\
        uv run python -m scripts.eval_structured_output --label before

The aux timeout is raised because a free model can take longer than the
production 15 s, and a timeout says nothing about the JSON. Results go to
evals/structured_output/results/<label>.json.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import re
import statistics
import time
from pathlib import Path
from typing import Any

import openai

from app.core.config import get_settings
from app.llm import gateway
from app.services.ai import case_resolver, intent_router, memory_extractor
from app.services.ai import recycling_analysis_service as recycling

EVAL_DIR = Path(__file__).resolve().parents[1] / "evals" / "structured_output"
PACE_SECONDS = 3.5
MEMORY_FIELDS = {"style", "enabled", "topic", "item_type", "preferred_method"}


class _Recorder(logging.Handler):
    """Collects the gateway's replies and usage records for the current case."""

    def __init__(self) -> None:
        super().__init__()
        self.replies: list[str | None] = []
        self.errors: list[str] = []
        self.calls: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.replies, self.errors, self.calls = [], [], []

    def emit(self, record: logging.LogRecord) -> None:
        call = getattr(record, "llm_call", None)
        if call is not None:
            self.calls.append(call)


RECORDER = _Recorder()
_real_chat_sync = gateway.chat_sync


def _recording_chat_sync(*args: Any, **kwargs: Any) -> gateway.Reply:
    try:
        reply = _real_chat_sync(*args, **kwargs)
    except Exception as exc:
        RECORDER.errors.append(type(exc).__name__)
        if isinstance(exc, openai.RateLimitError) and "per-day" in str(exc):
            raise SystemExit(f"Daily free-model limit reached: {exc}") from exc
        raise
    choices = reply.completion.choices or []
    RECORDER.replies.append(choices[0].message.content if choices else None)
    return reply


def classify_raw(raw: str | None) -> str:
    """The same buckets for every run, whatever parser the code used."""
    if raw is None:
        return "no_reply"
    text = raw.strip()
    try:
        if isinstance(json.loads(text), dict):
            return "clean_json"
    except json.JSONDecodeError:
        pass
    unfenced = re.sub(r"\s*```$", "", re.sub(r"^```(?:json)?\s*", "", text))
    try:
        if isinstance(json.loads(unfenced), dict):
            return "fenced_json"
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            if isinstance(json.loads(match.group(0)), dict):
                return "json_in_prose"
        except json.JSONDecodeError:
            pass
    return "invalid_json"


def _parse_leniently(raw: str | None) -> dict[str, Any] | None:
    """The reply as a dict, by the most lenient of the old parser's steps."""
    if raw is None:
        return None
    text = raw.strip()
    candidates = [text, re.sub(r"\s*```$", "", re.sub(r"^```(?:json)?\s*", "", text))]
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _options_ok(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(o, dict)
        and isinstance(o.get("label"), str)
        and isinstance(o.get("reply_text"), str)
        for o in value
    )


def conforms(kind: str, raw: str | None) -> bool:
    """Whether the reply has the fields the prompt asks for, with their types.

    Judged on the reply itself, not on what the code made of it: the old
    normalizers fill in defaults for missing fields, which hides a bad reply.
    """
    data = _parse_leniently(raw)
    if data is None:
        return False
    if kind == "router":
        return (
            data.get("intent") in intent_router.INTENTS
            and (
                data.get("follow_up_type") is None
                or data.get("follow_up_type") in intent_router.FOLLOW_UP_TYPES
            )
            and _is_number(data.get("confidence"))
            and isinstance(data.get("needs_clarification"), bool)
            and _options_ok(data.get("clarification_options"))
        )
    if kind == "memory":
        items = data.get("memory_candidates")
        return (
            isinstance(data.get("is_explicit_preference"), bool)
            and isinstance(items, list)
            and all(
                isinstance(i, dict)
                and i.get("memory_type")
                in {
                    "response_style",
                    "recycling_preference",
                    "topic_interest",
                    "item_method_preference",
                }
                and isinstance(i.get("memory_key"), str)
                # Each prompt's own contract: a free-form "value" object
                # before the schema, a field per kind of value after it.
                and (isinstance(i.get("value"), dict) or MEMORY_FIELDS <= i.keys())
                for i in items
            )
        )
    if kind == "resolver":
        case_id = data.get("target_case_id")
        return (
            (case_id is None or (isinstance(case_id, int) and not isinstance(case_id, bool)))
            and _is_number(data.get("confidence"))
            and isinstance(data.get("needs_clarification"), bool)
            and _options_ok(data.get("clarification_options"))
        )
    suggestions = data.get("recycle_suggestions")
    return (
        isinstance(data.get("waste_type"), str)
        and _is_number(data.get("confidence"))
        and _is_number(data.get("estimated_weight_kg"))
        and isinstance(suggestions, list)
        and all(isinstance(item, str) for item in suggestions)
        and isinstance(data.get("needs_nearby_search"), bool)
    )


def _case_summaries(items: list[Any]) -> list[dict[str, Any]]:
    summaries = []
    for index, item in enumerate(items, start=1):
        case_id, name = item if isinstance(item, list) else (index, item)
        summaries.append(
            {
                "case_id": case_id,
                "predicted_item": name,
                "current_stage": "analysis_complete",
                "status": "active",
                "has_nearby_results": False,
                "has_verification_attempts": False,
            }
        )
    return summaries


def _memory_value_is_readable(candidate: dict[str, Any]) -> bool:
    # What memory_service reads back for each type (see get_prompt_memory_summary).
    value = candidate.get("value") or {}
    kind = candidate.get("memory_type")
    if kind == "response_style":
        return value.get("value") in {"concise", "detailed"}
    if kind == "recycling_preference":
        return "value" in value
    if kind == "topic_interest":
        return bool(value.get("topic"))
    if kind == "item_method_preference":
        return bool(value.get("item_type") and value.get("preferred_method"))
    return False


def run_router(case: dict[str, Any]) -> dict[str, Any]:
    has_case = bool(case["cases"])
    out = intent_router.classify_intent_detailed(
        message=case["message"],
        image_data_url=None,
        recent_history=[],
        case_summaries=_case_summaries(case["cases"]),
        conversation_state={"current_pending_action": "none", "has_active_case": has_case},
        prompt_memory=None,
        allow_business_fallback=True,
    )
    result = out["result"]
    correct = result["intent"] == case["expected_intent"]
    if correct and case.get("expected_follow_up_type"):
        correct = result.get("follow_up_type") == case["expected_follow_up_type"]
    return {
        "from_model": out["router_failure_reason"] is None,
        "failure_reason": out["router_failure_reason"],
        "correct": correct,
        "observed": {"intent": result["intent"], "follow_up_type": result.get("follow_up_type")},
    }


def run_memory(case: dict[str, Any]) -> dict[str, Any]:
    out = memory_extractor.extract_explicit_memory_candidates_detailed(
        case["message"], allow_heuristic_fallback=False
    )
    candidates = out["candidates"]
    types = [c["memory_type"] for c in candidates]
    expected = case["expected_type"]
    correct = (not candidates) if expected is None else expected in types
    if correct and case.get("expected_value"):
        correct = any(c["value"].get("value") == case["expected_value"] for c in candidates)
    return {
        "from_model": out["extractor_failure_reason"] is None,
        "failure_reason": out["extractor_failure_reason"],
        "correct": correct,
        "readable": [_memory_value_is_readable(c) for c in candidates],
        "observed": candidates,
    }


def run_resolver(case: dict[str, Any]) -> dict[str, Any]:
    out = case_resolver.resolve_target_case_detailed(
        message=case["message"],
        recent_history=[],
        case_summaries=_case_summaries(case["cases"]),
        allow_heuristic_fallback=False,
    )
    result = out["result"]
    expected = case["expected_case_id"]
    if expected is None:
        correct = result["target_case_id"] is None or result["needs_clarification"]
    else:
        correct = result["target_case_id"] == expected and not result["needs_clarification"]
    return {
        "from_model": out["resolver_failure_reason"] is None,
        "failure_reason": out["resolver_failure_reason"],
        "correct": correct,
        "observed": {
            "target_case_id": result["target_case_id"],
            "needs_clarification": result["needs_clarification"],
        },
    }


def run_stage1(case: dict[str, Any]) -> dict[str, Any]:
    image = base64.b64encode((EVAL_DIR / case["image"]).read_bytes()).decode()
    try:
        payload = recycling._analyze_stage1(
            message=case["message"], image_data_url=f"data:image/jpeg;base64,{image}"
        )
    except Exception as exc:  # the normalizer runs outside the call's try
        return {
            "from_model": False,
            "failure_reason": f"crash:{type(exc).__name__}",
            "correct": False,
            "observed": None,
        }
    waste_type = str(payload.get("waste_type") or "").lower()
    # _analyze_stage1 swallows a failed call and returns a fixed fallback,
    # and its normalizer fills in whatever the reply left out.
    replied = bool(RECORDER.replies) and RECORDER.replies[-1] is not None
    return {
        "from_model": replied,
        "failure_reason": None if replied else "fallback_payload",
        "correct": any(word in waste_type for word in case["expected_material"]),
        "observed": {
            "waste_type": payload.get("waste_type"),
            "estimated_weight_kg": payload.get("estimated_weight_kg"),
        },
    }


RUNNERS = {
    "router": run_router,
    "memory": run_memory,
    "resolver": run_resolver,
    "stage1": run_stage1,
}


def summarise(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for kind in RUNNERS:
        rows = [r for r in results if r["kind"] == kind]
        if not rows:
            continue
        buckets: dict[str, int] = {}
        for row in rows:
            buckets[row["raw_class"]] = buckets.get(row["raw_class"], 0) + 1
        latencies = [c["latency_ms"] for r in rows for c in r["calls"] if c["outcome"] == "ok"]
        summary[kind] = {
            "cases": len(rows),
            "raw_reply": buckets,
            "conforms": sum(r["conforms"] for r in rows),
            "from_model": sum(r["from_model"] for r in rows),
            "correct": sum(r["correct"] for r in rows),
            "failure_reasons": sorted({r["failure_reason"] for r in rows if r["failure_reason"]}),
            "median_latency_ms": round(statistics.median(latencies)) if latencies else None,
            "completion_tokens": sum(
                (c["completion_tokens"] or 0) for r in rows for c in r["calls"]
            ),
        }
        if kind == "memory":
            flags = [flag for r in rows for flag in r["readable"]]
            summary[kind]["readable_candidates"] = f"{sum(flags)}/{len(flags)}"
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--only", default=",".join(RUNNERS))
    args = parser.parse_args()

    settings = get_settings()
    print(
        f"provider={settings.llm_provider} model={settings.openrouter_model} "
        f"fallback={settings.llm_fallback_provider or '-'}"
    )
    logger = logging.getLogger("app.llm")
    logger.setLevel(logging.INFO)
    logger.addHandler(RECORDER)
    gateway.chat_sync = _recording_chat_sync

    cases = json.loads((EVAL_DIR / "cases.json").read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    for kind in args.only.split(","):
        for case in cases[kind]:
            RECORDER.reset()
            row = RUNNERS[kind](case)
            raw = RECORDER.replies[-1] if RECORDER.replies else None
            row.update(
                kind=kind,
                id=case["id"],
                raw_class=classify_raw(raw) if not RECORDER.errors else "provider_error",
                conforms=conforms(kind, raw),
                raw_reply=raw,
                errors=RECORDER.errors,
                calls=RECORDER.calls,
            )
            results.append(row)
            print(
                f"  {case['id']} {row['raw_class']:<15} conforms={row['conforms']!s:<5} "
                f"model={row['from_model']!s:<5} "
                f"correct={row['correct']!s:<5} {row['failure_reason'] or ''}"
            )
            time.sleep(PACE_SECONDS)

    summary = summarise(results)
    out = EVAL_DIR / "results" / f"{args.label}.json"
    out.write_text(
        json.dumps(
            {
                "label": args.label,
                "model": settings.openrouter_model,
                "summary": summary,
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    print(f"written to {out}")


if __name__ == "__main__":
    main()
