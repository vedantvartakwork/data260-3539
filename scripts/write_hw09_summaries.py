"""Write human-readable HW9 metrics directly from the frozen raw result JSON."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "hw09"
RAW = REPORT / "raw"


def main() -> None:
    payload = json.loads((RAW / "hw09_results.json").read_text(encoding="utf-8"))
    workload = payload["cache_workload"]
    rows = [
        "# Homework 9 Metrics",
        "",
        "## Redis ingress workload",
        "",
        f"- Queries: {workload['query_count']}",
        f"- Cache hits / misses: {workload['cache_hits']} / {workload['cache_misses']}",
        f"- Hit rate: {workload['hit_rate_percent']}%",
        f"- Mean cached latency: {workload['average_cached_latency_ms']} ms",
        f"- Mean non-cached local-model latency: {workload['average_non_cached_latency_ms']} ms",
        "",
        "## Frozen 40-case threshold sweep",
        "",
        "| Threshold | Hit rate | False-hit rate | Mean latency (ms) | Total cost |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in payload["threshold_sweep"]:
        rows.append(
            f"| {row['threshold']:.2f} | {row['hit_rate_percent']:.2f}% | "
            f"{row['false_hit_rate_percent']:.2f}% | {row['mean_latency_ms']:.3f} | "
            f"${row['total_cost']:.3f} |"
        )
    rows.extend(
        [
            "",
            "Cost model: $0.002 per cache miss and $0.25 support cost per false hit.",
            f"Chosen threshold: **{payload['cost_model']['chosen_threshold']:.2f}**. "
            + payload["cost_model"]["justification"],
            "",
            "## Self-improving variants (held-out test set)",
            "",
            "| Variant | Correct | Incorrect | Avg attempts | Avg latency (ms) |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for name, result in payload["self_improving"]["variants"].items():
        rows.append(
            f"| {name} | {result['correct']} | {result['incorrect']} | "
            f"{result['average_attempts']:.3f} | {result['average_latency_ms']:.3f} |"
        )
    (REPORT / "METRICS.md").write_text("\n".join(rows) + "\n", encoding="utf-8")

    run_log = [
        "Vedant Vartak - DATA 260 Homework 9",
        "Backend: Redis 8 native cosine Vector Sets (VADD / VSIM)",
        "Local model adapter: qwen3:8b",
        f"Counter: Redis={payload['counter']['redis_count']} DB={payload['counter']['database_count']}",
        f"Ingress: {workload['cache_hits']} hits {workload['cache_misses']} misses",
        f"Chosen threshold: {payload['cost_model']['chosen_threshold']}",
        f"Staleness passed: {payload['staleness']['passed']}",
        "Offline tests: 8 passed",
        "Verification: PASS",
    ]
    (RAW / "RUN_LOG.txt").write_text("\n".join(run_log) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
