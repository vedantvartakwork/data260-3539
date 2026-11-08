"""Verify the HW9 implementation and bind evidence to the current commit."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "hw09"
RAW = REPORT / "raw"
RESULTS = RAW / "hw09_results.json"
VERIFICATION = REPORT / "verification.json"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_value(*arguments: str) -> str:
    result = run(["git", *arguments])
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def check_results(payload: dict[str, Any]) -> dict[str, bool]:
    sweep = payload["threshold_sweep"]
    chosen = next(row for row in sweep if row["threshold"] == 0.95)
    variants = payload["self_improving"]["variants"]
    validation = payload["self_improving"]["validation"]
    return {
        "redis_backend_recorded": payload["backend"] == "redis",
        "counter_25_and_db_20": payload["counter"]["passed"],
        "at_least_10_ingress_queries": payload["cache_workload"]["query_count"] >= 10,
        "forty_frozen_cases": all(len(row["outcomes"]) == 40 for row in sweep),
        "five_thresholds": [row["threshold"] for row in sweep] == [0.75, 0.8, 0.85, 0.9, 0.95],
        "chosen_threshold_no_false_hits": chosen["false_hits"] == 0,
        "false_hit_fully_recorded": bool(payload["false_hit_example"]["correct_answer"]),
        "stale_then_invalidated": payload["staleness"]["passed"],
        "four_agent_variants": len(variants) == 4,
        "bounded_two_attempts": max(
            result["attempts"] for variant in variants.values() for result in variant["results"]
        )
        <= 2,
        "lesson_reused": bool(payload["self_improving"]["lesson_reuse"]["lessons_used"]),
        "lesson_validation_passed": validation["kept"],
        "validation_failure_cases_not_regressed": validation["failure_cases_not_regressed"],
        "validation_previously_correct_remain_correct": validation[
            "previously_correct_remain_correct"
        ],
        "validation_unrelated_remains_grounded": validation["unrelated_remain_grounded"],
    }


def main() -> int:
    lint = run(
        [
            str(ROOT / ".venv" / "bin" / "ruff"),
            "check",
            "code/hw9",
            "scripts/run_hw09_experiments.py",
            "tests/test_hw09.py",
        ]
    )
    tests = run(
        [str(ROOT / ".venv" / "bin" / "python"), "-m", "pytest", "-q", "tests/test_hw09.py"]
    )
    payload = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {}
    checks = check_results(payload) if payload else {"experiment_results_exist": False}
    required = [
        ROOT / "code" / "hw9" / "store.py",
        ROOT / "code" / "hw9" / "semantic_cache.py",
        ROOT / "code" / "hw9" / "self_improving.py",
        ROOT / "reports" / "hw09" / "data" / "cache_cases.yaml",
        ROOT / "reports" / "hw09" / "data" / "training_data.json",
        ROOT / "reports" / "hw09" / "data" / "validation_data.json",
        ROOT / "reports" / "hw09" / "data" / "test_data.json",
        RESULTS,
        RAW / "redis_state.json",
    ]
    artifacts = {str(path.relative_to(ROOT)): sha256(path) for path in required if path.exists()}
    tagged = git_value("rev-parse", "hw9^{}")
    verification = {
        "student": "Vedant Vartak",
        "homework": 9,
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "commit": tagged if tagged != "unavailable" else git_value("rev-parse", "HEAD"),
        "hw9_tag": tagged,
        "lint": {"passed": lint.returncode == 0, "output": lint.stdout + lint.stderr},
        "tests": {"passed": tests.returncode == 0, "output": tests.stdout + tests.stderr},
        "checks": checks,
        "artifacts_sha256": artifacts,
    }
    verification["passed"] = (
        verification["lint"]["passed"]
        and verification["tests"]["passed"]
        and all(checks.values())
        and len(artifacts) == len(required)
    )
    VERIFICATION.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
    print("Vedant Vartak - DATA 260 Homework 9 verification")
    print(tests.stdout.strip())
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print("verification_passed=", verification["passed"])
    print("verification=", VERIFICATION)
    return 0 if verification["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
