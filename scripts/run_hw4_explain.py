"""Capture MySQL EXPLAIN output before and after adding one index."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from code.web_application.db import engine


RAW_DIR = Path("reports/hw04/raw")
INDEX_NAME = "idx_recall_notices_category"
EXPLAIN_SQL = "EXPLAIN SELECT * FROM recall_notices WHERE category = 'Produce'"


def rows_as_dicts(connection, statement: str) -> list[dict[str, object]]:
    result = connection.execute(text(statement))
    return [dict(row._mapping) for row in result]


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with engine.begin() as connection:
        existing = connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() "
                "AND table_name = 'recall_notices' "
                "AND index_name = :index_name"
            ),
            {"index_name": INDEX_NAME},
        ).scalar_one()
        if existing:
            connection.execute(text(f"DROP INDEX {INDEX_NAME} ON recall_notices"))

        before = rows_as_dicts(connection, EXPLAIN_SQL)
        connection.execute(
            text(f"CREATE INDEX {INDEX_NAME} ON recall_notices (category)")
        )
        after = rows_as_dicts(connection, EXPLAIN_SQL)

    (RAW_DIR / "explain_before.json").write_text(
        json.dumps(before, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    (RAW_DIR / "explain_after.json").write_text(
        json.dumps(after, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print("HOMEWORK 4 - MYSQL INDEX EXPLAIN")
    print("Before index:")
    print(json.dumps(before, indent=2, default=str))
    print("After index:")
    print(json.dumps(after, indent=2, default=str))


if __name__ == "__main__":
    main()
