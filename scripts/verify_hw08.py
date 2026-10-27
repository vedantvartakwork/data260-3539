"""Objective smoke-test runner that writes reports/hw08/verification.json."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.hw8.config import settings
from code.hw8.failures import run_all_failure_experiments, valid_recall
from code.hw8.pipeline import process_stage
from code.hw8.service import RecallService

OUTPUT = ROOT / "reports" / "hw08" / "verification.json"
LIVE_RESULTS = ROOT / "reports" / "hw08" / "raw" / "live_failure_experiments.json"


def git_hash() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def check(name: str, fn) -> dict:
    try:
        detail = fn()
        return {"name": name, "passed": True, "detail": detail or "ok"}
    except Exception as exc:
        return {"name": name, "passed": False, "detail": f"{type(exc).__name__}: {exc}"}


def round_trip() -> str:
    service = RecallService()
    created = service.process(
        {
            "correlation_id": "verify-create",
            "reply_to": settings.entity_responses,
            "operation": "CREATE_RECALL",
            "data": valid_recall(),
        }
    )
    fetched = service.process(
        {
            "correlation_id": "verify-get",
            "reply_to": settings.entity_responses,
            "operation": "GET_RECALL",
            "data": {"entity_id": created["entity_id"]},
        }
    )
    assert fetched["entity"]["entity_id"] == created["entity_id"]
    return f"entity_id={created['entity_id']}"


def pipeline_round_trip() -> str:
    state = {"correlation_id": "verify-pipeline", "question": "Recall guidance?", "journey": []}
    for role in ("planner", "writer", "reviewer"):
        state = process_stage(role, state)
    assert state["status"] == "approved"
    assert state["journey"] == ["planner", "writer", "reviewer"]
    return "inbox -> tasks -> drafts -> final"


def unit_suite() -> str:
    suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_hw08")
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    assert result.wasSuccessful()
    return f"tests_run={result.testsRun}"


def live_kafka_failures() -> str:
    payload = json.loads(LIVE_RESULTS.read_text(encoding="utf-8"))
    required = (
        "duplicate_delivery",
        "consumer_killed_mid_work",
        "poison_message",
        "two_partitions_two_consumers",
    )
    assert payload["passed"] is True
    assert all(payload[name]["passed"] is True for name in required)
    assert (
        payload["duplicate_delivery"]["first"]["entity_id"]
        == payload["duplicate_delivery"]["replay"]["entity_id"]
    )
    assert payload["two_partitions_two_consumers"]["keyed_processed_order"] == list(range(1, 21))
    return "live Kafka: duplicate restart poison ordering all passed"


def main() -> None:
    checks = [
        check("CREATE_RECALL followed by GET_RECALL round trip", round_trip),
        check("Planner Writer Reviewer correlation flow", pipeline_round_trip),
        check(
            "Duplicate restart poison and ordering experiments",
            lambda: "all passed" if run_all_failure_experiments()["passed"] else 1 / 0,
        ),
        check("Live Kafka failure experiments", live_kafka_failures),
        check("Homework 8 unit suite", unit_suite),
    ]
    payload = {
        "homework": 8,
        "student": "Vedant Vartak",
        "sid4": settings.sid4,
        "commit_hash": git_hash(),
        "model": settings.model,
        "configuration": {
            "port_base": settings.port_base,
            "prefix": settings.prefix,
            "domain_id": settings.domain_id,
        },
        "seed": settings.seed,
        "verify_seed": settings.verify_seed,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for item in checks:
        print(("PASS" if item["passed"] else "FAIL"), item["name"], "-", item["detail"])
    print("verification_json=", OUTPUT)
    if not payload["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
