"""Generate the reproducible 150-call retry/fault-injection evidence."""

from __future__ import annotations

import csv
import json
import math
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from code.hw5_retry import RetryPolicy, call_with_retry


VERIFY_SEED = 263539
RATES = (0.0, 0.2, 0.5)
CALLS_PER_RATE = 50
OUTPUT_DIR = ROOT / "reports/hw05/raw"
CSV_PATH = OUTPUT_DIR / "fault_injection_calls.csv"
JSON_PATH = OUTPUT_DIR / "fault_injection_summary.json"


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    # Nearest-rank percentile; for 50 observations p99 is the largest sample.
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(VERIFY_SEED)
    policy = RetryPolicy(
        max_attempts=3,
        timeout_seconds=0.1,
        base_delay_seconds=0.001,
        max_delay_seconds=0.004,
    )
    records = []
    summaries = []

    for rate in RATES:
        group = []
        for call_index in range(1, CALLS_PER_RATE + 1):
            attempt_outcomes = []

            def operation() -> dict[str, int]:
                failed = rng.random() < rate
                attempt_outcomes.append("failure" if failed else "success")
                if failed:
                    raise RuntimeError("injected transient storage failure")
                return {"call_index": call_index}

            result = call_with_retry(operation, policy)
            row = {
                "verify_seed": VERIFY_SEED,
                "injected_failure_rate": rate,
                "call_index": call_index,
                "success": result.ok,
                "attempts": result.attempts,
                "attempt_outcomes": "|".join(attempt_outcomes),
                "latency_ms": round(result.latency_ms, 3),
                "error": result.error or "",
            }
            records.append(row)
            group.append(row)

        latencies = [row["latency_ms"] for row in group]
        summaries.append(
            {
                "injected_failure_rate": rate,
                "calls": len(group),
                "success_rate": sum(row["success"] for row in group) / len(group),
                "mean_latency_ms": round(statistics.fmean(latencies), 3),
                "p99_latency_ms": round(percentile(latencies, 0.99), 3),
            }
        )

    with CSV_PATH.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    JSON_PATH.write_text(
        json.dumps(
            {
                "verify_seed": VERIFY_SEED,
                "retry_policy": {
                    "max_attempts": policy.max_attempts,
                    "timeout_seconds": policy.timeout_seconds,
                    "base_delay_seconds": policy.base_delay_seconds,
                    "max_delay_seconds": policy.max_delay_seconds,
                },
                "summaries": summaries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print("Vedant Vartak - DATA 260 Homework 5 fault-injection experiment")
    print(f"VERIFY_SEED={VERIFY_SEED}; calls={len(records)}")
    for summary in summaries:
        print(json.dumps(summary, sort_keys=True))
    print(f"raw_csv={CSV_PATH}")


if __name__ == "__main__":
    main()
