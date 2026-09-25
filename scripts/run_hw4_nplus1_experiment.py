"""Measure the naive and fixed recall-list endpoints over 180 requests."""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import httpx


PAGE_SIZES = (10, 50, 200)
IMPLEMENTATIONS = ("naive", "fixed")
RUNS_PER_CASE = 30


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8839")
    parser.add_argument("--email", default="admin@example.edu")
    parser.add_argument("--password", default="password")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/hw04/raw"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []

    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": args.email, "password": args.password},
        )
        login.raise_for_status()

        for page_size in PAGE_SIZES:
            for implementation in IMPLEMENTATIONS:
                endpoint = f"/api/v1/recalls/{implementation}"
                for run_number in range(1, RUNS_PER_CASE + 1):
                    started = time.perf_counter()
                    response = client.get(endpoint, params={"page_size": page_size})
                    latency_ms = (time.perf_counter() - started) * 1000
                    response.raise_for_status()
                    body = response.json()
                    rows.append(
                        {
                            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                            "implementation": implementation,
                            "page_size": page_size,
                            "run": run_number,
                            "sql_queries": int(response.headers["X-SQL-Query-Count"]),
                            "latency_ms": round(latency_ms, 3),
                            "records_returned": len(body["records"]),
                        }
                    )

    csv_path = args.output_dir / "n_plus_one_requests.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    json_path = args.output_dir / "n_plus_one_requests.json"
    json_path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    print("HOMEWORK 4 - N+1 EXPERIMENT")
    print(f"Measured requests: {len(rows)}")
    for page_size in PAGE_SIZES:
        for implementation in IMPLEMENTATIONS:
            subset = [
                row for row in rows
                if row["page_size"] == page_size
                and row["implementation"] == implementation
            ]
            print(
                f"page_size={page_size:3d} implementation={implementation:5s} "
                f"runs={len(subset):2d} queries={subset[0]['sql_queries']:3d} "
                f"mean_ms={mean(float(row['latency_ms']) for row in subset):.3f}"
            )
    print(f"Raw CSV: {csv_path}")
    print(f"Raw JSON: {json_path}")


if __name__ == "__main__":
    main()
