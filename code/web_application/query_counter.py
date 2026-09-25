"""Request-local SQL statement counting for the N+1 experiment."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import event

from code.web_application.db import engine


_ACTIVE_COUNTER: ContextVar[list[int] | None] = ContextVar(
    "hw4_sql_counter",
    default=None,
)


@event.listens_for(engine, "before_cursor_execute")
def _count_statement(*_args: object, **_kwargs: object) -> None:
    counter = _ACTIVE_COUNTER.get()
    if counter is not None:
        counter[0] += 1


@contextmanager
def count_sql_queries() -> Generator[list[int], None, None]:
    counter = [0]
    token = _ACTIVE_COUNTER.set(counter)
    try:
        yield counter
    finally:
        _ACTIVE_COUNTER.reset(token)
