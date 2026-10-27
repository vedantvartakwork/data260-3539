"""Capture reproducible evidence from the live Homework 8 Kafka stack."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "reports" / "hw08" / "raw"
COMPOSE = [
    "docker",
    "compose",
    "-p",
    "data260-hw8",
    "-f",
    "docker-compose.hw8.yml",
]


def run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout + completed.stderr


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat()
    header = f"Vedant Vartak - DATA 260 Homework 8\ntimestamp_utc={timestamp}\n\n"

    (RAW / "docker_ps.txt").write_text(header + run([*COMPOSE, "ps", "--all"]), encoding="utf-8")
    services = [
        "kafka",
        "topic-init",
        "fastapi",
        "recall-worker",
        "planner",
        "writer-1",
        "writer-2",
        "reviewer",
    ]
    (RAW / "kafka_service_logs.txt").write_text(
        header + run([*COMPOSE, "logs", "--no-color", "--tail", "160", *services]),
        encoding="utf-8",
    )
    (RAW / "homework_demo_live.txt").write_text(
        header + run([str(ROOT / ".venv/bin/python"), "-m", "code.hw8.homework_demo"]),
        encoding="utf-8",
    )
    (RAW / "agent_pipeline_live.txt").write_text(
        header + run([str(ROOT / ".venv/bin/python"), "-m", "code.hw8.send_question"]),
        encoding="utf-8",
    )
    print("Captured live Docker Kafka RPC and agent-pipeline evidence in", RAW)


if __name__ == "__main__":
    main()
