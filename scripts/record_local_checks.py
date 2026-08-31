#!/usr/bin/env python3
"""Append real local environment and Docker checks to RUN_LOG.txt."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path


def run(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def main() -> None:
    commands = [
        ["python3.12", "--version"],
        ["docker", "inspect", "--format", "{{.State.Status}}|{{.State.Health.Status}}", "data260-3539-hw1"],
        ["curl", "--fail", "--silent", "--show-error", "http://127.0.0.1:8839/"],
        ["python3.12", "-m", "unittest", "discover", "-s", "tests", "-v"],
        ["node", "tests/test_app_js.mjs"],
    ]
    lines = [f"[{datetime.now(timezone.utc).isoformat()}] Started local verification"]
    for command in commands:
        returncode, output = run(command)
        concise = output if len(output) <= 4000 else output[:4000] + "\n[output truncated in run log]"
        lines.extend([f"$ {' '.join(command)}", concise, f"exit_code={returncode}"])
        if returncode != 0:
            raise SystemExit(f"Local check failed: {' '.join(command)}")
    lines.append(f"[{datetime.now(timezone.utc).isoformat()}] Finished local verification successfully")
    with Path("reports/hw01/RUN_LOG.txt").open("a", encoding="utf-8") as handle:
        handle.write("\n" + "\n".join(lines) + "\n")
    print("Recorded successful local checks in reports/hw01/RUN_LOG.txt")


if __name__ == "__main__":
    main()
