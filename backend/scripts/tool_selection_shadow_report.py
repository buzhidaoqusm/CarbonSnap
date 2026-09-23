"""Aggregate the tool-selection shadow log into rule-vs-model agreement numbers.

Reads the JSONL sink written by ``tool_selection_shadow.record_shadow_comparison``
(configured via ``AI_TOOL_SELECTION_SHADOW_LOG``) and prints agreement metrics:
exact-match rate, mean Jaccard, per-tool precision/recall of the rule engine vs
the model, and the most common divergences.

Usage:
    python scripts/tool_selection_shadow_report.py [path] [--limit N] [--json]

If ``path`` is omitted it falls back to ``AI_TOOL_SELECTION_SHADOW_LOG`` or
``../data/tool_selection_shadow.jsonl``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def _default_log_path() -> Path:
    env_path = os.getenv("AI_TOOL_SELECTION_SHADOW_LOG", "").strip()
    if env_path:
        return Path(env_path)
    backend_root = Path(__file__).resolve().parents[1]
    return backend_root.parent / "data" / "tool_selection_shadow.jsonl"


def _load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def summarize(records: list[dict[str, Any]], *, limit: int = 5) -> dict[str, Any]:
    total = len(records)
    if total == 0:
        return {"total": 0}

    exact = sum(1 for r in records if r.get("exact_match"))
    jaccard_sum = sum(float(r.get("jaccard", 0.0)) for r in records)

    matched = Counter()
    rule_only = Counter()
    model_only = Counter()
    rule_selected = Counter()
    model_selected = Counter()
    divergences = Counter()
    by_mode = Counter()
    by_intent = Counter()

    for record in records:
        by_mode[record.get("mode", "unknown")] += 1
        by_intent[record.get("intent") or "unknown"] += 1
        matched.update(record.get("matched", []))
        rule_only.update(record.get("rule_only", []))
        model_only.update(record.get("model_only", []))
        rule_selected.update(record.get("rule_tools", []))
        model_selected.update(record.get("model_tools", []))
        if not record.get("exact_match"):
            key = (
                "rule_only="
                + ",".join(sorted(record.get("rule_only", [])))
                + " | model_only="
                + ",".join(sorted(record.get("model_only", [])))
            )
            divergences[key] += 1

    tools = sorted(set(rule_selected) | set(model_selected))
    per_tool = {}
    for tool in tools:
        r = rule_selected.get(tool, 0)
        m = model_selected.get(tool, 0)
        agree = matched.get(tool, 0)
        # Treat the model selection as the reference: how often the rule engine
        # agreed on this tool when either side picked it.
        union = r + m - agree
        per_tool[tool] = {
            "rule_selected": r,
            "model_selected": m,
            "agreed": agree,
            "jaccard": round(agree / union, 4) if union else 1.0,
        }

    return {
        "total": total,
        "exact_match": exact,
        "exact_match_rate": round(exact / total, 4),
        "mean_jaccard": round(jaccard_sum / total, 4),
        "by_mode": dict(by_mode),
        "by_intent": dict(by_intent),
        "per_tool": per_tool,
        "top_divergences": divergences.most_common(limit),
    }


def _print_report(summary: dict[str, Any]) -> None:
    if summary.get("total", 0) == 0:
        print("No shadow records found.")
        return

    print(f"Records analysed:      {summary['total']}")
    print(
        f"Exact-match rate:      {summary['exact_match_rate'] * 100:.1f}% "
        f"({summary['exact_match']}/{summary['total']})"
    )
    print(f"Mean Jaccard:          {summary['mean_jaccard']:.3f}")
    print(f"By mode:               {summary['by_mode']}")
    print(f"By intent:             {summary['by_intent']}")
    print()
    print("Per-tool agreement (rule vs model):")
    print(f"  {'tool':<32} {'rule':>5} {'model':>6} {'agree':>6} {'jaccard':>8}")
    for tool, stats in sorted(summary["per_tool"].items(), key=lambda kv: kv[1]["jaccard"]):
        print(
            f"  {tool:<32} {stats['rule_selected']:>5} {stats['model_selected']:>6} "
            f"{stats['agreed']:>6} {stats['jaccard']:>8.3f}"
        )
    print()
    print("Top divergences:")
    for key, count in summary["top_divergences"]:
        print(f"  {count:>4}x  {key}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=None, help="Path to the shadow JSONL log")
    parser.add_argument("--limit", type=int, default=5, help="Top-N divergences to show")
    parser.add_argument("--json", action="store_true", help="Emit the summary as JSON")
    args = parser.parse_args(argv)

    path = Path(args.path) if args.path else _default_log_path()
    if not path.exists():
        print(f"Shadow log not found: {path}", file=sys.stderr)
        return 1

    summary = summarize(_load_records(path), limit=args.limit)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        _print_report(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
