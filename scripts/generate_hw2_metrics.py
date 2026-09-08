#!/usr/bin/env python3
"""Generate the Homework 2 metrics tables from raw experiment JSON."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any


RAW = Path("reports/hw02/raw")
OUT = Path("reports/hw02/METRICS.md")


def load(name: str) -> list[dict[str, Any]]:
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def average(rows: list[dict[str, Any]]) -> float:
    return mean(float(row["latency_ms"]) for row in rows) if rows else 0.0


def main() -> None:
    schema = load("schema_validation_runs.json")
    ceilings = load("ceiling_comparison_runs.json")
    adversarial = load("adversarial_runs.json")
    before_fix_path = RAW / "adversarial_runs_before_fix.json"
    adversarial_before = json.loads(before_fix_path.read_text(encoding="utf-8")) if before_fix_path.exists() else []
    categories = ["valid_first_attempt", "valid_after_1_retry", "valid_after_2_or_more_retries", "hit_turn_ceiling"]
    counts = Counter(row["outcome"] for row in schema)
    lines = [
        "# Homework 2 Metrics",
        "",
        "Model: `qwen3:8b`; temperature: `0.7`; frozen input: `reports/hw02/cases/schema_input.json`.",
        "",
        "## Schema-validation experiment (30 runs)",
        "",
        "| Outcome | Count | Mean latency (ms) |",
        "| --- | ---: | ---: |",
    ]
    labels = {
        "valid_first_attempt": "Valid first attempt",
        "valid_after_1_retry": "Valid after 1 retry",
        "valid_after_2_or_more_retries": "Valid after 2+ retries",
        "hit_turn_ceiling": "Hit turn ceiling",
    }
    for category in categories:
        rows = [row for row in schema if row["outcome"] == category]
        lines.append(f"| {labels[category]} | {counts[category]} | {average(rows):.2f} |")

    lines.extend(["", "## Turn-ceiling comparison (20 runs each)", "", "| Turn ceiling | Completed | Completion rate | Mean latency (ms) |", "| ---: | ---: | ---: | ---: |"])
    summaries = {}
    for ceiling in (2, 10):
        rows = [row for row in ceilings if int(row["max_turns"]) == ceiling]
        completed = sum(row["status"] == "completed" for row in rows)
        rate = completed / len(rows) * 100 if rows else 0.0
        summaries[ceiling] = (completed, rate, average(rows))
        lines.append(f"| {ceiling} | {completed}/{len(rows)} | {rate:.1f}% | {average(rows):.2f} |")
    selected = max(summaries, key=lambda ceiling: (summaries[ceiling][1], -summaries[ceiling][2]))
    lines.extend(["", f"**Deployment choice:** turn ceiling `{selected}`. It produced the best completion-rate/latency result in these measured runs.", ""])

    hits_before = sum(row["status"] == "abandoned" for row in adversarial_before)
    hits_after = sum(row["status"] == "abandoned" for row in adversarial)
    lines.extend([
        "## Adversarial input (5 runs)",
        "",
        f"- Before the fix, runs reaching the ceiling: **{hits_before}/5 ({hits_before / 5 * 100:.1f}%)**",
        f"- After the fix, runs reaching the ceiling: **{hits_after}/5 ({hits_after / 5 * 100:.1f}%)**",
        f"- Post-fix completion rate: **{(5 - hits_after)}/5 ({(5 - hits_after) / 5 * 100:.1f}%)**",
        f"- Post-fix mean latency: **{average(adversarial):.2f} ms**",
        "- Observed issue: the reviewer invented requirements (such as mandatory brand/lot tags) and repeatedly rejected schema-valid, factual output.",
        "- Implemented fix: delimit untrusted recall text, explicitly ignore embedded commands, and narrow the reviewer rubric to factual support without invented tag requirements; Pydantic validation and bounded retries remain enforced.",
        "",
    ])
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
