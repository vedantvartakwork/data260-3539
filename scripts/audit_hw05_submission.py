"""Audit the selected HW5 package without rerunning or replacing experiments."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
REPORT_HASH = "d80ec37e2fa520c02229d347d7f3441941b8e2a5c4b94986dafec2ce81b42cd8"
REQUIRED = [
    "README.md", "Makefile", "requirements.txt", "docker-compose.hw4.yml",
    "code/hw5_tools.py", "code/hw5_retry.py", "code/hw5_agent.py",
    "code/web_application/backend.py", "code/web_application/db.py",
    "code/web_application/models.py", "code/web_application/schemas.py",
    "code/web_application/security.py", "code/web_application/routers/recalls.py",
    "code/web_application/routers/manufacturers.py",
    "code/web_application/frontend/src/store.js",
    "code/web_application/frontend/src/features/recalls/recallsSlice.js",
    "code/web_application/frontend/src/components/Home.jsx",
    "code/web_application/frontend/src/components/CreateRecord.jsx",
    "code/web_application/frontend/src/components/UpdateRecord.jsx",
    "code/web_application/frontend/src/components/DeleteRecord.jsx",
    "mcp_servers/domain_server.py", "mcp_servers/meals_server.py",
    "sql/hw05_migration.sql", "scripts/test_hw05_tools.py",
    "scripts/verify_hw05.py", "scripts/run_hw05_api_integration.py",
    "scripts/run_hw05_agent_scenarios.py", "scripts/run_hw05_fault_experiment.py",
    "reports/hw05/report.pdf", "output/pdf/Vartak_HW5.pdf",
    "reports/hw05/verification.json", "reports/hw05/RUN_LOG.txt",
    "reports/hw05/METRICS.md", "reports/hw05/AI_USE.md",
    "reports/hw05/REFLECTION.md", "reports/hw05/TOOL_CONTRACTS.md",
    "reports/hw05/raw/fault_injection_calls.csv",
    "reports/hw05/raw/fault_injection_summary.json",
    "reports/hw05/raw/agent_runs.jsonl", "reports/hw05/raw/agent_scenario_summary.json",
    "reports/hw05/raw/inspector_final_calls.json",
    "reports/hw05/raw/mcp_tool_outputs.json", "reports/hw05/raw/api_integration.json",
    "reports/hw05/raw/database_evidence.txt",
    "reports/hw05/postman/DATA260_HW5.postman_collection.json",
    "reports/hw05/postman/DATA260_HW5.postman_environment.json",
]


def read_json(path: str):
    return json.loads((ROOT / path).read_text())


def main() -> None:
    missing = [p for p in REQUIRED if not (ROOT / p).is_file()]
    assert not missing, missing
    checks = ["required_file_inventory"]
    for path in ("reports/hw05/report.pdf", "output/pdf/Vartak_HW5.pdf"):
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == REPORT_HASH
        assert len(PdfReader(ROOT / path).pages) == 48
    checks.append("exact_selected_report_48_pages_sha256")

    rows = list(csv.DictReader((ROOT / "reports/hw05/raw/fault_injection_calls.csv").open()))
    assert len(rows) == 150
    rng = random.Random(263539)
    for row in rows:
        assert int(row["verify_seed"]) == 263539
        expected = []
        for _ in range(3):
            failed = rng.random() < float(row["injected_failure_rate"])
            expected.append("failure" if failed else "success")
            if not failed:
                break
        assert row["attempt_outcomes"] == "|".join(expected)
        assert int(row["attempts"]) == len(expected)
        assert (row["success"] == "True") == (expected[-1] == "success")
    checks.append("all_150_seeded_failure_sequences")
    actual = []
    metrics = (ROOT / "reports/hw05/METRICS.md").read_text()
    for rate in (0.0, 0.2, 0.5):
        group = [r for r in rows if float(r["injected_failure_rate"]) == rate]
        assert len(group) == 50
        latencies = [float(r["latency_ms"]) for r in group]
        item = {"injected_failure_rate": rate, "calls": 50,
                "success_rate": sum(r["success"] == "True" for r in group) / 50,
                "mean_latency_ms": round(statistics.fmean(latencies), 3),
                "p99_latency_ms": sorted(latencies)[math.ceil(0.99 * 50) - 1]}
        actual.append(item)
        assert f'{item["mean_latency_ms"]:.3f}' in metrics
        assert f'{item["p99_latency_ms"]:.3f}' in metrics
    assert actual == read_json("reports/hw05/raw/fault_injection_summary.json")["summaries"]
    checks.append("retained_csv_summary_metrics_alignment")

    wire = read_json("reports/hw05/raw/mcp_tool_outputs.json")
    domain = wire["domain_server"]["calls"]
    assert len(domain) == 6
    for name in ("search", "detail", "aggregate"):
        calls = [c for c in domain if c["tool"] == name]
        assert {c["expected"] for c in calls} == {"success", "rejected"}
        for call in calls:
            result = call["output"]["structuredContent"]
            assert set(result) == {"ok", "data", "error"}
            assert result["ok"] == (call["expected"] == "success")
    meals = read_json("reports/hw05/raw/inspector_final_calls.json")
    assert len(meals) == 4
    assert {c["tool"] for c in meals} == {
        "search_meals_by_name", "meals_by_ingredient", "meal_details", "random_meal"}
    assert all(not c["output"].get("isError") for c in meals)
    checks.append("all_four_mealdb_and_six_domain_saved_calls")

    log = [json.loads(line) for line in (ROOT / "reports/hw05/raw/agent_runs.jsonl").read_text().splitlines()]
    stops = [r for r in log if r.get("event") == "stop"]
    scenarios = read_json("reports/hw05/raw/agent_scenario_summary.json")
    assert len(stops) == len(scenarios) == 4
    for saved, summary in zip(stops, scenarios):
        for key in ("step_count", "tool_call_count", "stop_reason", "final_answer"):
            assert saved[key] == summary[key]
    checks.append("four_scenarios_match_agent_jsonl")
    api = read_json("reports/hw05/raw/api_integration.json")
    assert api["passed"] == api["total"] == 14
    assert all(c["status"] == c["expected"] for c in api["checks"])
    checks.append("saved_api_14_of_14")
    verification = read_json("reports/hw05/verification.json")
    assert verification["homework"] == 5 and verification["sid4"] == 3539
    assert verification["passed"] == verification["total"] == 14
    checks.append("live_verification_14_of_14")

    payload = {
        "homework": 5, "sid4": 3539,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "audited_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "report_sha256": REPORT_HASH, "report_pages": 48,
        "passed": len(checks), "total": len(checks),
        "checks": [{"name": name, "status": "PASS"} for name in checks],
        "required_files": REQUIRED,
        "collaborator_access": {"supriyaselvanganesan": "write", "Sbnikitha": "pending_write_invitation"},
        "access_checked_utc_date": "2026-10-05",
        "note": "Application baseline hash on PDF cover precedes selected-report packaging. Resolve the final hw5 tag via Git. Collaborator acceptance and Canvas upload are separate pending actions.",
    }
    (ROOT / "reports/hw05/submission_audit.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
