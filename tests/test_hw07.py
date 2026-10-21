from __future__ import annotations

import csv
import tempfile
import unittest
from code.hw5_tools import InMemoryRecallRepository
from code.hw7.agent import ScriptedActionModel, run_agent
from code.hw7.bike_agent import run_bike_agent
from code.hw7.bike_tools import calculator, csv_sql, policy_retriever
from code.hw7.file_tools import (
    confirm_bash,
    edit_file,
    glob_files,
    is_destructive,
    read_file,
    search_in_files,
    write_file,
)
from code.hw7.injection_security import evaluate_attacks
from code.hw7.jwt_auth import create_access_token, decode_access_token
from code.hw7.reflexion import run_reflexion, verify_task
from code.web_application.models import User
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]


class Homework7Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = InMemoryRecallRepository()

    def test_jwt_round_trip_and_expiry(self) -> None:
        user = User(
            id=7,
            username="reader3539",
            name="Reader",
            email="reader@example.edu",
            password_hash="x",
            role="reader",
        )
        token = create_access_token(user, now=100)
        payload = decode_access_token(token, now=101)
        self.assertEqual(payload["username"], "reader3539")
        self.assertEqual(payload["role"], "reader")
        with self.assertRaises(HTTPException) as error:
            decode_access_token(token, now=100 + 1801)
        self.assertEqual(error.exception.status_code, 401)

    def test_agent_multistep_repair_and_missing_id(self) -> None:
        model = ScriptedActionModel(
            [
                "not-json",
                {"tool": "search", "inputs": {"query": "shrimp", "limit": 1}},
                {"tool": "detail", "inputs": {"recall_id": 1}},
                {"final": "The first shrimp result is recall 1."},
            ]
        )
        result = run_agent(
            "Search shrimp then detail the first result",
            model=model,
            repository=self.repo,
            log_path=None,
        )
        self.assertEqual(result.stop_reason, "success")
        self.assertEqual(result.repairs, 1)
        self.assertEqual(result.tool_calls, 2)

        missing = run_agent(
            "Get impossible recall 999",
            model=ScriptedActionModel(
                [
                    {"tool": "detail", "inputs": {"recall_id": 999}},
                    {"final": "Recall 999 was not found; no details are available."},
                ]
            ),
            repository=self.repo,
            log_path=None,
        )
        self.assertFalse(missing.invocations[0].observation["ok"])
        self.assertEqual(missing.stop_reason, "success")

    def test_bounded_reflexion_records_failed_then_retried_evidence(self) -> None:
        attempts = [
            ScriptedActionModel(
                [
                    {"tool": "search", "inputs": {"query": "shrimp", "limit": 1}},
                    {"final": "I found shrimp."},
                ]
            ),
            ScriptedActionModel(
                [
                    {"tool": "search", "inputs": {"query": "shrimp", "limit": 1}},
                    {"tool": "detail", "inputs": {"recall_id": 1}},
                    {"final": "Recall 1 is Frozen Shrimp Lot 00001."},
                ]
            ),
        ]
        result = run_reflexion(
            "Search shrimp and detail the first result",
            model_factory=lambda attempt: attempts[attempt],
            verifier=verify_task(["search", "detail"]),
            repository=self.repo,
        )
        self.assertEqual(result.stop_reason, "success")
        self.assertEqual(result.retries, 1)
        self.assertIn("expected at least 2", result.reflections[0].failure_evidence)
        self.assertFalse(result.reflections[0].trusted)

    def _write_trip_csv(self, path: Path, target_rides: int, target_duration: float) -> None:
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=["week", "duration_minutes", "user_scope", "notes"]
            )
            writer.writeheader()
            for index in range(500):
                writer.writerow(
                    {
                        "week": index % 4 + 1,
                        "duration_minutes": target_duration if index < target_rides else 8,
                        "user_scope": "target" if index < target_rides else "other",
                        "notes": "normal trip",
                    }
                )

    def test_mrkl_tools_and_two_500_row_acceptance_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            policy = root / "pricing.html"
            policy.write_text(
                "<p>A 30-Day Membership costs $25. A single ride has a $1 unlock fee and costs $0.15 per minute.</p>",
                encoding="utf-8",
            )
            url = policy.as_uri()
            many, few = root / "many.csv", root / "few.csv"
            self._write_trip_csv(many, 80, 20)
            self._write_trip_csv(few, 4, 8)

            query = csv_sql({"sql": "SELECT COUNT(*) AS n FROM trips"}, many)
            self.assertEqual(int(query["data"]["rows"][0]["n"]), 500)
            self.assertTrue(
                policy_retriever({"url": url, "query": "membership price", "k": 2})["success"]
            )
            self.assertEqual(
                calculator({"expression": "(95+5)/4", "units": "USD"})["data"]["value"], 25
            )

            member = run_bike_agent(many, url, scenario="membership_wins")
            pay = run_bike_agent(few, url, scenario="pay_wins")
            self.assertEqual(member.decision, "Buy Monthly Membership")
            self.assertEqual(pay.decision, "Pay Per Ride/Minute")
            self.assertGreaterEqual(member.step_count, 3)

    def test_prompt_injection_and_read_only_sql_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trips.csv"
            path.write_text(
                "week,duration_minutes,user_scope,notes\n1,5,target,secret\n", encoding="utf-8"
            )
            result = csv_sql({"sql": "DELETE FROM trips"}, path)
            self.assertFalse(result["success"])
            outcomes = evaluate_attacks(str(path))
            self.assertEqual(len(outcomes), 3)
            self.assertIn("PASS", outcomes[1]["after_prompt_and_tool_defense"])

    def test_file_tool_integration_and_10_command_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            for name, content in {
                "alpha.py": "VALUE = 1\n",
                "beta.py": "DEBUG = True\nprint('debug')\n",
                "gamma.py": "VALUE = 3\n",
            }.items():
                write_file(name, content, sandbox=temp)
            self.assertEqual(glob_files("*.py", sandbox=temp), ["alpha.py", "beta.py", "gamma.py"])
            hits = search_in_files("DEBUG", sandbox=temp, file_pattern="*.py")
            self.assertEqual(hits[0]["path"], "beta.py")
            self.assertIn("DEBUG", read_file("beta.py", sandbox=temp, max_lines=1))
            self.assertIn(
                "+DEBUG = False",
                edit_file("beta.py", "DEBUG = True", "DEBUG = False", sandbox=temp)["diff"],
            )

            allowed = ["pwd", "ls", "find . -name '*.py'", "rg DEBUG", "python -m compileall ."]
            blocked = [
                "rm -rf .",
                "sudo ls",
                "chmod 777 alpha.py",
                "dd if=/dev/zero of=/dev/disk1",
                "mkfs /dev/disk1",
            ]
            self.assertTrue(all(confirm_bash(command)["allowed"] for command in allowed))
            self.assertTrue(all(not confirm_bash(command)["allowed"] for command in blocked))
            self.assertTrue(all(is_destructive(command) for command in blocked))

    def test_required_hw7_artifact_paths(self) -> None:
        for relative in (
            "code/hw7/agent.py",
            "code/hw7/reflexion.py",
            "code/hw7/bike_tools.py",
            "code/hw7/injection_security.py",
            "code/hw7/file_tools.py",
            "sql/hw07_migration.sql",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
