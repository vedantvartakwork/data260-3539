"""Summarize the saved 100-user JMeter result without changing raw samples."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "reports" / "hw08" / "raw"


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def main() -> None:
    with (RAW / "jmeter_100_users.jtl").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    elapsed = [int(row["elapsed"]) for row in rows]
    passed = [row for row in rows if row["success"].lower() == "true"]
    started = min(int(row["timeStamp"]) for row in rows)
    finished = max(int(row["timeStamp"]) + int(row["elapsed"]) for row in rows)
    duration_seconds = (finished - started) / 1000
    summary = {
        "student": "Vedant Vartak",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "threads": 100,
        "ramp_up_seconds": 10,
        "samples": len(rows),
        "passed": len(passed),
        "failed": len(rows) - len(passed),
        "error_percent": round((len(rows) - len(passed)) / len(rows) * 100, 2),
        "average_ms": round(mean(elapsed), 2),
        "min_ms": min(elapsed),
        "max_ms": max(elapsed),
        "p95_ms": percentile(elapsed, 0.95),
        "duration_seconds": round(duration_seconds, 3),
        "throughput_requests_per_second": round(len(rows) / duration_seconds, 2),
        "response_codes": sorted({row["responseCode"] for row in rows}),
        "passed_all": len(passed) == len(rows) == 100,
    }
    (RAW / "jmeter_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
