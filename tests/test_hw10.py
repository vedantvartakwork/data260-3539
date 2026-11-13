from __future__ import annotations

import json
from code.hw10.config import settings
from code.hw10.evaluator import replay_evaluator
from code.hw10.pipeline import ObservableRecallPipeline
from code.hw10.tracing import TraceStore, read_jsonl
from pathlib import Path

import pytest


def test_personal_configuration() -> None:
    assert (settings.sid4, settings.prefix, settings.port_base) == (3539, "s3539", 8839)
    assert (settings.seed, settings.verify_seed, settings.domain_id) == (3539, 263539, 3)


def test_frozen_dataset_has_twenty_manual_labels() -> None:
    cases = json.loads((settings.data_dir / "eval_cases.json").read_text(encoding="utf-8"))
    labels = (settings.data_dir / "human_labels.csv").read_text(encoding="utf-8").splitlines()
    assert len(cases) == 20
    assert len(labels) == 21
    assert {case["case_id"] for case in cases} == {line.split(",")[0] for line in labels[1:]}


def test_trace_store_records_required_fields(tmp_path: Path) -> None:
    store = TraceStore(tmp_path)
    with store.span("trace-1", "planner"):
        pass
    span = read_jsonl(store.spans_path)[0]
    assert {"trace_id", "stage", "start", "end", "duration_ms", "status", "error"} <= set(span)


def test_cache_miss_then_hit_paths(tmp_path: Path) -> None:
    pipeline = ObservableRecallPipeline(tmp_path)
    first = pipeline.run("Exact recall question", trace_id="miss", judge_mode="replay")
    second = pipeline.run("Exact recall question", trace_id="hit", judge_mode="replay")
    assert first["cache_result"] == "miss"
    assert second["cache_result"] == "hit"
    hit_spans = [row for row in read_jsonl(tmp_path / "spans.jsonl") if row["trace_id"] == "hit"]
    assert [row["stage"] for row in hit_spans] == ["cache_lookup"]


def test_miss_preserves_trace_and_stage_order(tmp_path: Path) -> None:
    pipeline = ObservableRecallPipeline(tmp_path)
    result = pipeline.run("Uncached question", trace_id="same-id", use_cache=False)
    assert result["correlation_id"] == result["trace_id"] == "same-id"
    stages = [row["stage"] for row in read_jsonl(tmp_path / "spans.jsonl")]
    assert stages == [
        "cache_lookup",
        "inbox",
        "planner",
        "queue_wait",
        "writer",
        "reviewer",
        "evaluator",
    ]


def test_failed_trace_names_stage_and_error(tmp_path: Path) -> None:
    pipeline = ObservableRecallPipeline(tmp_path)
    with pytest.raises(RuntimeError, match="intentional writer failure"):
        pipeline.run("Failure question", trace_id="failed", use_cache=False, fail_stage="writer")
    failed = [row for row in read_jsonl(tmp_path / "spans.jsonl") if row["status"] == "error"]
    assert failed[0]["stage"] == "writer"
    assert "intentional writer failure" in failed[0]["error"]


def test_replay_evaluator_reports_final_vs_draft() -> None:
    result = replay_evaluator(
        {
            "correlation_id": "x",
            "draft": "Return or disposal guidance.",
            "answer": "Approved: Return or disposal guidance.",
        }
    )
    assert result["final"]["score"] >= result["writer"]["score"]
    assert result["improvement"] == result["final"]["score"] - result["writer"]["score"]


def test_generated_experiments_when_present() -> None:
    summary_path = settings.raw_dir / "evaluation_summary.json"
    if not summary_path.exists():
        pytest.skip("Run experiments first")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    metrics = json.loads((settings.raw_dir / "stage_metrics.json").read_text(encoding="utf-8"))
    assert metrics["confirmed_cache_misses"] == 50
    assert metrics["cache_served_count"] == 0
    assert summary["cache_hit_trace_answer_matches"] is True
