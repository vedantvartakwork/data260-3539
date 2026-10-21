"""Homework 7 bike-share upload UI and execution endpoint."""

from __future__ import annotations

import tempfile
from code.hw7.bike_agent import run_bike_agent
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["hw7-bike-agent"])
EVIDENCE_DIR = Path(__file__).resolve().parents[2] / "reports" / "hw07" / "evidence_html"


@router.get("/hw7", response_class=HTMLResponse, include_in_schema=False)
def bike_ui() -> str:
    return (Path(__file__).parent / "static" / "bike_agent.html").read_text(encoding="utf-8")


@router.get("/hw7/evidence/{page_name}", response_class=HTMLResponse, include_in_schema=False)
def hw7_evidence_page(page_name: str) -> str:
    """Serve generated local evidence pages without permitting path traversal."""
    allowed = {
        "agent",
        "auth",
        "bike_membership",
        "bike_pay",
        "files",
        "lint",
        "reflexion",
        "security",
    }
    if page_name not in allowed:
        return "<h1>Unknown evidence page</h1>"
    return (EVIDENCE_DIR / f"{page_name}.html").read_text(encoding="utf-8")


@router.post("/api/hw7/bikeshare/run")
async def run_bikeshare(
    csv_file: UploadFile = File(...),
    pricing_url: str = Form(...),
) -> dict:
    suffix = Path(csv_file.filename or "uploaded.csv").suffix or ".csv"
    with tempfile.TemporaryDirectory(prefix="data260-hw7-") as temp:
        target = Path(temp) / f"uploaded{suffix}"
        target.write_bytes(await csv_file.read())
        return run_bike_agent(target, pricing_url).as_dict()
