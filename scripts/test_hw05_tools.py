"""Offline assert-based runner for HW5 tool contracts, safety, and max_steps."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from code.hw5_agent import MockModel, run_agent
from code.hw5_tools import InMemoryRecallRepository, execute_tool


REPOSITORY = InMemoryRecallRepository()


def parsed(name: str, inputs: dict) -> dict:
    return json.loads(execute_tool(name, inputs, REPOSITORY))


def test_search_valid() -> None:
    result = parsed("search", {"query": "shrimp", "limit": 5})
    assert result["ok"] and result["data"]["count"] == 1


def test_search_invalid() -> None:
    result = parsed("search", {"query": "s", "limit": 5})
    assert not result["ok"] and "Invalid search input" in result["error"]


def test_detail_valid() -> None:
    result = parsed("detail", {"recall_id": 1})
    assert result["ok"] and result["data"]["recall_code"] == "REC-3539-00001"


def test_detail_invalid() -> None:
    result = parsed("detail", {"recall_id": 0})
    assert not result["ok"] and "Invalid detail input" in result["error"]


def test_aggregate_valid() -> None:
    result = parsed("aggregate", {"group_by": "category", "min_units": 0})
    assert result["ok"] and len(result["data"]["groups"]) == 2


def test_aggregate_invalid() -> None:
    result = parsed("aggregate", {"group_by": "submitter", "min_units": 0})
    assert not result["ok"] and "Invalid aggregate input" in result["error"]


def test_safety_rule_allowed() -> None:
    result = parsed("search", {"query": "rec", "limit": 10})
    assert result["ok"]


def test_safety_rule_blocked() -> None:
    result = parsed("search", {"query": "rec", "limit": 11})
    assert not result["ok"] and result["error"].startswith("Safety rule blocked")


def test_agent_max_steps() -> None:
    model = MockModel(
        [{"tool": "search", "inputs": {"query": "rec", "limit": 2}}],
        repeat_last=True,
    )
    run = run_agent(
        "Keep searching forever",
        model=model,
        repository=REPOSITORY,
        max_steps=3,
        log_path=None,
    )
    assert run.stop_reason == "max_steps" and run.step_count == 3


TESTS = [
    test_search_valid,
    test_search_invalid,
    test_detail_valid,
    test_detail_invalid,
    test_aggregate_valid,
    test_aggregate_invalid,
    test_safety_rule_allowed,
    test_safety_rule_blocked,
    test_agent_max_steps,
]


def main() -> int:
    passed = 0
    print("Vedant Vartak - DATA 260 Homework 5 offline tests")
    for test in TESTS:
        try:
            test()
        except Exception as exc:
            print(f"FAIL {test.__name__}: {exc}")
        else:
            passed += 1
            print(f"PASS {test.__name__}")
    print(f"SUMMARY {passed}/{len(TESTS)} tests passed")
    return 0 if passed == len(TESTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
