from __future__ import annotations

import os
import sys
from pathlib import Path

DEFAULT_TEST_TARGETS = [
    "tests/unit/test_ai_decision_engine.py",
    "tests/unit/test_intent_router.py",
    "tests/unit/test_case_resolver.py",
    "tests/unit/test_memory_extractor.py",
    "tests/unit/test_forum_retrieval_service.py",
    "tests/unit/test_ai_forum_retrieval_flow.py",
    "tests/unit/test_seed_example_data.py",
]


def main(argv: list[str] | None = None) -> int:
    backend_root = Path(__file__).resolve().parents[1]
    os.chdir(backend_root)
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    try:
        import pytest
    except ModuleNotFoundError as exc:  # pragma: no cover
        print(
            "pytest is not installed in the current interpreter. "
            "Run this script with backend/.venv/Scripts/python.exe.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    extra_args = list(argv if argv is not None else sys.argv[1:])
    pytest_args = [*DEFAULT_TEST_TARGETS, "-q", *extra_args]
    return int(pytest.main(pytest_args))


if __name__ == "__main__":
    raise SystemExit(main())
