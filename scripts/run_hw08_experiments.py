"""Write deterministic HW8 failure logs and machine-readable raw evidence."""

from __future__ import annotations

import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.hw8.config import settings
from code.hw8.failures import run_all_failure_experiments
from code.hw8.pipeline import process_stage

REPORT = ROOT / "reports" / "hw08"
RAW = REPORT / "raw"


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    results = run_all_failure_experiments()
    pipeline = {
        "correlation_id": "pipeline-3539",
        "entity_key": "recall-3539",
        "question": "What should a customer do after finding a matching grocery recall?",
        "journey": [],
    }
    journey = []
    for role, input_topic, output_topic in (
        ("planner", settings.inbox, settings.tasks),
        ("writer", settings.tasks, settings.drafts),
        ("reviewer", settings.drafts, settings.final),
    ):
        pipeline = process_stage(role, pipeline)
        journey.append(
            {
                "role": role,
                "read_topic": input_topic,
                "send_topic": output_topic,
                "correlation_id": pipeline["correlation_id"],
                "status": pipeline["status"],
            }
        )
    payload = {
        "student": "Vedant Vartak",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "configuration": {
            "sid4": settings.sid4,
            "prefix": settings.prefix,
            "seed": settings.seed,
            "verify_seed": settings.verify_seed,
        },
        "pipeline": {"journey": journey, "final": pipeline},
        **results,
    }
    (RAW / "hw08_experiments.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with (RAW / "ordering_20_messages.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["input_sequence", "unkeyed_processed", "keyed_processed", "keyed_partition"]
        )
        ordering = results["results"]["two_partitions_two_consumers"]
        for input_n, unkeyed_n, keyed_n in zip(
            ordering["input_order"],
            ordering["unkeyed_processed_order"],
            ordering["keyed_processed_order"],
            strict=True,
        ):
            writer.writerow([input_n, unkeyed_n, keyed_n, ordering["keyed_partition"]])

    lines = [
        "Vedant Vartak - DATA 260 Homework 8 deterministic experiment log",
        f"timestamp_utc={payload['timestamp_utc']}",
        f"VERIFY_SEED={settings.verify_seed}",
        "",
        "THREE-AGENT MESSAGE JOURNEY",
    ]
    lines.extend(json.dumps(item, sort_keys=True) for item in journey)
    lines.extend(["FINAL " + json.dumps(pipeline, sort_keys=True), "", "FAILURE BEHAVIOR"])
    for name, result in results["results"].items():
        lines.append(f"{name}: {json.dumps(result, sort_keys=True)}")
    lines.append(f"PASS all_failure_experiments={results['passed']}")
    (REPORT / "RUN_LOG.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
