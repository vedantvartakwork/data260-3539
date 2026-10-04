"""Shared, validated Homework 5 domain tools and safe execution entry point."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from code.web_application.db import db_session_basede26
from code.web_application.models import Manufacturer, RecallNotice


def envelope(*, data: Any = None, error: str | None = None) -> dict[str, Any]:
    return {"ok": error is None, "data": data if error is None else None, "error": error}


class SearchInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query: str = Field(min_length=2, max_length=80)
    limit: int = Field(default=5, ge=1, le=25)


class DetailInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    recall_id: int = Field(gt=0)


class AggregateInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    group_by: str = Field(pattern=r"^(category|manufacturer)$")
    min_units: int = Field(default=0, ge=0, le=100_000_000)


class RecallRepository(Protocol):
    def search(self, query: str, limit: int) -> list[dict[str, Any]]: ...
    def detail(self, recall_id: int) -> dict[str, Any] | None: ...
    def aggregate(self, group_by: str, min_units: int) -> list[dict[str, Any]]: ...


class SQLAlchemyRecallRepository:
    """Read-only repository backed by the cumulative MySQL database."""

    def __init__(self, session_factory: Callable[[], Session] = db_session_basede26):
        self.session_factory = session_factory

    def search(self, query: str, limit: int) -> list[dict[str, Any]]:
        pattern = f"%{query.strip()}%"
        with self.session_factory() as db:
            rows = list(
                db.scalars(
                    select(RecallNotice)
                    .where(
                        or_(
                            RecallNotice.product_name.like(pattern),
                            RecallNotice.brand_name.like(pattern),
                            RecallNotice.recall_code.like(pattern),
                        )
                    )
                    .order_by(RecallNotice.id)
                    .limit(limit)
                )
            )
            return [
                {
                    "id": row.id,
                    "recall_code": row.recall_code,
                    "product_name": row.product_name,
                    "brand_name": row.brand_name,
                    "category": row.category,
                    "units_affected": row.units_affected,
                }
                for row in rows
            ]

    def detail(self, recall_id: int) -> dict[str, Any] | None:
        with self.session_factory() as db:
            row = db.scalar(
                select(RecallNotice)
                .options(joinedload(RecallNotice.manufacturer))
                .where(RecallNotice.id == recall_id)
            )
            if row is None:
                return None
            return {
                "id": row.id,
                "recall_code": row.recall_code,
                "product_name": row.product_name,
                "brand_name": row.brand_name,
                "category": row.category,
                "units_affected": row.units_affected,
                "recall_details": row.recall_details,
                "manufacturer": {
                    "id": row.manufacturer.id,
                    "name": row.manufacturer.name,
                    "contact_name": row.manufacturer.contact_name,
                },
            }

    def aggregate(self, group_by: str, min_units: int) -> list[dict[str, Any]]:
        with self.session_factory() as db:
            if group_by == "category":
                label = RecallNotice.category
                statement = (
                    select(
                        label.label("label"),
                        func.count(RecallNotice.id).label("recall_count"),
                        func.sum(RecallNotice.units_affected).label("total_units"),
                    )
                    .where(RecallNotice.units_affected >= min_units)
                    .group_by(label)
                    .order_by(label)
                )
            else:
                label = Manufacturer.name
                statement = (
                    select(
                        label.label("label"),
                        func.count(RecallNotice.id).label("recall_count"),
                        func.sum(RecallNotice.units_affected).label("total_units"),
                    )
                    .join(RecallNotice, RecallNotice.manufacturer_id == Manufacturer.id)
                    .where(RecallNotice.units_affected >= min_units)
                    .group_by(label)
                    .order_by(label)
                )
            return [
                {
                    "label": row.label,
                    "recall_count": int(row.recall_count),
                    "total_units": int(row.total_units or 0),
                }
                for row in db.execute(statement)
            ]


class InMemoryRecallRepository:
    """Deterministic dependency-injected fixture for offline tests."""

    def __init__(self, rows: list[dict[str, Any]] | None = None):
        self.rows = rows or [
            {
                "id": 1,
                "recall_code": "REC-3539-00001",
                "product_name": "Frozen Shrimp Lot 00001",
                "brand_name": "Campus Pantry",
                "category": "Meat and Seafood",
                "units_affected": 1200,
                "recall_details": "Selected packages may contain an undeclared allergen.",
                "manufacturer": {"id": 1, "name": "Campus Pantry", "contact_name": "A. Safety"},
            },
            {
                "id": 2,
                "recall_code": "REC-3539-00002",
                "product_name": "Greek Yogurt Lot 00002",
                "brand_name": "Golden Dairy",
                "category": "Dairy and Refrigerated",
                "units_affected": 800,
                "recall_details": "The printed expiration date may be incorrect.",
                "manufacturer": {"id": 2, "name": "Golden Dairy", "contact_name": "B. Safety"},
            },
        ]

    def search(self, query: str, limit: int) -> list[dict[str, Any]]:
        needle = query.casefold()
        matches = [
            row
            for row in self.rows
            if any(
                needle in str(row[field]).casefold()
                for field in ("product_name", "brand_name", "recall_code")
            )
        ]
        fields = ("id", "recall_code", "product_name", "brand_name", "category", "units_affected")
        return [{field: row[field] for field in fields} for row in matches[:limit]]

    def detail(self, recall_id: int) -> dict[str, Any] | None:
        return next((dict(row) for row in self.rows if row["id"] == recall_id), None)

    def aggregate(self, group_by: str, min_units: int) -> list[dict[str, Any]]:
        labels = []
        for row in self.rows:
            if row["units_affected"] < min_units:
                continue
            labels.append(row["category"] if group_by == "category" else row["manufacturer"]["name"])
        counts = Counter(labels)
        return [
            {
                "label": label,
                "recall_count": count,
                "total_units": sum(
                    row["units_affected"]
                    for row in self.rows
                    if row["units_affected"] >= min_units
                    and (row["category"] if group_by == "category" else row["manufacturer"]["name"]) == label
                ),
            }
            for label, count in sorted(counts.items())
        ]


def search_tool(inputs: dict[str, Any], repository: RecallRepository) -> dict[str, Any]:
    parsed = SearchInputs.model_validate(inputs)
    rows = repository.search(parsed.query, parsed.limit)
    return envelope(data={"matches": rows, "count": len(rows)})


def detail_tool(inputs: dict[str, Any], repository: RecallRepository) -> dict[str, Any]:
    parsed = DetailInputs.model_validate(inputs)
    row = repository.detail(parsed.recall_id)
    if row is None:
        return envelope(error=f"Recall {parsed.recall_id} was not found")
    return envelope(data=row)


def aggregate_tool(inputs: dict[str, Any], repository: RecallRepository) -> dict[str, Any]:
    parsed = AggregateInputs.model_validate(inputs)
    rows = repository.aggregate(parsed.group_by, parsed.min_units)
    return envelope(data={"group_by": parsed.group_by, "groups": rows})


TOOL_HANDLERS = {
    "search": search_tool,
    "detail": detail_tool,
    "aggregate": aggregate_tool,
}


def call_domain_tool(
    name: str,
    inputs: dict[str, Any],
    repository: RecallRepository | None = None,
) -> dict[str, Any]:
    """Run a domain tool and always return the shared response envelope."""
    if name not in TOOL_HANDLERS:
        return envelope(error=f"Unknown tool: {name}")
    try:
        return TOOL_HANDLERS[name](inputs, repository or SQLAlchemyRecallRepository())
    except ValidationError as exc:
        messages = "; ".join(
            f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in exc.errors()
        )
        return envelope(error=f"Invalid {name} input: {messages}")
    except Exception as exc:  # MCP/agent boundary must not crash callers.
        return envelope(error=f"{name} failed: {exc}")


def execute_tool(
    name: str,
    inputs: dict[str, Any],
    repository: RecallRepository | None = None,
) -> str:
    """Single safe JSON-string entry point used by the Homework 5 agent.

    Safety rule: the agent may retrieve at most ten recall summaries per search.
    This limits bulk extraction while leaving normal interactive lookups available.
    """
    if name == "search" and isinstance(inputs, dict):
        limit = inputs.get("limit", 5)
        if isinstance(limit, int) and limit > 10:
            return json.dumps(
                envelope(error="Safety rule blocked search: limit cannot exceed 10 records")
            )
    return json.dumps(call_domain_tool(name, inputs, repository), sort_keys=True)
