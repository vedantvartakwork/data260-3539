"""Print the secure session-cookie evidence required by Homework 3."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from code.web_application.backend import app
from code.web_application.routers.auth import reset_sessions


reset_sessions()
client = TestClient(app, base_url="https://testserver")
response = client.post(
    "/login",
    data={"username": "admin", "password": "password"},
    follow_redirects=False,
)
cookie = response.headers["set-cookie"]
lower_cookie = cookie.lower()

print("HOMEWORK 3 - SECURE SESSION COOKIE")
print(f"POST /login status: {response.status_code}")
print(f"Redirect location: {response.headers['location']}")
print("Set-Cookie response header:")
print(cookie)
print()
print(f"HttpOnly: {'PASS' if 'httponly' in lower_cookie else 'FAIL'}")
print(f"Secure: {'PASS' if 'secure' in lower_cookie else 'FAIL'}")
print(f"SameSite=Lax: {'PASS' if 'samesite=lax' in lower_cookie else 'FAIL'}")
