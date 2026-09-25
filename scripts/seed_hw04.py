"""Create the HW4 schema and deterministically seed MySQL test data."""

from __future__ import annotations

import random
import sys
from pathlib import Path

from sqlalchemy import delete, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from code.web_application.db import Base, db_session_basede26, engine
from code.web_application.models import RecallEvent, RecallNotice, SessionRecord, User
from code.web_application.security import hash_password


SEED = 3539
PRIMARY_ROWS = 5_000
RELATED_ROWS = 200
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
BRANDS = [
    "Valley Harvest",
    "Creamy Farm",
    "Sunny Pantry",
    "Coastal Catch",
    "Morning Basket",
    "Golden Dairy",
]
CATEGORIES = [
    "Produce",
    "Meat and Seafood",
    "Dairy and Refrigerated",
    "Packaged Foods",
]
ISSUES = [
    "may contain an undeclared allergen and should be returned for a refund",
    "may have an incorrect expiration date printed on the package",
    "may be contaminated and should not be consumed",
    "was packaged with an incorrect ingredient label",
]


def make_recalls(rng: random.Random) -> list[RecallNotice]:
    rows = []
    for number in range(1, PRIMARY_ROWS + 1):
        product = rng.choice(PRODUCTS)
        brand = rng.choice(BRANDS)
        rows.append(
            RecallNotice(
                product_name=f"{product} Lot {number:05d}",
                brand_name=brand,
                submitter_email=f"recall{number}@example.edu",
                category=rng.choice(CATEGORIES),
                recall_details=(
                    f"{brand} {product} lot {number:05d} {rng.choice(ISSUES)}. "
                    "Consumers should follow the recall instructions."
                ),
                terms_accepted=True,
            )
        )
    return rows


def main() -> None:
    rng = random.Random(SEED)
    Base.metadata.create_all(engine)

    with db_session_basede26() as db:
        db.execute(delete(SessionRecord))
        db.execute(delete(RecallEvent))
        db.execute(delete(RecallNotice))
        db.execute(delete(User))
        db.commit()

        admin = User(
            name="Recall Coordinator",
            email="admin@example.edu",
            password_hash=hash_password("password"),
        )
        db.add(admin)
        db.add_all(make_recalls(rng))
        db.commit()

        events = [
            RecallEvent(
                recall_id=number,
                event_type=rng.choice(["notice", "distribution", "follow-up"]),
                note=f"Seeded related recall event {number:03d} using SEED {SEED}.",
            )
            for number in range(1, RELATED_ROWS + 1)
        ]
        db.add_all(events)
        db.commit()

        recall_count = db.scalar(text("SELECT COUNT(*) FROM recall_notices"))
        event_count = db.scalar(text("SELECT COUNT(*) FROM recall_events"))
        user_count = db.scalar(text("SELECT COUNT(*) FROM users"))

    print("HOMEWORK 4 - MYSQL SEED")
    print(f"Database: s3539_rel")
    print(f"SEED: {SEED}")
    print(f"Primary recall rows: {recall_count}")
    print(f"Related event rows: {event_count}")
    print(f"Authentication users: {user_count}")
    print("Demo login: admin@example.edu / password")


if __name__ == "__main__":
    main()
