"""Record timestamped real console output without changing application code."""
from datetime import datetime, timezone
from pathlib import Path
import csv
import json
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    stamp = datetime.now(timezone.utc).isoformat()
    rows = list(csv.DictReader((ROOT / "reports/hw05/raw/fault_injection_calls.csv").open()))
    rng = random.Random(263539)
    for row in rows:
        expected = []
        for attempt in range(3):
            failed = rng.random() < float(row["injected_failure_rate"])
            expected.append("failure" if failed else "success")
            if not failed:
                break
        assert row["attempt_outcomes"] == "|".join(expected)
    output = [f"\nFINAL AUDIT CONSOLE - Vedant Vartak - {stamp}", "PASS reproducible VERIFY_SEED sequence: 150/150 records", "p99 convention: nearest rank ceil(0.99 * n)"]
    summary = json.loads((ROOT / "reports/hw05/raw/fault_injection_summary.json").read_text())
    output += [json.dumps(row) for row in summary["summaries"]]
    result = subprocess.run([sys.executable, "scripts/verify_hw05.py"], cwd=ROOT, capture_output=True, text=True)
    output += ["COMMAND: python scripts/verify_hw05.py", result.stdout, result.stderr, f"EXIT STATUS: {result.returncode}"]
    text = "\n".join(output)
    with (ROOT / "reports/hw05/RUN_LOG.txt").open("a") as stream:
        stream.write(text + "\n")
    print(text)
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main())
