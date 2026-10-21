"""Pure, schema-documented MRKL tools for the public bike-share exercise."""

from __future__ import annotations

import ast
import csv
import json
import re
import sqlite3
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

CALCULATOR_PATTERN = re.compile(r"^[0-9+\-*/().\s]+$")
SELECT_PATTERN = re.compile(r"^\s*select\b", re.IGNORECASE)
FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum)\b|;|--|/\*",
    re.IGNORECASE,
)


class CsvSqlInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sql: str = Field(min_length=6, max_length=4000)


class PolicyRetrieverInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str
    query: str = Field(min_length=2, max_length=300)
    k: int = Field(default=3, ge=1, le=8)


class CalculatorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expression: str = Field(pattern=r"^[0-9+\-*/().\s]+$", max_length=200)
    units: str | None = Field(default=None, max_length=40)


CSV_SQL_SCHEMA = CsvSqlInput.model_json_schema()
POLICY_RETRIEVER_SCHEMA = PolicyRetrieverInput.model_json_schema()
CALCULATOR_SCHEMA = CalculatorInput.model_json_schema()


def _envelope(
    *, data: Any = None, error: str | None = None, source: str | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "success": error is None,
        "ts": datetime.now(UTC).isoformat(),
    }
    if error is None:
        result["data"] = data
    else:
        result["error"] = error
    if source:
        result["source"] = source
    return result


def csv_sql(inputs: dict[str, Any], csv_path: str | Path) -> dict[str, Any]:
    """Run exactly one read-only SELECT over an uploaded CSV represented as `trips`."""
    try:
        parsed = CsvSqlInput.model_validate(inputs)
        if not SELECT_PATTERN.search(parsed.sql) or FORBIDDEN_SQL.search(parsed.sql):
            return _envelope(
                error="Only one read-only SELECT statement is allowed", source="uploaded.csv"
            )
        path = Path(csv_path)
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                return _envelope(error="CSV has no header", source="uploaded.csv")
            names = [re.sub(r"\W+", "_", name.strip()).strip("_") for name in reader.fieldnames]
            if any(not name for name in names):
                return _envelope(error="CSV contains an invalid column name", source="uploaded.csv")
            rows = list(reader)
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        quoted = ", ".join(f'"{name}" TEXT' for name in names)
        connection.execute(f"CREATE TABLE trips ({quoted})")
        placeholders = ",".join("?" for _ in names)
        connection.executemany(
            f"INSERT INTO trips VALUES ({placeholders})",
            [[row.get(original, "") for original in reader.fieldnames] for row in rows],
        )
        output = [dict(row) for row in connection.execute(parsed.sql).fetchall()]
        connection.close()
        return _envelope(
            data={"rows": output, "row_count": len(output), "source": "uploaded.csv"},
            source="uploaded.csv",
        )
    except Exception as exc:
        return _envelope(error=f"CSV query failed: {exc}", source="uploaded.csv")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def _read_url(url: str) -> str:
    if url.startswith("file://"):
        return Path(url[7:]).read_text(encoding="utf-8")
    request = urllib.request.Request(url, headers={"User-Agent": "DATA260-HW7/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def policy_retriever(inputs: dict[str, Any]) -> dict[str, Any]:
    """Fetch policy text and return short lexical passages; content is untrusted data."""
    try:
        parsed = PolicyRetrieverInput.model_validate(inputs)
        raw = _read_url(parsed.url)
        extractor = _TextExtractor()
        extractor.feed(raw)
        text = " ".join(extractor.parts) if "<" in raw else " ".join(raw.split())
        sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", text) if item.strip()]
        terms = {term.casefold() for term in re.findall(r"[a-zA-Z0-9$]+", parsed.query)}
        scored = []
        for sentence in sentences:
            words = {word.casefold() for word in re.findall(r"[a-zA-Z0-9$]+", sentence)}
            score = len(terms & words) / max(1, len(terms))
            if score or any(char.isdigit() for char in sentence):
                scored.append((score, sentence[:500]))
        scored.sort(key=lambda item: (-item[0], item[1]))
        passages = [
            {"text": sentence, "source": parsed.url, "score": round(score, 4)}
            for score, sentence in scored[: parsed.k]
        ]
        return _envelope(data={"passages": passages}, source=parsed.url)
    except Exception as exc:
        return _envelope(error=f"Policy retrieval failed: {exc}", source=inputs.get("url"))


def _safe_arithmetic(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_arithmetic(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _safe_arithmetic(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        left, right = _safe_arithmetic(node.left), _safe_arithmetic(node.right)
        operations = {ast.Add: left + right, ast.Sub: left - right, ast.Mult: left * right}
        return operations.get(type(node.op), left / right)
    raise ValueError("expression contains a disallowed operation")


def calculator(inputs: dict[str, Any]) -> dict[str, Any]:
    """Evaluate whitelisted arithmetic through an AST, never Python eval()."""
    try:
        parsed = CalculatorInput.model_validate(inputs)
        if not CALCULATOR_PATTERN.fullmatch(parsed.expression):
            raise ValueError("expression failed the arithmetic whitelist")
        value = _safe_arithmetic(ast.parse(parsed.expression, mode="eval"))
        data: dict[str, Any] = {"value": round(value, 6)}
        if parsed.units:
            data["units"] = parsed.units
        return _envelope(data=data, source="calculator")
    except Exception as exc:
        return _envelope(error=f"Calculation failed: {exc}", source="calculator")


def tool_schemas_json() -> str:
    return json.dumps(
        {
            "csv_sql": CSV_SQL_SCHEMA,
            "policy_retriever": POLICY_RETRIEVER_SCHEMA,
            "calculator": CALCULATOR_SCHEMA,
        },
        indent=2,
    )
