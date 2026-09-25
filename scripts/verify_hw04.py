"""Run objective HW4 smoke checks and write verification.json."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from code.web_application.db import db_session_basede26


OUTPUT_PATH = ROOT / "reports/hw04/verification.json"
PORT_BASE = 8839


def commit_hash() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def add_check(checks: list[dict[str, object]], name: str, passed: bool, details: str) -> None:
    checks.append({"name": name, "passed": bool(passed), "details": details})


def wait_for_server(client: httpx.Client) -> None:
    for _ in range(60):
        try:
            if client.get("/health").status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise RuntimeError("FastAPI did not start on PORT_BASE 8839")


def main() -> None:
    checks: list[dict[str, object]] = []
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "code.web_application.backend:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT_BASE),
        ],
        cwd=ROOT,
        env={**os.environ, "SESSION_COOKIE_SECURE": "false"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{PORT_BASE}", timeout=20.0) as client:
            wait_for_server(client)
            health = client.get("/health")
            add_check(checks, "fastapi_health", health.status_code == 200, f"HTTP {health.status_code}")

            unauthorized = client.get("/api/v1/recalls?page_size=10")
            add_check(
                checks,
                "login_required",
                unauthorized.status_code == 401,
                f"HTTP {unauthorized.status_code} without a session",
            )

            login = client.post(
                "/api/v1/auth/login",
                json={"email": "admin@example.edu", "password": "password"},
            )
            cookie = login.headers.get("set-cookie", "").lower()
            cookie_ok = login.status_code == 200 and "httponly" in cookie and "samesite=lax" in cookie
            add_check(checks, "database_session_cookie", cookie_ok, f"HTTP {login.status_code}; HttpOnly/SameSite checked")

            naive = client.get("/api/v1/recalls/naive?page_size=10")
            fixed = client.get("/api/v1/recalls/fixed?page_size=10")
            naive_json = naive.json() if naive.status_code == 200 else {}
            fixed_json = fixed.json() if fixed.status_code == 200 else {}
            add_check(
                checks,
                "naive_list_endpoint",
                naive.status_code == 200 and len(naive_json.get("records", [])) == 10,
                f"HTTP {naive.status_code}; queries={naive_json.get('sql_queries')}",
            )
            add_check(
                checks,
                "fixed_list_endpoint",
                fixed.status_code == 200 and len(fixed_json.get("records", [])) == 10,
                f"HTTP {fixed.status_code}; queries={fixed_json.get('sql_queries')}",
            )
            add_check(
                checks,
                "n_plus_one_removed",
                int(fixed_json.get("sql_queries", 999)) < int(naive_json.get("sql_queries", 0)),
                f"naive={naive_json.get('sql_queries')}, fixed={fixed_json.get('sql_queries')}",
            )
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    with db_session_basede26() as db:
        recall_count = int(db.scalar(text("SELECT COUNT(*) FROM recall_notices")) or 0)
        event_count = int(db.scalar(text("SELECT COUNT(*) FROM recall_events")) or 0)
    add_check(checks, "seeded_primary_rows", recall_count == 5000, f"rows={recall_count}")
    add_check(checks, "seeded_related_rows", event_count == 200, f"rows={event_count}")

    request_csv = ROOT / "reports/hw04/raw/n_plus_one_requests.csv"
    raw_count = 0
    if request_csv.exists():
        with request_csv.open(encoding="utf-8") as handle:
            raw_count = sum(1 for _ in csv.DictReader(handle))
    add_check(checks, "raw_n_plus_one_requests", raw_count == 180, f"rows={raw_count}")

    evaluation_path = ROOT / "reports/hw04/raw/evaluation.json"
    evaluation = json.loads(evaluation_path.read_text()) if evaluation_path.exists() else []
    refusal_rows = [
        row for row in evaluation
        if row.get("configuration") == "context_rag" and row.get("question_id") in {"q5", "q6"}
    ]
    add_check(
        checks,
        "rag_q5_q6_refusals",
        len(refusal_rows) == 2 and all(row.get("refused_when_needed") for row in refusal_rows),
        f"passing refusals={sum(bool(row.get('refused_when_needed')) for row in refusal_rows)}/2",
    )

    frontend_index = ROOT / "code/web_application/frontend/dist/index.html"
    add_check(checks, "react_production_build", frontend_index.exists(), str(frontend_index.relative_to(ROOT)))

    payload = {
        "homework": 4,
        "sid4": 3539,
        "commit_hash": commit_hash(),
        "model_configuration": {
            "llm": "qwen3:8b",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "chunk_size": 500,
            "chunk_overlap": 50,
            "top_k": 3,
        },
        "seed": 3539,
        "verify_seed": 263539,
        "checks": checks,
        "passed": all(bool(check["passed"]) for check in checks),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if not payload["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
