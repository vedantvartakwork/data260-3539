"""Create and deterministically seed the cumulative Homework 5 database."""

from __future__ import annotations

import random
import sys
from pathlib import Path

from sqlalchemy import delete, inspect, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from code.web_application.db import Base, db_session_basede26, engine
from code.web_application.models import (
    Manufacturer,
    RecallEvent,
    RecallNotice,
    SessionRecord,
    User,
)
from code.web_application.security import hash_password


SEED = 3539
PRIMARY_ROWS = 500
RELATED_EVENT_ROWS = 200
MANUFACTURER_ROWS = 12
CATEGORIES = [
    "Produce",
    "Meat and Seafood",
    "Dairy and Refrigerated",
    "Packaged Foods",
]
PRODUCTS = [
    "Baby Spinach",
    "Greek Yogurt",
    "Peanut Butter",
    "Frozen Shrimp",
    "Granola Bars",
    "Cheddar Cheese",
    "Chicken Salad",
    "Apple Juice",
]
ISSUES = [
    "may contain an undeclared allergen and should be returned for a refund",
    "may have an incorrect expiration date printed on the package",
    "may be contaminated and should not be consumed",
    "was packaged with an incorrect ingredient label",
]


def make_manufacturers() -> list[Manufacturer]:
    return [
        Manufacturer(
            name=f"Grocery Safety Manufacturer {number:02d}",
            contact_name=f"Safety Contact {number:02d}",
            contact_email=f"safety{number:02d}@example.edu",
        )
        for number in range(1, MANUFACTURER_ROWS + 1)
    ]


def ensure_hw5_schema() -> None:
    """Apply the cumulative HW5 additions without destroying existing HW4 data."""
    Base.metadata.create_all(engine)
    # SQLite is used only for isolated local/test evidence; create_all already
    # produces the final schema, while the migration SQL below is MySQL-only.
    if engine.dialect.name == "sqlite":
        return
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("recall_notices")}

    with engine.begin() as connection:
        if "recall_code" not in columns:
            connection.execute(
                text("ALTER TABLE recall_notices ADD COLUMN recall_code VARCHAR(32) NULL AFTER product_name")
            )
        if "units_affected" not in columns:
            connection.execute(
                text("ALTER TABLE recall_notices ADD COLUMN units_affected INT NOT NULL DEFAULT 0 AFTER recall_code")
            )
        if "manufacturer_id" not in columns:
            connection.execute(
                text("ALTER TABLE recall_notices ADD COLUMN manufacturer_id INT NULL AFTER units_affected")
            )
        if "updated_at" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE recall_notices ADD COLUMN updated_at DATETIME NOT NULL "
                    "DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at"
                )
            )

        placeholder_id = connection.scalar(
            text(
                "SELECT id FROM manufacturers "
                "WHERE contact_email = 'legacy-manufacturer@example.edu' LIMIT 1"
            )
        )
        if placeholder_id is None:
            result = connection.execute(
                text(
                    "INSERT INTO manufacturers (name, contact_name, contact_email) "
                    "VALUES ('Legacy Recall Manufacturer', 'Recall Coordinator', "
                    "'legacy-manufacturer@example.edu')"
                )
            )
            placeholder_id = result.lastrowid
        connection.execute(
            text(
                "UPDATE recall_notices SET "
                "recall_code = COALESCE(recall_code, CONCAT('REC-', LPAD(id, 6, '0'))), "
                "manufacturer_id = COALESCE(manufacturer_id, :manufacturer_id)"
            ),
            {"manufacturer_id": placeholder_id},
        )

    inspector = inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("recall_notices")}
    unique_names = {
        constraint.get("name")
        for constraint in inspector.get_unique_constraints("recall_notices")
    }
    foreign_names = {
        constraint.get("name")
        for constraint in inspector.get_foreign_keys("recall_notices")
    }
    with engine.begin() as connection:
        if columns["recall_code"].get("nullable", True):
            connection.execute(
                text("ALTER TABLE recall_notices MODIFY recall_code VARCHAR(32) NOT NULL")
            )
        if columns["manufacturer_id"].get("nullable", True):
            connection.execute(
                text("ALTER TABLE recall_notices MODIFY manufacturer_id INT NOT NULL")
            )
        if "uq_recall_notices_code" not in unique_names:
            connection.execute(
                text(
                    "ALTER TABLE recall_notices ADD CONSTRAINT "
                    "uq_recall_notices_code UNIQUE (recall_code)"
                )
            )
        if "fk_recall_notices_manufacturer" not in foreign_names:
            connection.execute(
                text(
                    "ALTER TABLE recall_notices ADD CONSTRAINT fk_recall_notices_manufacturer "
                    "FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id) ON DELETE RESTRICT"
                )
            )


def main() -> None:
    rng = random.Random(SEED)
    ensure_hw5_schema()

    with db_session_basede26() as db:
        db.execute(delete(SessionRecord))
        db.execute(delete(RecallEvent))
        db.execute(delete(RecallNotice))
        db.execute(delete(Manufacturer))
        db.execute(delete(User))
        db.commit()

        db.add(
            User(
                name="Recall Coordinator",
                email="admin@example.edu",
                password_hash=hash_password("password"),
            )
        )
        manufacturers = make_manufacturers()
        db.add_all(manufacturers)
        db.flush()

        recalls: list[RecallNotice] = []
        for number in range(1, PRIMARY_ROWS + 1):
            manufacturer = rng.choice(manufacturers)
            product = rng.choice(PRODUCTS)
            recalls.append(
                RecallNotice(
                    product_name=f"{product} Lot {number:05d}",
                    recall_code=f"REC-{SEED}-{number:05d}",
                    units_affected=rng.randint(10, 20_000),
                    manufacturer_id=manufacturer.id,
                    brand_name=manufacturer.name,
                    submitter_email=f"recall{number}@example.edu",
                    category=rng.choice(CATEGORIES),
                    recall_details=(
                        f"{manufacturer.name} {product} lot {number:05d} "
                        f"{rng.choice(ISSUES)}. Consumers should follow the recall instructions."
                    ),
                    terms_accepted=True,
                )
            )
        db.add_all(recalls)
        db.flush()

        db.add_all(
            RecallEvent(
                recall_id=recalls[number - 1].id,
                event_type=rng.choice(["notice", "distribution", "follow-up"]),
                note=f"Seeded related recall event {number:03d} using SEED {SEED}.",
            )
            for number in range(1, RELATED_EVENT_ROWS + 1)
        )
        db.commit()

        counts = {
            "manufacturers": db.scalar(text("SELECT COUNT(*) FROM manufacturers")),
            "recall_notices": db.scalar(text("SELECT COUNT(*) FROM recall_notices")),
            "recall_events": db.scalar(text("SELECT COUNT(*) FROM recall_events")),
            "users": db.scalar(text("SELECT COUNT(*) FROM users")),
        }

    print("HOMEWORK 5 - MYSQL SEED")
    print("Database: s3539_rel")
    print(f"SEED: {SEED}")
    for name, count in counts.items():
        print(f"{name}: {count}")
    print("Demo login: admin@example.edu / password")


if __name__ == "__main__":
    main()
