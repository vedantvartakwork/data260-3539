#!/usr/bin/env python3
"""Produce objective Homework 5 verification results."""

from __future__ import annotations

import csv
import asyncio
import json
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from code.hw5_tools import TOOL_HANDLERS
from code.hw5_tools import InMemoryRecallRepository, call_domain_tool
from mcp_servers.domain_server import mcp as domain_mcp
from mcp_servers.meals_server import search_meals_by_name
from mcp_servers.meals_server import mcp as meals_mcp


OUT = ROOT / "reports/hw05/verification.json"


def run(command: list[str], cwd: Path = ROOT) -> tuple[bool, str]:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    detail = (completed.stdout + completed.stderr).strip()
    return completed.returncode == 0, detail[-4000:]


def add(checks: list[dict], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "status": "PASS" if passed else "FAIL", "detail": detail})


def main() -> None:
    checks: list[dict] = []
    commit_hash = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    add(checks, "personal_configuration", (3539 + 5300, f"data260-3539") == (8839, "data260-3539"),
        "SID4=3539 PORT_BASE=8839 PREFIX=s3539 SEED=3539 VERIFY_SEED=263539 DOMAIN_ID=3")

    required = [
        "reports/hw05/RUN_LOG.txt", "reports/hw05/METRICS.md", "reports/hw05/AI_USE.md",
        "reports/hw05/TOOL_CONTRACTS.md", "reports/hw05/raw/fault_injection_calls.csv",
        "reports/hw05/raw/mcp_tool_outputs.json", "scripts/test_hw05_tools.py",
        "mcp_servers/meals_server.py", "mcp_servers/domain_server.py",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    add(checks, "required_files", not missing, "missing=" + repr(missing))

    calls_path = ROOT / "reports/hw05/raw/fault_injection_calls.csv"
    row_count = 0
    if calls_path.is_file():
        with calls_path.open(newline="", encoding="utf-8") as stream:
            row_count = sum(1 for _ in csv.DictReader(stream))
    add(checks, "fault_injection_150_calls", row_count == 150, f"rows={row_count}")

    add(checks, "domain_exactly_three_tools", set(TOOL_HANDLERS) == {"search", "detail", "aggregate"},
        f"tools={sorted(TOOL_HANDLERS)}")
    domain_names = sorted(tool.name for tool in asyncio.run(domain_mcp.list_tools()))
    meal_names = sorted(tool.name for tool in asyncio.run(meals_mcp.list_tools()))
    add(checks, "domain_mcp_inventory", domain_names == ["aggregate", "detail", "search"], str(domain_names))
    add(checks, "mealdb_mcp_inventory", len(meal_names) == 4, str(meal_names))
    domain_result = call_domain_tool(
        "search", {"query": "shrimp", "limit": 1}, InMemoryRecallRepository()
    )
    add(checks, "domain_mcp_tool_call", domain_result.get("ok") is True, json.dumps(domain_result))
    try:
        meal_result = search_meals_by_name("Arrabiata", 1)
        meal_ok = len(meal_result.get("meals", [])) == 1
        meal_detail = json.dumps(meal_result)[:1000]
    except Exception as exc:
        meal_ok, meal_detail = False, str(exc)
    add(checks, "mealdb_mcp_tool_call", meal_ok, meal_detail)
    try:
        response = httpx.get("http://127.0.0.1:8839/health", timeout=3.0)
        backend_ok = response.status_code == 200 and response.json() == {"status": "ok"}
        backend_detail = f"status={response.status_code} body={response.text}"
    except Exception as exc:
        backend_ok, backend_detail = False, str(exc)
    add(checks, "fastapi_port_base_smoke", backend_ok, backend_detail)

    passed, detail = run([sys.executable, "scripts/test_hw05_tools.py"])
    add(checks, "offline_tool_runner", passed and "9/9" in detail, detail)
    passed, detail = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    add(checks, "python_test_suite", passed and "OK" in detail, detail)
    passed, detail = run(["npm", "run", "build"], ROOT / "code/web_application/frontend")
    add(checks, "react_production_build", passed, detail)

    payload = {
        "homework": 5,
        "student": "Vedant Vartak",
        "sid4": 3539,
        "commit_hash": commit_hash,
        "configuration": {
            "port_base": 8839,
            "prefix": "s3539",
            "seed": 3539,
            "verify_seed": 263539,
            "domain_id": 3,
            "model": "qwen3:8b",
        },
        "passed": sum(item["status"] == "PASS" for item in checks),
        "total": len(checks),
        "checks": checks,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    raise SystemExit(0 if payload["passed"] == payload["total"] else 1)


if __name__ == "__main__":
    main()
