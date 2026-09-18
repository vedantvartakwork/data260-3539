"""Authentication routes for the grocery recall application."""

from __future__ import annotations

import os
import time
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND

router = APIRouter()
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=TEMPLATE_DIR)

VALID_USERNAME = os.getenv("DEMO_USERNAME", "admin")
VALID_PASSWORD = os.getenv("DEMO_PASSWORD", "password")
IDLE_TIMEOUT_SECONDS = int(os.getenv("SESSION_IDLE_TIMEOUT_SECONDS", "300"))

# Starlette signs the browser cookie. This small server-side registry additionally
# lets logout revoke a session immediately, even if an old cookie is replayed.
ACTIVE_SESSIONS: dict[str, dict[str, object]] = {}


def reset_sessions() -> None:
    """Clear active sessions for deterministic tests and local demonstrations."""
    ACTIVE_SESSIONS.clear()


def _active_user(request: Request) -> tuple[dict[str, str] | None, str | None]:
    """Return the active user, enforcing revocation and an idle timeout."""
    session_id = request.session.get("session_id")
    user = request.session.get("user")
    record = ACTIVE_SESSIONS.get(session_id) if isinstance(session_id, str) else None

    if not isinstance(user, dict) or record is None:
        request.session.clear()
        return None, "login_required"

    now = time.time()
    last_activity = float(record.get("last_activity", 0.0))
    if now - last_activity > IDLE_TIMEOUT_SECONDS:
        ACTIVE_SESSIONS.pop(session_id, None)
        request.session.clear()
        return None, "session_expired"

    record["last_activity"] = now
    request.session["last_activity"] = now
    return user, None


@router.get("/")
def home(request: Request, logged_out: bool = False):
    """Show the domain home page with navigation based on login state."""
    user, _ = _active_user(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"user": user, "logged_out": logged_out},
    )


@router.get("/login")
def login_page(request: Request, reason: str | None = None):
    """Show the login form and any session-status alert."""
    user, _ = _active_user(request)
    if user:
        return RedirectResponse("/dashboard", status_code=HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None, "reason": reason},
    )


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Validate credentials, create a revocable session, and redirect."""
    if username != VALID_USERNAME or password != VALID_PASSWORD:
        request.session.clear()
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Invalid username or password.", "reason": None},
            status_code=401,
        )

    request.session.clear()
    session_id = uuid4().hex
    user = {"username": username, "display_name": "Recall Coordinator"}
    now = time.time()
    ACTIVE_SESSIONS[session_id] = {"user": user, "last_activity": now}
    request.session.update({"session_id": session_id, "user": user, "last_activity": now})
    return RedirectResponse("/dashboard", status_code=HTTP_302_FOUND)


@router.get("/dashboard")
def dashboard(request: Request):
    """Show the protected dashboard only while the session remains active."""
    user, reason = _active_user(request)
    if not user:
        return RedirectResponse(f"/login?reason={reason}", status_code=HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"user": user, "idle_timeout": IDLE_TIMEOUT_SECONDS},
    )


@router.get("/logout")
def logout(request: Request):
    """Revoke the server-side session, clear its cookie, and return home."""
    session_id = request.session.get("session_id")
    if isinstance(session_id, str):
        ACTIVE_SESSIONS.pop(session_id, None)
    request.session.clear()
    return RedirectResponse("/?logged_out=true", status_code=HTTP_302_FOUND)
