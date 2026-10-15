#!/usr/bin/env python3
"""Produce the deterministic Homework 6 verification record."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT_BOOTSTRAP = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT_BOOTSTRAP) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_BOOTSTRAP))

from code.hw6.config import PROJECT_ROOT, settings


def run(command: list[str]) -> tuple[bool, str]:
    result = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True)
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


def main() -> None:
    report_dir = PROJECT_ROOT / "reports" / "hw06"
    report_dir.mkdir(parents=True, exist_ok=True)
    tests_pass, tests_output = run([sys.executable, "-m", "unittest", "tests.test_hw06", "-v"])
    compile_pass, compile_output = run([sys.executable, "-m", "compileall", "-q", "code/hw6", "scripts/run_hw06_memory_experiment.py"])
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
    required = [
        "AGENT.md", "MEMORY.md", "docker-compose.hw6.yml", "code/hw6/config.py",
        "code/hw6/db.py", "code/hw6/memory.py", "reports/hw06/MEMORY.original.md",
        "reports/hw06/memory_probes.yaml", "reports/hw06/AI_USE.md",
    ]
    files_pass = all((PROJECT_ROOT / path).exists() for path in required)
    raw_dir = report_dir / "raw"
    try:
        database_evidence = json.loads((raw_dir / "database_crud_evidence.json").read_text())
        database_pass = (
            database_evidence["create"]["status_code"] == 201
            and database_evidence["delete"]["status_code"] == 204
            and database_evidence["mongo_schema_validation"]["blocked"] is True
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        database_pass = False
    try:
        experiment = json.loads((raw_dir / "experiment_summary.json").read_text())
        experiment_pass = len(experiment) == 4 and all(
            item["conversation_turns"] == 30
            and len(item["probe_scores"]) == 5
            and sum(1 for _ in (raw_dir / f"{item['name']}_transcript.jsonl").open()) == 35
            for item in experiment
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        experiment_pass = False
    try:
        memory_evidence = json.loads((raw_dir / "memory_api_evidence.json").read_text())
        memory_pass = (
            len(memory_evidence["conversation"]) == 10
            and memory_evidence["mongo_collections"]["message_count"] == 20
            and memory_evidence["mongo_collections"]["summary_count"] >= 2
            and memory_evidence["mongo_collections"]["episode_count"] >= 10
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        memory_pass = False
    try:
        file_evidence = json.loads((raw_dir / "file_memory_evidence.json").read_text())
        file_memory_pass = (
            file_evidence["meaningful_lines_before"] == 55
            and file_evidence["meaningful_lines_after"] < 40
            and not file_evidence["incorrect_resolutions"]
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        file_memory_pass = False
    record = {
        "homework": 6,
        "student": "Vedant Vartak",
        "sid4": settings.sid4,
        "commit": commit,
        "model": settings.ollama_model,
        "config": {
            "port_base": settings.port_base,
            "prefix": settings.prefix,
            "database": settings.mongo_database,
            "domain_id": settings.domain_id,
            "short_term_n": settings.short_term_n,
            "summarize_every_user_messages": settings.summarize_every_user_messages,
            "episodic_top_k": settings.episodic_top_k,
        },
        "seeds": {"seed": settings.seed, "verify_seed": settings.verify_seed},
        "checks": {
            "offline_tests": {"pass": tests_pass, "details": tests_output},
            "python_compile": {"pass": compile_pass, "details": compile_output or "compileall passed"},
            "required_files": {"pass": files_pass, "details": required},
            "mongodb_crud_evidence": {"pass": database_pass},
            "memory_experiment": {"pass": experiment_pass, "details": "4 runs x (30 conversation turns + 5 probes)"},
            "live_memory_evidence": {"pass": memory_pass, "details": "10 user turns with MongoDB messages, summaries, and episodes"},
            "file_memory_consolidation": {"pass": file_memory_pass, "details": "55 meaningful lines consolidated below 40 with audited conflicts"},
        },
        "pass": tests_pass and compile_pass and files_pass and database_pass and experiment_pass and memory_pass and file_memory_pass,
    }
    destination = report_dir / "verification.json"
    destination.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    raise SystemExit(0 if record["pass"] else 1)


if __name__ == "__main__":
    main()
