#!/usr/bin/env python3
"""Rebuild CSV, run log, and metrics from the preserved raw JSON."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    raw_dir = Path("reports/hw01/raw")
    json_path = raw_dir / "nondeterminism_results.json"
    results = json.loads(json_path.read_text(encoding="utf-8"))

    csv_path = raw_dir / "nondeterminism_results.csv"
    fields = ["temperature", "run_number", "model", "success", "tags", "summary", "latency_ms", "error"]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for result in results:
            writer.writerow({**result, "tags": json.dumps(result["tags"], ensure_ascii=False)})

    log_lines = [
        f"[{results[0]['started_at']}] Started non-determinism experiment: model={results[0]['model']}, runs_per_temperature=20"
    ]
    for result in results:
        status = "success" if result["success"] else "failure"
        log_lines.append(
            f"[{result['finished_at']}] temp={float(result['temperature']):.1f} "
            f"run={int(result['run_number']):02d} {status} latency_ms={float(result['latency_ms']):.2f}"
        )
    log_lines.append(
        f"[{results[-1]['finished_at']}] Finished experiment with "
        f"{sum(bool(item['success']) for item in results)}/{len(results)} successful runs"
    )

    demo_path = raw_dir / "five_turn_demo.json"
    if demo_path.exists():
        demo = json.loads(demo_path.read_text(encoding="utf-8"))
        log_lines.append(f"[{demo['generated_at']}] Completed five-turn demo; output={demo_path}")
    Path("reports/hw01/RUN_LOG.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    subprocess.run(
        [sys.executable, "scripts/generate_metrics.py", "--input", str(json_path), "--output", "reports/hw01/METRICS.md"],
        check=True,
    )
    print(f"Rebuilt {csv_path}, reports/hw01/RUN_LOG.txt, and reports/hw01/METRICS.md from {len(results)} records")


if __name__ == "__main__":
    main()
