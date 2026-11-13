"""Structured JSON spans and request records for the HW10 dashboard."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


class TraceStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.spans_path = directory / "spans.jsonl"
        self.requests_path = directory / "requests.jsonl"

    def reset(self) -> None:
        self.spans_path.write_text("", encoding="utf-8")
        self.requests_path.write_text("", encoding="utf-8")

    @staticmethod
    def _append(path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    @contextmanager
    def span(
        self,
        trace_id: str,
        stage: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        started_at = utc_now()
        started = time.perf_counter()
        state: dict[str, Any] = {"status": "ok", "error": None}
        try:
            yield state
        except Exception as exc:
            state["status"] = "error"
            state["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            payload = {
                "trace_id": trace_id,
                "stage": stage,
                "start": started_at,
                "end": utc_now(),
                "duration_ms": duration_ms,
                "status": state.get("status", "ok"),
                "error": state.get("error"),
            }
            if metadata:
                payload.update(metadata)
            for key, value in state.items():
                if key not in {"status", "error"}:
                    payload[key] = value
            self._append(self.spans_path, payload)

    def request(self, payload: dict[str, Any]) -> None:
        self._append(self.requests_path, payload)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
