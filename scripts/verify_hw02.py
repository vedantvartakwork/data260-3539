#!/usr/bin/env python3
"""Run objective HW2 smoke checks and write reports/hw02/verification.json."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.hw2_graph import run_graph
from src.model_client import CompletionResult


class SmokeClient:
    def __init__(self) -> None:
        self.call = 0

    def complete(self, messages, tools=None, *, temperature=None, json_mode=False):
        self.call += 1
        if self.call == 1:
            content = '{"tags":["spinach recall","almond allergen","Valley Harvest"],"summary":"Valley Harvest recalls spinach bags because they may contain undeclared almonds."}'
        else:
            content = '{"has_issues":false,"notes":[]}'
        return CompletionResult(content, 10, 5, "smoke", 1)


def check(name: str, passed: bool, details: str) -> dict[str, object]:
    return {"name": name, "passed": bool(passed), "details": details}


def main() -> None:
    checks: list[dict[str, object]] = []
    required = [
        "code/web_application/backend.py",
        "code/web_application/index.html",
        "code/web_application/styles.css",
        "code/web_application/app.js",
        "code/hw2_graph.py",
        "src/model_client.py",
        "reports/hw02/cases/schema_input.json",
        "reports/hw02/cases/adversarial_input.json",
        "reports/hw02/RUN_LOG.txt",
        "reports/hw02/METRICS.md",
        "reports/hw02/AI_USE.md",
        "reports/hw02/reproducible_run_instructions",
    ]
    missing = [path for path in required if not Path(path).is_file()]
    checks.append(check("required_files", not missing, "all required files present" if not missing else f"missing: {missing}"))

    tests = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        capture_output=True,
        text=True,
    )
    checks.append(check("unit_tests", tests.returncode == 0, (tests.stdout + tests.stderr).strip()[-5000:]))

    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "code.web_application.backend:app", "--host", "127.0.0.1", "--port", "8839"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    web_ok = False
    web_detail = "server did not respond"
    try:
        for _ in range(30):
            try:
                with urllib.request.urlopen("http://127.0.0.1:8839/health", timeout=1) as response:
                    body = json.load(response)
                    web_ok = response.status == 200 and body == {"status": "ok"}
                    web_detail = f"HTTP {response.status} on PORT_BASE 8839"
                    break
            except Exception:
                time.sleep(0.1)
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
    checks.append(check("fastapi_port_base", web_ok, web_detail))

    graph = run_graph(
        "Recall",
        "Valley Harvest spinach may contain undeclared almonds and should be returned.",
        "recalls@example.edu",
        client=SmokeClient(),
        max_turns=2,
    )
    final_output = graph.get("final_output") or {}
    graph_ok = graph["status"] == "completed" and len(final_output.get("tags", [])) == 3
    checks.append(check("langgraph_finishes", graph_ok, f"status={graph['status']}; tags={len(final_output.get('tags', []))}"))

    expected_raw = {
        "schema_validation_runs.json": 30,
        "ceiling_comparison_runs.json": 40,
        "adversarial_runs.json": 5,
    }
    raw_ok = True
    raw_details = []
    for name, expected in expected_raw.items():
        path = Path("reports/hw02/raw") / name
        count = len(json.loads(path.read_text(encoding="utf-8"))) if path.is_file() else 0
        raw_ok = raw_ok and count == expected
        raw_details.append(f"{name}={count}/{expected}")
    checks.append(check("experiment_counts", raw_ok, "; ".join(raw_details)))

    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    passed = all(bool(item["passed"]) for item in checks)
    result = {
        "homework": 2,
        "sid4": 3539,
        "commit_hash": commit,
        "model": "qwen3:8b",
        "configuration": {"temperature": 0.7, "port_base": 8839},
        "seed": 3539,
        "verify_seed": 263539,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "passed": passed,
    }
    output = Path("reports/hw02/verification.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
