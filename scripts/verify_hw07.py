#!/usr/bin/env python3
"""Objective Homework 7 smoke checks and verification.json writer."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "hw07"
RAW = REPORT / "raw"
OUTPUT = REPORT / "verification.json"


def run(command: list[str]) -> tuple[bool, str]:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    message = (completed.stdout + completed.stderr).strip()
    return completed.returncode == 0, message[-2000:]


def check_raw() -> tuple[bool, str]:
    reliability = json.loads((RAW / "tool_reliability_20_model_attempts.json").read_text())
    reflexion = json.loads((RAW / "original_vs_reflexion.json").read_text())
    gate = json.loads((RAW / "safety_gate_10_commands.json").read_text())
    attacks = json.loads((RAW / "prompt_injection_before_after.json").read_text())
    bike_a = json.loads((RAW / "bike_membership_wins_summary.json").read_text())
    bike_b = json.loads((RAW / "bike_pay_per_use_wins_summary.json").read_text())
    auth = json.loads((RAW / "jwt_rbac_http_evidence.json").read_text())
    conditions = {
        "20 real model attempts": len(reliability) == 20
        and all(row["well_formed_after_repair"] for row in reliability),
        "Reflexion comparison": bool(reflexion),
        "10 safety-gate cases": len(gate) == 10,
        "3 prompt-injection attacks": len(attacks.get("attacks", attacks)) == 3,
        "membership scenario": bike_a["dataset_rows"] >= 500
        and bike_a["result"]["decision"] == "Buy Monthly Membership",
        "pay scenario": bike_b["dataset_rows"] >= 500
        and bike_b["result"]["decision"] == "Pay Per Ride/Minute",
        "live auth statuses": auth["invalid_login"]["status_code"] == 401
        and auth["create_writer"]["status_code"] == 201
        and auth["delete_moderator"]["status_code"] == 204,
    }
    return all(conditions.values()), json.dumps(conditions, sort_keys=True)


def main() -> None:
    python = str(ROOT / ".venv" / "bin" / "python")
    ruff = str(ROOT / ".venv" / "bin" / "ruff")
    checks: list[dict[str, object]] = []
    for name, command in (
        ("HW7 unit tests", [python, "-m", "unittest", "tests.test_hw07", "-v"]),
        ("Ruff", [ruff, "check", "code/hw7", "tests/test_hw07.py", "scripts/verify_hw07.py"]),
        ("Python compile", [python, "-m", "compileall", "-q", "code/hw7"]),
    ):
        passed, detail = run(command)
        checks.append({"name": name, "passed": passed, "detail": detail})
    passed, detail = check_raw()
    checks.append({"name": "Raw artifact contracts", "passed": passed, "detail": detail})
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result = {
        "homework": 7,
        "student": "Vedant Vartak",
        "sid4": 3539,
        "commit": commit,
        "model": "qwen3:8b",
        "configuration": {"PORT_BASE": 8839, "PREFIX": "s3539", "DOMAIN_ID": 3},
        "SEED": 3539,
        "VERIFY_SEED": 263539,
        "generated_at": datetime.now(UTC).isoformat(),
        "checks": checks,
        "passed": all(bool(item["passed"]) for item in checks),
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
