#!/usr/bin/env python3
"""Run and freeze every HW10 experiment from source data."""

from __future__ import annotations

import csv
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
loaded_code = sys.modules.get("code")
if loaded_code is not None and not hasattr(loaded_code, "__path__"):
    sys.modules.pop("code", None)

from code.hw10.config import settings
from code.hw10.judge import LocalGEvalJudge
from code.hw10.pipeline import ObservableRecallPipeline
from code.hw10.tracing import read_jsonl

RAW = settings.raw_dir


def percentile(values: list[float], percent: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * percent
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] + ((ordered[high] - ordered[low]) * fraction)


def commit_for_dataset() -> str:
    result = subprocess.run(
        [
            "git",
            "log",
            "-1",
            "--format=%H",
            "--",
            "reports/hw10/data/eval_cases.json",
            "reports/hw10/data/human_labels.csv",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    pipeline = ObservableRecallPipeline(RAW)
    pipeline.reset()

    live_trace = "trace-live-eval-3539"
    live = pipeline.run(
        "A customer has frozen shrimp with recall code REC-3539-00001. What should they do?",
        trace_id=live_trace,
        use_cache=True,
        judge_mode="live",
    )
    (RAW / "end_to_end_case.json").write_text(json.dumps(live, indent=2) + "\n", encoding="utf-8")
    hit_trace = "trace-cache-hit-3539"
    hit = pipeline.run(
        "A customer has frozen shrimp with recall code REC-3539-00001. What should they do?",
        trace_id=hit_trace,
        use_cache=True,
    )
    failed_trace = "trace-writer-failure-3539"
    try:
        pipeline.run(
            "Demonstrate the failed trace without returning an answer.",
            trace_id=failed_trace,
            use_cache=False,
            fail_stage="writer",
        )
    except RuntimeError:
        pass

    miss_trace_ids: list[str] = []
    for index in range(50):
        trace_id = f"trace-miss-{index + 1:02d}-3539"
        miss_trace_ids.append(trace_id)
        pipeline.run(
            f"Unique uncached recall operations question {index + 1}: explain safe action for lot U{index + 1:03d}.",
            trace_id=trace_id,
            use_cache=False,
            judge_mode="replay",
        )

    examples = {
        "cache_hit": hit_trace,
        "cache_miss": live_trace,
        "failed": failed_trace,
    }
    (RAW / "trace_examples.json").write_text(
        json.dumps(examples, indent=2) + "\n", encoding="utf-8"
    )

    cases = json.loads((settings.data_dir / "eval_cases.json").read_text(encoding="utf-8"))
    with (settings.data_dir / "human_labels.csv").open(encoding="utf-8", newline="") as handle:
        labels = {row["case_id"]: int(row["human_label"]) for row in csv.DictReader(handle)}
    judge = LocalGEvalJudge()
    scored: dict[str, list[dict]] = defaultdict(list)
    total = len(cases) * 3
    completed = 0
    for run_number in range(1, 4):
        for case in cases:
            result = judge.evaluate(case["question"], case["draft"], "Writer Helpfulness")
            scored[case["case_id"]].append(
                {"run": run_number, "score": result.score, "reason": result.reason}
            )
            completed += 1
            print(
                f"judge {completed:02d}/{total}: {case['case_id']} run {run_number} -> {result.score}",
                flush=True,
            )

    rows: list[dict] = []
    all_differences: list[float] = []
    changed_cases = 0
    for case in cases:
        case_id = case["case_id"]
        run_scores = [item["score"] for item in scored[case_id]]
        differences = [abs(run_scores[index] - run_scores[0]) for index in range(1, 3)]
        all_differences.extend(differences)
        if len(set(run_scores)) > 1:
            changed_cases += 1
        rows.append(
            {
                "case_id": case_id,
                "topic": case["metadata"]["topic"],
                "human_label": labels[case_id],
                "judge_run_1": run_scores[0],
                "judge_run_2": run_scores[1],
                "judge_run_3": run_scores[2],
                "reason_run_1": scored[case_id][0]["reason"],
            }
        )
    human = [row["human_label"] for row in rows]
    first = [row["judge_run_1"] for row in rows]
    spearman = float(spearmanr(human, first).statistic)
    mad = statistics.mean(abs(a - b) for a, b in zip(human, first, strict=True))
    changed_frequency = changed_cases / len(rows)
    mean_change = statistics.mean(all_differences)
    max_change = max(all_differences)
    validation = {
        "dataset_commit": commit_for_dataset(),
        "judge": "DeepEval GEval with local Ollama qwen3:8b temperature=0 seed=263539",
        "cases": rows,
        "repeatability": {
            "runs": 3,
            "changed_cases": changed_cases,
            "changed_score_frequency": changed_frequency,
            "mean_absolute_change": mean_change,
            "max_absolute_change": max_change,
        },
    }
    (RAW / "judge_validation.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )

    spans = read_jsonl(RAW / "spans.jsonl")
    requests = read_jsonl(RAW / "requests.jsonl")
    miss_spans = [span for span in spans if span["trace_id"] in miss_trace_ids]
    by_stage: dict[str, list[float]] = defaultdict(list)
    for span in miss_spans:
        by_stage[span["stage"]].append(float(span["duration_ms"]))
    miss_e2e = [
        float(row["e2e_latency_ms"]) for row in requests if row["trace_id"] in miss_trace_ids
    ]
    mean_e2e = statistics.mean(miss_e2e)
    stage_metrics = []
    for stage in ["cache_lookup", "planner", "writer", "reviewer", "queue_wait", "evaluator"]:
        values = by_stage[stage]
        stage_metrics.append(
            {
                "stage": stage,
                "p50_ms": round(percentile(values, 0.50), 3),
                "p95_ms": round(percentile(values, 0.95), 3),
                "mean_ms": round(statistics.mean(values), 3),
                "percent_of_e2e": round((statistics.mean(values) / mean_e2e) * 100, 2),
            }
        )
    dominant = max(stage_metrics, key=lambda item: item["mean_ms"])
    performance = {
        "confirmed_cache_misses": len(miss_e2e),
        "cache_served_count": sum(
            1
            for row in requests
            if row["trace_id"] in miss_trace_ids and row["cache_result"] == "hit"
        ),
        "e2e_p50_ms": round(percentile(miss_e2e, 0.50), 3),
        "e2e_p95_ms": round(percentile(miss_e2e, 0.95), 3),
        "stages": stage_metrics,
        "dominant_stage": dominant["stage"],
        "optimization": (
            f"Optimize {dominant['stage']} first because it has the largest measured mean share. "
            "The cache-hit path is reported separately and is not mixed into these miss percentiles."
        ),
    }
    (RAW / "stage_metrics.json").write_text(
        json.dumps(performance, indent=2) + "\n", encoding="utf-8"
    )

    deployment_gate = (
        f"The judge has Spearman={spearman:.3f}, MAD={mad:.3f}, and changed-score frequency="
        f"{changed_frequency:.1%}. It is useful for advisory regression screening but not a sole "
        "production release gate. More diverse expert labels, inter-rater agreement, and periodic "
        "drift checks are required before gate authority."
    )
    summary = {
        "end_to_end": live["evaluation"],
        "spearman": round(spearman, 6),
        "mean_absolute_difference": round(mad, 6),
        "changed_score_frequency": round(changed_frequency, 6),
        "mean_absolute_change": round(mean_change, 6),
        "max_absolute_change": max_change,
        "deployment_gate": deployment_gate,
        "cache_hit_trace_answer_matches": hit["answer"] == live["answer"],
        "dataset_commit": validation["dataset_commit"],
    }
    (RAW / "evaluation_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {"summary": summary, "performance": performance, "trace_examples": examples}, indent=2
        )
    )


if __name__ == "__main__":
    main()
