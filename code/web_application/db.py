"""Database configuration for the Homework 4 MySQL application."""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://data260:data260@127.0.0.1:3307/s3539_rel",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# The assignment requires this exact connection-variable name.
db_session_basede26 = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = db_session_basede26()
    try:
        yield db
    finally:
        db.close()
