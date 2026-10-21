#!/usr/bin/env python3
"""Apply the HW7 user migration and seed reader/writer/moderator identities."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, select, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from code.web_application.db import db_session_basede26, engine
from code.web_application.models import User
from code.web_application.security import hash_password

USERS = (
    ("reader3539", "HW7 Reader", "reader3539@example.edu", "reader-pass-3539", "reader"),
    ("writer3539", "HW7 Writer", "writer3539@example.edu", "writer-pass-3539", "writer"),
    (
        "moderator3539",
        "HW7 Moderator",
        "moderator3539@example.edu",
        "moderator-pass-3539",
        "moderator",
    ),
)


def ensure_columns() -> None:
    columns = {item["name"] for item in inspect(engine).get_columns("users")}
    with engine.begin() as connection:
        if "username" not in columns:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN username VARCHAR(80) NULL AFTER id")
            )
            connection.execute(
                text(
                    "UPDATE users SET username=LOWER(SUBSTRING_INDEX(email, '@', 1)) WHERE username IS NULL"
                )
            )
            connection.execute(text("ALTER TABLE users MODIFY username VARCHAR(80) NOT NULL"))
            connection.execute(
                text("ALTER TABLE users ADD UNIQUE KEY uq_users_username (username)")
            )
        if "role" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE users ADD COLUMN role ENUM('reader','writer','moderator') NOT NULL DEFAULT 'reader' AFTER password_hash"
                )
            )


def main() -> None:
    ensure_columns()
    with db_session_basede26() as db:
        for username, name, email, password, role in USERS:
            user = db.scalar(select(User).where(User.username == username))
            if user is None:
                user = User(
                    username=username,
                    name=name,
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                )
                db.add(user)
            else:
                user.name, user.email, user.password_hash, user.role = (
                    name,
                    email,
                    hash_password(password),
                    role,
                )
        db.commit()
    print("Vedant Vartak - DATA 260 HW7 JWT users")
    for username, _, _, password, role in USERS:
        print(f"{role}: {username} / {password}")


if __name__ == "__main__":
    main()
