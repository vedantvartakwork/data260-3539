"""Generate the HW4 N+1 percentile table from the 180-request CSV."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


RAW_PATH = Path("reports/hw04/raw/n_plus_one_requests.csv")
OUTPUT_PATH = Path("reports/hw04/METRICS.md")
EVALUATION_PATH = Path("reports/hw04/raw/evaluation.csv")
K_SWEEP_PATH = Path("reports/hw04/raw/k_sweep.json")
EXPLAIN_BEFORE_PATH = Path("reports/hw04/raw/explain_before.json")
EXPLAIN_AFTER_PATH = Path("reports/hw04/raw/explain_after.json")


def percentile(values: list[float], value: int) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), value))


def main() -> None:
    with RAW_PATH.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 180:
        raise ValueError(f"Expected 180 measured requests, found {len(rows)}")

    groups: dict[tuple[int, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(int(row["page_size"]), row["implementation"])].append(row)

    with EVALUATION_PATH.open(encoding="utf-8") as handle:
        evaluation_rows = list(csv.DictReader(handle))
    k_sweep = json.loads(K_SWEEP_PATH.read_text(encoding="utf-8"))
    explain_before = json.loads(EXPLAIN_BEFORE_PATH.read_text(encoding="utf-8"))[0]
    explain_after = json.loads(EXPLAIN_AFTER_PATH.read_text(encoding="utf-8"))[0]

    lines = [
        "# Homework 4 Metrics",
        "",
        "Model for Part 4: `qwen3:8b`; SEED: `3539`; VERIFY_SEED: `263539`.",
        "",
        "## N+1 query comparison",
        "",
        "| Page size | Version | SQL statements/request | p50 (ms) | p95 (ms) | p99 (ms) | Speed-up |",
        "| ---: | :--- | ---: | ---: | ---: | ---: | ---: |",
    ]

    summaries: dict[tuple[int, str], dict[str, float]] = {}
    for page_size in (10, 50, 200):
        for implementation in ("naive", "fixed"):
            subset = groups[(page_size, implementation)]
            if len(subset) != 30:
                raise ValueError(
                    f"Expected 30 rows for {page_size}/{implementation}, found {len(subset)}"
                )
            latencies = [float(row["latency_ms"]) for row in subset]
            summaries[(page_size, implementation)] = {
                "queries": float(subset[0]["sql_queries"]),
                "p50": percentile(latencies, 50),
                "p95": percentile(latencies, 95),
                "p99": percentile(latencies, 99),
            }

        naive = summaries[(page_size, "naive")]
        fixed = summaries[(page_size, "fixed")]
        speedup = naive["p50"] / fixed["p50"] if fixed["p50"] else 0.0
        for implementation in ("naive", "fixed"):
            item = summaries[(page_size, implementation)]
            speedup_text = "-" if implementation == "naive" else f"{speedup:.2f}x"
            lines.append(
                f"| {page_size} | {implementation} | {item['queries']:.0f} | "
                f"{item['p50']:.3f} | {item['p95']:.3f} | {item['p99']:.3f} | {speedup_text} |"
            )

    lines.extend(
        [
            "",
            "The naive endpoint issues one recall query plus one related-event query per returned record. "
            "The fixed endpoint uses eager loading and completes the same response with one SQL statement. "
            "The difference grows with page size because the naive query count grows linearly while the fixed query count stays constant.",
            "",
            "## Index experiment",
            "",
            "| Plan | Access type | Key | Estimated rows |",
            "| :--- | :--- | :--- | ---: |",
            f"| Before index | {explain_before['type']} | {explain_before['key'] or '-'} | {explain_before['rows']} |",
            f"| After index | {explain_after['type']} | {explain_after['key'] or '-'} | {explain_after['rows']} |",
            "",
            "The category filter changed from a full table scan (`ALL`) to indexed reference access (`ref`).",
            "",
            "## Grounded RAG evaluation",
            "",
            "| Configuration | Correct answers | Grounded answers | Format compliant |",
            "| :--- | ---: | ---: | ---: |",
        ]
    )
    for configuration in ("no_rag", "basic_rag", "context_rag"):
        subset = [row for row in evaluation_rows if row["configuration"] == configuration]
        correct = sum(row["correct_answer"] == "True" for row in subset)
        grounded = sum(row["grounded"] == "True" for row in subset)
        compliant = sum(row["format_compliant"] == "True" for row in subset)
        lines.append(f"| {configuration} | {correct}/6 | {grounded}/6 | {compliant}/6 |")

    lines.extend(
        [
            "",
            "The context-engineered configuration cited retrieved sources and used the required refusal for both unsupported questions.",
            "",
            "### top-k comparison for the two-chunk question",
            "",
            "| k | Chunks kept | Correct retrieval | Correct answer |",
            "| ---: | ---: | :---: | :---: |",
        ]
    )
    for row in k_sweep:
        lines.append(
            f"| {row['top_k']} | {row['chunks_after_engineering']} | "
            f"{'Yes' if row['correct_retrieval'] else 'No'} | "
            f"{'Yes' if row['correct_answer'] else 'No'} |"
        )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUTPUT_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
