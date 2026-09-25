from __future__ import annotations

import unittest
from pathlib import Path

import yaml

from code.web_application import models
from code.web_application.db import db_session_basede26
from code.web_application.security import hash_password, verify_password


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "code/web_application/frontend/src"


class Homework4StructureTests(unittest.TestCase):
    def test_required_database_models_and_connection_name(self) -> None:
        self.assertIsNotNone(db_session_basede26)
        self.assertEqual(models.User.__tablename__, "users")
        self.assertEqual(models.SessionRecord.__tablename__, "sessions")
        self.assertEqual(models.RecallNotice.__tablename__, "recall_notices")
        self.assertEqual(models.RecallEvent.__tablename__, "recall_events")
        self.assertTrue(hasattr(models.User, "password_hash"))

    def test_password_hash_is_salted_and_verifiable(self) -> None:
        first = hash_password("password")
        second = hash_password("password")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("password", first))
        self.assertFalse(verify_password("wrong", first))

    def test_required_react_components_and_routes(self) -> None:
        for name in (
            "Login.jsx",
            "Home.jsx",
            "CreateRecord.jsx",
            "UpdateRecord.jsx",
            "DeleteRecord.jsx",
        ):
            self.assertTrue((FRONTEND / "components" / name).is_file(), name)
        app = (FRONTEND / "App.jsx").read_text(encoding="utf-8")
        for route in ('path="/"', 'path="/create"', 'path="/update/:id"', 'path="/delete/:id"'):
            self.assertIn(route, app)
        self.assertIn("ProtectedRoute", app)

    def test_rag_question_set_covers_six_types(self) -> None:
        path = ROOT / "reports/hw04/questions.yaml"
        questions = yaml.safe_load(path.read_text(encoding="utf-8"))["questions"]
        self.assertEqual(len(questions), 6)
        self.assertEqual(sum(bool(item["should_refuse"]) for item in questions), 2)
        self.assertEqual({item["id"] for item in questions}, {f"q{i}" for i in range(1, 7)})


if __name__ == "__main__":
    unittest.main()
