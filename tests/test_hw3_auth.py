from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from code.web_application.backend import app
from code.web_application.routers.auth import ACTIVE_SESSIONS, reset_sessions


class AuthenticationTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_sessions()
        self.client = TestClient(app, base_url="https://testserver")

    def test_home_login_and_invalid_alert(self) -> None:
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn("Grocery Recall Manager", home.text)
        invalid = self.client.post(
            "/login",
            data={"username": "admin", "password": "incorrect"},
        )
        self.assertEqual(invalid.status_code, 401)
        self.assertIn("Login failed", invalid.text)

    def test_secure_cookie_and_protected_dashboard(self) -> None:
        login = self.client.post(
            "/login",
            data={"username": "admin", "password": "password"},
            follow_redirects=False,
        )
        self.assertEqual(login.status_code, 302)
        cookie = login.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("secure", cookie)
        self.assertIn("samesite=lax", cookie)
        dashboard = self.client.get("/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("Recall Coordinator", dashboard.text)

    def test_logout_revokes_replayed_cookie(self) -> None:
        login = self.client.post(
            "/login",
            data={"username": "admin", "password": "password"},
            follow_redirects=False,
        )
        old_cookie = login.cookies.get("session")
        self.client.get("/logout", follow_redirects=False)
        replay = TestClient(app, base_url="https://testserver")
        response = replay.get(
            "/dashboard",
            headers={"cookie": f"session={old_cookie}"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("login_required", response.headers["location"])

    def test_idle_session_cannot_reach_dashboard(self) -> None:
        self.client.post(
            "/login",
            data={"username": "admin", "password": "password"},
            follow_redirects=False,
        )
        session_id = next(iter(ACTIVE_SESSIONS))
        ACTIVE_SESSIONS[session_id]["last_activity"] = 0.0
        expired = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(expired.status_code, 302)
        self.assertIn("session_expired", expired.headers["location"])


if __name__ == "__main__":
    unittest.main()
