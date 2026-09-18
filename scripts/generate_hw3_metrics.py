"""Recompute the Homework 3 summary tables from raw retrieval output."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
HW3_DIR = ROOT / "reports" / "hw03"
RAW_PATH = HW3_DIR / "raw" / "retrieval_results.jsonl"
OUTPUT_PATH = HW3_DIR / "METRICS.md"
TECHNIQUE_LABELS = {
    "token": "Token",
    "semantic": "Semantic",
    "sentence_window": "Sentence window",
}


def load_results() -> list[dict]:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Run the retrieval comparison first: {RAW_PATH}")
    return [json.loads(line) for line in RAW_PATH.read_text().splitlines() if line]


def summary_row(payloads: list[dict]) -> dict:
    top_ones = [max(row["cosine_sim"] for row in item["results"]) for item in payloads]
    all_cosines = [
        row["cosine_sim"] for item in payloads for row in item["results"]
    ]
    recalls = [
        any(row["contains_expected_source"] for row in item["results"])
        for item in payloads
    ]
    return {
        "chunks": payloads[0]["chunk_count"],
        "avg_length": payloads[0]["avg_chunk_length"],
        "top1": float(np.mean(top_ones)),
        "mean_at_k": float(np.mean(all_cosines)),
        "recall": float(np.mean(recalls)),
        "latency": float(np.mean([item["retrieval_latency_ms"] for item in payloads])),
    }


def find_confident_wrong(payloads: list[dict]) -> tuple[dict, dict] | None:
    candidates = []
    for payload in payloads:
        if not payload["source_unique"]:
            continue
        for row in payload["results"]:
            if not row["contains_expected_source"]:
                candidates.append((row["cosine_sim"], payload, row))
    if not candidates:
        return None
    _, payload, row = max(candidates, key=lambda item: item[0])
    return payload, row


def main() -> None:
    payloads = load_results()
    techniques = sorted({item["technique"] for item in payloads})

    lines = [
        "# Homework 3 Retrieval Metrics",
        "",
        f"Model: `{payloads[0]['model']}`; top-k: `{payloads[0]['top_k']}`; questions: `5`.",
        "",
        "| Technique | Chunks | Avg chunk length | Top-1 cosine | Mean@k cosine | Recall@k | Mean retrieval latency (ms) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for technique in techniques:
        selected = [item for item in payloads if item["technique"] == technique]
        row = summary_row(selected)
        lines.append(
            f"| {TECHNIQUE_LABELS[technique]} | {row['chunks']} | "
            f"{row['avg_length']:.2f} | {row['top1']:.4f} | {row['mean_at_k']:.4f} | "
            f"{row['recall']:.1%} | {row['latency']:.3f} |"
        )

    lines.extend(
        [
            "",
            "Recall@k is the share of questions where at least one of the top-k chunks came from the expected source file.",
            "",
            "## Per-question expected-source recall",
            "",
            "| Question | Token | Semantic | Sentence window |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for question_id in sorted({item["question_id"] for item in payloads}):
        cells = []
        for technique in ["token", "semantic", "sentence_window"]:
            item = next(
                row
                for row in payloads
                if row["question_id"] == question_id and row["technique"] == technique
            )
            found = any(result["contains_expected_source"] for result in item["results"])
            cells.append("Yes" if found else "No")
        lines.append(f"| {question_id} | {' | '.join(cells)} |")

    wrong = find_confident_wrong(payloads)
    lines.extend(["", "## Confidently scored wrong retrieval", ""])
    if wrong is None:
        lines.append("No source-unique wrong retrieval was found in the five graded questions.")
    else:
        payload, row = wrong
        lines.extend(
            [
                f"- Question: {payload['question_id']} - {payload['question']}",
                f"- Technique and rank: {TECHNIQUE_LABELS[payload['technique']]} rank {row['rank']}",
                f"- Cosine similarity: {row['cosine_sim']:.4f}",
                f"- Expected source: `{payload['expected_source_file']}`",
                f"- Retrieved source: `{row['source_file']}`",
                f"- Preview: {row['preview']}",
                "- Why it likely scored well: both passages use closely related FDA recall, public-health, and notification vocabulary even though this source does not contain the source-unique answer.",
            ]
        )

    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUTPUT_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
