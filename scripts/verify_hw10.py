#!/usr/bin/env python3
"""Verify the complete HW10 implementation and freeze verification.json."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
loaded_code = sys.modules.get("code")
if loaded_code is not None and not hasattr(loaded_code, "__path__"):
    sys.modules.pop("code", None)

from code.hw10.config import settings
from code.hw10.tracing import read_jsonl


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def command(arguments: list[str], *, env: dict[str, str] | None = None) -> dict:
    result = subprocess.run(
        arguments,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    return {
        "command": " ".join(arguments),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "passed": result.returncode == 0,
    }


def git_value(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def main() -> None:
    raw = settings.raw_dir
    summary = json.loads((raw / "evaluation_summary.json").read_text(encoding="utf-8"))
    metrics = json.loads((raw / "stage_metrics.json").read_text(encoding="utf-8"))
    validation = json.loads((raw / "judge_validation.json").read_text(encoding="utf-8"))
    spans = read_jsonl(raw / "spans.jsonl")
    requests = read_jsonl(raw / "requests.jsonl")

    check_env = dict(os.environ)
    check_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    ruff = command(
        [
            ".venv/bin/ruff",
            "check",
            "code/hw10",
            "scripts/run_hw10_experiments.py",
            "scripts/verify_hw10.py",
            "tests/test_hw10.py",
            "tests/conftest.py",
        ]
    )
    tests = command([".venv/bin/python", "-m", "pytest", "-q", "tests/test_hw10.py"], env=check_env)

    dashboard_passed = False
    dashboard_detail = ""
    try:
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(str(ROOT / "code" / "hw10" / "dashboard.py"), default_timeout=10)
        app.run()
        dashboard_passed = len(app.exception) == 0 and bool(app.title)
        dashboard_detail = (
            f"titles={[item.value for item in app.title]}; exceptions={len(app.exception)}"
        )
    except Exception as exc:
        dashboard_detail = f"{type(exc).__name__}: {exc}"

    example_ids = json.loads((raw / "trace_examples.json").read_text(encoding="utf-8"))
    by_trace = {
        trace_id: [span for span in spans if span["trace_id"] == trace_id]
        for trace_id in example_ids.values()
    }
    hit_ok = [span["stage"] for span in by_trace[example_ids["cache_hit"]]] == ["cache_lookup"]
    miss_ok = [span["stage"] for span in by_trace[example_ids["cache_miss"]]] == [
        "cache_lookup",
        "inbox",
        "planner",
        "queue_wait",
        "writer",
        "reviewer",
        "evaluator",
    ]
    failed = by_trace[example_ids["failed"]]
    fail_ok = any(span["stage"] == "writer" and span["status"] == "error" for span in failed)

    semantic_checks = [
        {"name": "frozen_20_case_set", "passed": len(validation["cases"]) == 20},
        {"name": "three_repeat_runs", "passed": validation["repeatability"]["runs"] == 3},
        {
            "name": "human_dataset_precedes_scores",
            "passed": summary["dataset_commit"] == "43ee393a839d19b97cbb16f5961b89eb2337869e",
        },
        {
            "name": "fifty_confirmed_misses",
            "passed": metrics["confirmed_cache_misses"] == 50
            and metrics["cache_served_count"] == 0,
        },
        {"name": "cache_hit_trace", "passed": hit_ok},
        {"name": "cache_miss_trace", "passed": miss_ok},
        {"name": "failed_trace", "passed": fail_ok},
        {"name": "single_trace_identifier", "passed": all(row["trace_id"] for row in requests)},
        {"name": "dashboard_app_test", "passed": dashboard_passed, "detail": dashboard_detail},
        {"name": "judge_correlation_reported", "passed": -1 <= summary["spearman"] <= 1},
        {"name": "judge_mad_reported", "passed": summary["mean_absolute_difference"] >= 0},
    ]
    artifacts = {path.name: sha256(path) for path in sorted(raw.glob("*")) if path.is_file()}
    passed = ruff["passed"] and tests["passed"] and all(item["passed"] for item in semantic_checks)
    payload = {
        "homework": 10,
        "student": "Vedant Vartak",
        "sid4": settings.sid4,
        "prefix": settings.prefix,
        "model": settings.model,
        "status": "PASS" if passed else "FAIL",
        "implementation_commit": git_value("rev-parse", "HEAD"),
        "resolved_hw10_tag": git_value("rev-parse", "hw10^{}"),
        "dataset_commit": summary["dataset_commit"],
        "ruff": ruff,
        "tests": tests,
        "checks": semantic_checks,
        "metrics": {
            "spearman": summary["spearman"],
            "mean_absolute_difference": summary["mean_absolute_difference"],
            "changed_score_frequency": summary["changed_score_frequency"],
            "confirmed_cache_misses": metrics["confirmed_cache_misses"],
            "cache_served_count": metrics["cache_served_count"],
        },
        "artifact_sha256": artifacts,
    }
    target = settings.report_dir / "verification.json"
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
