#!/usr/bin/env python3
"""Generate METRICS.md from raw non-determinism results."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


def normalize_tag(tag: str) -> str:
    return " ".join(tag.casefold().split())


def normalized_tag_set(tags: list[str]) -> tuple[str, ...]:
    return tuple(sorted(normalize_tag(tag) for tag in tags))


def nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("cannot calculate a percentile without values")
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def summarize(runs: list[dict[str, Any]], temperature: float) -> dict[str, Any]:
    successful = [run for run in runs if run.get("success") and float(run["temperature"]) == temperature]
    tag_sets = {normalized_tag_set(run["tags"]) for run in successful}
    tag_counts: Counter[str] = Counter()
    for run in successful:
        tag_counts.update(set(normalized_tag_set(run["tags"])))
    latencies = [float(run["latency_ms"]) for run in successful]
    return {
        "successful_runs": len(successful),
        "distinct_tag_sets": len(tag_sets),
        "tags_all": sorted(tag for tag, count in tag_counts.items() if count == len(successful)) if successful else [],
        "tags_once": sorted(tag for tag, count in tag_counts.items() if count == 1),
        "p50": nearest_rank(latencies, 0.50) if latencies else None,
        "p95": nearest_rank(latencies, 0.95) if latencies else None,
        "p99": nearest_rank(latencies, 0.99) if latencies else None,
    }


def display_list(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "None"


def render_metrics(runs: list[dict[str, Any]]) -> str:
    summaries = {temperature: summarize(runs, temperature) for temperature in (0.7, 0.0)}
    lines = [
        "# Homework 1 Metrics",
        "",
        "Generated from `reports/hw01/raw/nondeterminism_results.json`.",
        "",
        "## Non-determinism",
        "",
        "Tag comparison is case-insensitive, ignores leading/trailing and repeated whitespace, and treats tag order as irrelevant.",
        "",
        "| Metric | Temp 0.7 | Temp 0.0 |",
        "| --- | ---: | ---: |",
        f"| Successful runs | {summaries[0.7]['successful_runs']} | {summaries[0.0]['successful_runs']} |",
        f"| Distinct tag sets | {summaries[0.7]['distinct_tag_sets']} | {summaries[0.0]['distinct_tag_sets']} |",
        f"| Tags in all successful runs | {display_list(summaries[0.7]['tags_all'])} | {display_list(summaries[0.0]['tags_all'])} |",
        f"| Tags appearing once | {display_list(summaries[0.7]['tags_once'])} | {display_list(summaries[0.0]['tags_once'])} |",
        "",
        "| Latency metric | Temp 0.7 | Temp 0.0 |",
        "| --- | ---: | ---: |",
    ]
    for key, label in (("p50", "p50"), ("p95", "p95"), ("p99", "p99")):
        left = "N/A" if summaries[0.7][key] is None else f"{summaries[0.7][key]:.2f} ms"
        right = "N/A" if summaries[0.0][key] is None else f"{summaries[0.0][key]:.2f} ms"
        lines.append(f"| {label} | {left} | {right} |")
    lines.extend(
        [
            "",
            "Percentiles use the nearest-rank method: sort successful latency values and select rank `ceil(p * n)`.",
            "Failed runs are retained in the raw file but excluded from tag and latency calculations.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("reports/hw01/raw/nondeterminism_results.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/hw01/METRICS.md"))
    args = parser.parse_args()
    runs = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.write_text(render_metrics(runs), encoding="utf-8")
    print(f"Wrote {args.output} from {len(runs)} raw runs")


if __name__ == "__main__":
    main()

