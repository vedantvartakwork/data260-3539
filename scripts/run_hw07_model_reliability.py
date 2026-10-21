#!/usr/bin/env python3
"""Run the required 20 real qwen3:8b tool-use attempts on fixed cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from code.hw5_tools import InMemoryRecallRepository
from code.hw7.agent import run_agent

CASES = {
    "A": (
        "Search for shrimp and then detail-lookup the first result. You must call both tools before answering.",
        ["search", "detail"],
    ),
    "B": (
        "Aggregate recalls by category and then search for one supporting shrimp example. You must call both tools before answering.",
        ["aggregate", "search"],
    ),
    "C": (
        "Compare shrimp and yogurt. Search for each and use detail on both first results before answering.",
        ["search", "detail", "search", "detail"],
    ),
}


def classify(result, expected: list[str]) -> str | None:
    if result.initial_failure:
        return result.initial_failure
    actual = [call.tool for call in result.invocations]
    if any(actual.count(name) < expected.count(name) for name in set(expected)):
        return "lost multi-step chain"
    if result.stop_reason != "success":
        return "lost multi-step chain"
    return None


def main() -> None:
    destination = ROOT / "reports/hw07/raw/tool_reliability_20_model_attempts.json"
    repository = InMemoryRecallRepository()
    rows = []
    for index in range(1, 21):
        case = "ABC"[(index - 1) % 3]
        prompt, expected = CASES[case]
        result = run_agent(prompt, repository=repository, log_path=None)
        failure = classify(result, expected)
        row = {
            "attempt": index,
            "case": case,
            "model": "qwen3:8b",
            "failure_class": failure,
            "well_formed_before_repair": result.initial_failure is None,
            "well_formed_after_repair": failure is None,
            **result.as_dict(),
        }
        rows.append(row)
        destination.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        print(
            f"attempt={index:02d} case={case} stop={result.stop_reason} calls={result.tool_calls} failure={failure}",
            flush=True,
        )
    print(destination)


if __name__ == "__main__":
    main()
