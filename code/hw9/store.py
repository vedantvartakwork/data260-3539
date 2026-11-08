"""SQLite primary store with a Redis-backed recall view counter."""

from __future__ import annotations

import json
import sqlite3
from code.hw9.config import settings
from pathlib import Path
from typing import Any

SEED_RECALLS = [
    (
        "REC-3539-00001",
        "Frozen Shrimp Lot 00001",
        "Ocean Harvest",
        "Produce",
        6535,
        "Possible undeclared sulfites",
        "Return the product for a refund.",
    ),
    (
        "REC-3539-00002",
        "Chicken Salad Lot 00002",
        "Campus Kitchen",
        "Packaged Foods",
        18135,
        "Possible Listeria contamination",
        "Do not consume; discard or return it.",
    ),
    (
        "REC-3539-00003",
        "Greek Yogurt Lot 00003",
        "Valley Dairy",
        "Dairy and Refrigerated",
        13799,
        "Incorrect allergen label",
        "Return unopened containers.",
    ),
    (
        "REC-3539-00004",
        "Tuna Salad Lot 00004",
        "Harbor Foods",
        "Meat and Seafood",
        9200,
        "Potential foreign material",
        "Stop use and request a refund.",
    ),
    (
        "REC-3539-00005",
        "Granola Bars Lot 00005",
        "Campus Pantry",
        "Packaged Foods",
        3539,
        "Undeclared peanut allergen",
        "Return the packages for a full refund.",
    ),
    (
        "REC-3539-00006",
        "Spinach Bag Lot 00006",
        "Green Fields",
        "Produce",
        7450,
        "Possible E. coli contamination",
        "Discard the spinach immediately.",
    ),
    (
        "REC-3539-00007",
        "Ground Beef Lot 00007",
        "Prairie Meats",
        "Meat and Seafood",
        12000,
        "Possible Salmonella contamination",
        "Cook only if directed or return it.",
    ),
    (
        "REC-3539-00008",
        "Cheddar Slices Lot 00008",
        "Valley Dairy",
        "Dairy and Refrigerated",
        6800,
        "Packaging seal failure",
        "Return packages with a broken seal.",
    ),
    (
        "REC-3539-00009",
        "Tomato Salsa Lot 00009",
        "Southwest Foods",
        "Packaged Foods",
        4100,
        "Incorrect best-by date",
        "Check the lot code and discard expired jars.",
    ),
    (
        "REC-3539-00010",
        "Apple Slices Lot 00010",
        "Fresh Start",
        "Produce",
        5300,
        "Possible sanitation failure",
        "Return or discard the affected lot.",
    ),
]


class RecallStore:
    def __init__(self, db_path: str | Path, redis_client: Any) -> None:
        self.db_path = str(db_path)
        self.redis = redis_client
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._setup()

    def _setup(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS recalls (
                recall_code TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                manufacturer TEXT NOT NULL,
                category TEXT NOT NULL,
                units_affected INTEGER NOT NULL,
                recall_details TEXT NOT NULL,
                guidance TEXT NOT NULL,
                view_count INTEGER NOT NULL DEFAULT 0,
                data_version INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        count = self.connection.execute("SELECT COUNT(*) FROM recalls").fetchone()[0]
        if count == 0:
            self.connection.executemany(
                """
                INSERT INTO recalls (
                    recall_code, product_name, manufacturer, category, units_affected,
                    recall_details, guidance
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                SEED_RECALLS,
            )
            self.connection.commit()

    def list_recalls(self) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM recalls ORDER BY recall_code").fetchall()
        return [dict(row) for row in rows]

    def get_recall(self, recall_code: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM recalls WHERE recall_code = ?", (recall_code,)
        ).fetchone()
        return dict(row) if row else None

    def increment_recall_views(self, recall_code: str) -> int:
        """Increment Redis on every access and sync to SQLite every tenth increment."""
        if self.get_recall(recall_code) is None:
            raise KeyError(f"Unknown recall: {recall_code}")
        key = f"{settings.view_prefix}{recall_code}"
        current = int(self.redis.incr(key))
        if current % 10 == 0:
            self.connection.execute(
                "UPDATE recalls SET view_count = ? WHERE recall_code = ?",
                (current, recall_code),
            )
            self.connection.commit()
            print(f"Synced views to database: {recall_code}={current}")
        return current

    def reset_view_counter(self, recall_code: str) -> None:
        self.redis.delete(f"{settings.view_prefix}{recall_code}")
        self.connection.execute(
            "UPDATE recalls SET view_count = 0 WHERE recall_code = ?", (recall_code,)
        )
        self.connection.commit()

    def update_units(self, recall_code: str, units_affected: int) -> int:
        if units_affected <= 0:
            raise ValueError("units_affected must be positive")
        cursor = self.connection.execute(
            """
            UPDATE recalls
            SET units_affected = ?, data_version = data_version + 1
            WHERE recall_code = ?
            """,
            (units_affected, recall_code),
        )
        if cursor.rowcount != 1:
            raise KeyError(f"Unknown recall: {recall_code}")
        self.connection.commit()
        row = self.get_recall(recall_code)
        assert row is not None
        return int(row["data_version"])

    def export_reference(self) -> list[dict[str, Any]]:
        return json.loads(json.dumps(self.list_recalls()))

    def close(self) -> None:
        self.connection.close()
