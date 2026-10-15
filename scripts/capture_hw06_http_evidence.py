#!/usr/bin/env python3
"""Capture readable proof from the running HW6 FastAPI endpoints."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8839"


def request(path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data else "GET",
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        return {"status": response.status, "body": json.load(response)}


def main() -> None:
    chat = request(
        "/api/chat",
        {"user_id": "vedant-hw6", "session_id": "demo-3539", "message": "What MongoDB database should I use? Answer briefly."},
    )
    memory = request("/api/memory/vedant-hw6")
    for episode in memory["body"]["episodes"]:
        episode.pop("embedding", None)
    aggregate = request("/api/aggregate/vedant-hw6")
    openapi = request("/openapi.json")
    result = {
        "student": "Vedant Vartak",
        "base_url": BASE_URL,
        "health": request("/health"),
        "POST /api/chat": chat,
        "GET /api/memory/vedant-hw6": memory,
        "GET /api/aggregate/vedant-hw6": aggregate,
        "registered_hw6_paths": sorted(path for path in openapi["body"]["paths"] if path.startswith("/api/chat") or path.startswith("/api/memory") or path.startswith("/api/aggregate") or path.startswith("/api/v1/documents")),
    }
    destination = PROJECT_ROOT / "reports" / "hw06" / "raw" / "http_endpoint_evidence.json"
    destination.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
