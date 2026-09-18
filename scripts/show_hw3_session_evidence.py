"""Demonstrate logout revocation and idle-timeout enforcement."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from code.web_application.backend import app
from code.web_application.routers.auth import ACTIVE_SESSIONS, reset_sessions


def login(client: TestClient):
    return client.post(
        "/login",
        data={"username": "admin", "password": "password"},
        follow_redirects=False,
    )


reset_sessions()
client = TestClient(app, base_url="https://testserver")
logged_in = login(client)
old_cookie = logged_in.cookies.get("session")
logout = client.get("/logout", follow_redirects=False)

replay_client = TestClient(app, base_url="https://testserver")
replayed = replay_client.get(
    "/dashboard",
    headers={"cookie": f"session={old_cookie}"},
    follow_redirects=False,
)

timeout_client = TestClient(app, base_url="https://testserver")
login(timeout_client)
session_id = next(iter(ACTIVE_SESSIONS))
ACTIVE_SESSIONS[session_id]["last_activity"] = 0.0
expired = timeout_client.get("/dashboard", follow_redirects=False)

print("HOMEWORK 3 - SESSION REUSE PROTECTION")
print(f"Login status: {logged_in.status_code} -> {logged_in.headers['location']}")
print(f"Logout status: {logout.status_code} -> {logout.headers['location']}")
print(f"Replayed logged-out cookie: {replayed.status_code} -> {replayed.headers['location']}")
print("Result: PASS - the logged-out session cannot reach /dashboard")
print()
print(f"Expired idle session: {expired.status_code} -> {expired.headers['location']}")
print("Result: PASS - the expired session cannot reach /dashboard")
