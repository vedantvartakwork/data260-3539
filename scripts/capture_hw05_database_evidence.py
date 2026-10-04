#!/usr/bin/env python3
"""Print and save concise live MySQL schema/count evidence for HW5."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import inspect, text


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from code.web_application.db import engine


OUTPUT = ROOT / "reports/hw05/raw/database_evidence.txt"


def main() -> None:
    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())
    with engine.connect() as connection:
        counts = {
            table: connection.scalar(text(f"SELECT COUNT(*) FROM `{table}`"))
            for table in ("manufacturers", "recall_notices", "recall_events", "users", "sessions")
        }
    lines = [
        "VEDANT VARTAK — DATA 260 HOMEWORK 5 — MYSQL EVIDENCE",
        f"timestamp_utc: {datetime.now(timezone.utc).isoformat()}",
        "database: s3539_rel",
        "tables: " + ", ".join(tables),
        "",
        "row_counts:",
        *[f"  {name}: {count}" for name, count in counts.items()],
        "",
    ]
    for table in ("manufacturers", "recall_notices"):
        lines.append(f"{table}_columns:")
        for column in inspector.get_columns(table):
            lines.append(
                f"  {column['name']} | {column['type']} | nullable={column['nullable']}"
            )
        lines.append("")
    foreign_keys = inspector.get_foreign_keys("recall_notices")
    lines.append("recall_notices_foreign_keys:")
    for key in foreign_keys:
        lines.append(
            f"  {key['name']}: {key['constrained_columns']} -> "
            f"{key['referred_table']}{key['referred_columns']} ondelete={key['options'].get('ondelete')}"
        )
    output = "\n".join(lines) + "\n"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(output, encoding="utf-8")
    print(output, end="")
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
