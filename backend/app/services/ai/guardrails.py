from __future__ import annotations

from typing import Any

INJECTION_PATTERNS: dict[str, tuple[str, ...]] = {
    "instruction_override": (
        "ignore previous instructions",
        "disregard previous instructions",
        "disregard prior instructions",
        "forget previous instructions",
    ),
    "secret_exfiltration": (
        "reveal the system prompt",
        "show the system prompt",
        "developer message",
        "hidden developer message",
        "hidden instructions",
    ),
    "tool_abuse": (
        "bypass safety",
        "jailbreak",
        "call any tool",
        "ignore tool restrictions",
    ),
}


def scan_retrieved_text_for_injection(text: str) -> dict[str, Any]:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return {"injection_flagged": False, "reason": "clean", "matched": []}

    for reason, patterns in INJECTION_PATTERNS.items():
        matched = [pattern for pattern in patterns if pattern in normalized]
        if matched:
            return {
                "injection_flagged": True,
                "reason": reason,
                "matched": matched,
            }

    return {"injection_flagged": False, "reason": "clean", "matched": []}
