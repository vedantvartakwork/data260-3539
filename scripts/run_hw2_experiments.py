#!/usr/bin/env python3
"""Run and preserve all Homework 2 graph experiments."""

from __future__ import annotations

import csv
import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.hw2_graph import load_case, run_graph

MODEL = "qwen3:8b"
TEMPERATURE = 0.7
RAW = Path("reports/hw02/raw")


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def outcome(result: dict[str, Any]) -> str:
    if result["status"] != "completed":
        return "hit_turn_ceiling"
    attempts = int(result["planner_attempts"])
    if attempts == 1:
        return "valid_first_attempt"
    if attempts == 2:
        return "valid_after_1_retry"
    return "valid_after_2_or_more_retries"


def one(case: dict[str, str], run_number: int, max_turns: int, suite: str) -> dict[str, Any]:
    started_at = timestamp()
    try:
        result = run_graph(**case, model=MODEL, temperature=TEMPERATURE, max_turns=max_turns)
        return {
            "suite": suite,
            "run_number": run_number,
            "started_at": started_at,
            "finished_at": timestamp(),
            "model": MODEL,
            "temperature": TEMPERATURE,
            "max_turns": max_turns,
            "status": result["status"],
            "outcome": outcome(result),
            "planner_attempts": result["planner_attempts"],
            "latency_ms": result["latency_ms"],
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
            "final_output": result.get("final_output"),
            "validation_error": result.get("validation_error"),
            "trace": result["trace"],
            "error": None,
        }
    except Exception as exc:
        return {
            "suite": suite,
            "run_number": run_number,
            "started_at": started_at,
            "finished_at": timestamp(),
            "model": MODEL,
            "temperature": TEMPERATURE,
            "max_turns": max_turns,
            "status": "abandoned",
            "outcome": "hit_turn_ceiling",
            "planner_attempts": 0,
            "latency_ms": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "final_output": None,
            "validation_error": None,
            "trace": [],
            "error": f"{type(exc).__name__}: {exc}",
        }


def save(stem: str, rows: list[dict[str, Any]]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{stem}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fields = ["suite", "run_number", "started_at", "finished_at", "model", "temperature", "max_turns", "status", "outcome", "planner_attempts", "latency_ms", "input_tokens", "output_tokens", "final_output", "validation_error", "error"]
    with (RAW / f"{stem}.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "final_output": json.dumps(row["final_output"], ensure_ascii=False)})


def run_suite(case: dict[str, str], count: int, ceiling: int, suite: str, log: list[str]) -> list[dict[str, Any]]:
    rows = []
    for run_number in range(1, count + 1):
        row = one(case, run_number, ceiling, suite)
        rows.append(row)
        line = f"[{row['finished_at']}] suite={suite} run={run_number:02d} ceiling={ceiling} status={row['status']} outcome={row['outcome']} latency_ms={row['latency_ms']}"
        print(line, flush=True)
        log.append(line)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["all", "adversarial"], default="all")
    args = parser.parse_args()
    random.seed(3539)
    schema_case = load_case(Path("reports/hw02/cases/schema_input.json"))
    adversarial_case = load_case(Path("reports/hw02/cases/adversarial_input.json"))

    if args.only == "adversarial":
        log_path = Path("reports/hw02/RUN_LOG.txt")
        existing = log_path.read_text(encoding="utf-8").rstrip().splitlines() if log_path.exists() else []
        log = [*existing, f"[{timestamp()}] Started post-fix adversarial verification model={MODEL} temperature={TEMPERATURE} seed=3539"]
        adversarial = run_suite(adversarial_case, 5, 2, "adversarial_after_fix", log)
        save("adversarial_runs", adversarial)
        log.append(f"[{timestamp()}] Finished post-fix adversarial verification: {len(adversarial)} total runs")
        log_path.write_text("\n".join(log) + "\n", encoding="utf-8")
        import subprocess
        subprocess.run([sys.executable, "scripts/generate_hw2_metrics.py"], check=True)
        return

    log = [f"[{timestamp()}] Started HW2 experiments model={MODEL} temperature={TEMPERATURE} seed=3539"]

    schema = run_suite(schema_case, 30, 10, "schema_validation", log)
    save("schema_validation_runs", schema)

    ceilings = run_suite(schema_case, 20, 2, "ceiling_2", log)
    ceilings.extend(run_suite(schema_case, 20, 10, "ceiling_10", log))
    save("ceiling_comparison_runs", ceilings)

    adversarial = run_suite(adversarial_case, 5, 2, "adversarial", log)
    save("adversarial_runs", adversarial)
    log.append(f"[{timestamp()}] Finished HW2 experiments: {len(schema) + len(ceilings) + len(adversarial)} total runs")
    Path("reports/hw02/RUN_LOG.txt").write_text("\n".join(log) + "\n", encoding="utf-8")

    import subprocess
    subprocess.run([sys.executable, "scripts/generate_hw2_metrics.py"], check=True)


if __name__ == "__main__":
    main()
