#!/usr/bin/env python3
"""Run the fixed input 20 times at each required temperature."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents_demo import load_input, run_pipeline


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/hw01/cases/nondeterminism_input.json"))
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--raw-dir", type=Path, default=Path("reports/hw01/raw"))
    args = parser.parse_args()

    title, content = load_input(args.input)
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    log_lines = [f"[{timestamp()}] Started non-determinism experiment: model={args.model}, runs_per_temperature={args.runs}"]

    for temperature in (0.7, 0.0):
        for run_number in range(1, args.runs + 1):
            started = time.perf_counter()
            record: dict[str, Any] = {
                "temperature": temperature,
                "run_number": run_number,
                "model": args.model,
                "started_at": timestamp(),
            }
            try:
                pipeline = run_pipeline(title, content, model=args.model, temperature=temperature)
                record.update(
                    {
                        "success": True,
                        "tags": pipeline["publish"]["tags"],
                        "summary": pipeline["publish"]["summary"],
                        "reviewer_changed": pipeline["reviewer_changed"],
                        "token_usage": pipeline["token_usage"],
                        "error": None,
                    }
                )
            except Exception as exc:  # preserve every failed run for auditability
                record.update({"success": False, "tags": [], "summary": "", "error": f"{type(exc).__name__}: {exc}"})
            record["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
            record["finished_at"] = timestamp()
            results.append(record)
            status = "success" if record["success"] else "failure"
            line = f"[{record['finished_at']}] temp={temperature:.1f} run={run_number:02d} {status} latency_ms={record['latency_ms']:.2f}"
            log_lines.append(line)
            print(line, flush=True)

    json_path = args.raw_dir / "nondeterminism_results.json"
    csv_path = args.raw_dir / "nondeterminism_results.csv"
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["temperature", "run_number", "model", "success", "tags", "summary", "latency_ms", "error"],
            extrasaction="ignore",
        )
        writer.writeheader()
        for result in results:
            writer.writerow({**result, "tags": json.dumps(result["tags"], ensure_ascii=False)})

    log_lines.append(f"[{timestamp()}] Finished experiment with {sum(bool(item['success']) for item in results)}/{len(results)} successful runs")
    Path("reports/hw01/RUN_LOG.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, "scripts/generate_metrics.py", "--input", str(json_path), "--output", "reports/hw01/METRICS.md"],
        check=True,
    )


if __name__ == "__main__":
    main()
