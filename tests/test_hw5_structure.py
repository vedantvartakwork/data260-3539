from __future__ import annotations

import json
import time
import unittest
from pathlib import Path

from code.hw5_agent import MockModel, run_agent
from code.hw5_retry import RetryPolicy, call_with_retry
from code.hw5_tools import InMemoryRecallRepository, execute_tool
from code.web_application import models


ROOT = Path(__file__).resolve().parents[1]


class Homework5StructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryRecallRepository()

    def result(self, name: str, inputs: dict) -> dict:
        return json.loads(execute_tool(name, inputs, self.repository))

    def test_related_database_models_and_constraints(self) -> None:
        self.assertEqual(models.Manufacturer.__tablename__, "manufacturers")
        self.assertTrue(models.Manufacturer.contact_email.property.columns[0].unique)
        self.assertTrue(models.RecallNotice.recall_code.property.columns[0].unique)
        foreign_key = next(
            iter(models.RecallNotice.manufacturer_id.property.columns[0].foreign_keys)
        )
        self.assertEqual(foreign_key.ondelete, "RESTRICT")

    def test_exact_three_domain_tools_and_envelope(self) -> None:
        from code.hw5_tools import TOOL_HANDLERS

        self.assertEqual(set(TOOL_HANDLERS), {"search", "detail", "aggregate"})
        for name, inputs in (
            ("search", {"query": "shrimp", "limit": 2}),
            ("detail", {"recall_id": 1}),
            ("aggregate", {"group_by": "category", "min_units": 0}),
        ):
            self.assertEqual(set(self.result(name, inputs)), {"ok", "data", "error"})

    def test_execute_tool_returns_json_and_blocks_bulk_search(self) -> None:
        allowed = self.result("search", {"query": "rec", "limit": 10})
        blocked = self.result("search", {"query": "rec", "limit": 11})
        self.assertTrue(allowed["ok"])
        self.assertFalse(blocked["ok"])
        self.assertIn("Safety rule blocked", blocked["error"])

    def test_mock_agent_stops_at_ceiling(self) -> None:
        model = MockModel(
            [{"tool": "search", "inputs": {"query": "rec", "limit": 2}}],
            repeat_last=True,
        )
        result = run_agent(
            "Keep going",
            model=model,
            repository=self.repository,
            max_steps=2,
            log_path=None,
        )
        self.assertEqual(result.stop_reason, "max_steps")
        self.assertEqual(result.step_count, 2)

    def test_required_hw5_files_exist(self) -> None:
        for relative in (
            "mcp_servers/meals_server.py",
            "mcp_servers/domain_server.py",
            "scripts/test_hw05_tools.py",
            "scripts/run_hw05_fault_experiment.py",
            "sql/hw05_migration.sql",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_home_exposes_all_records_through_pagination(self) -> None:
        router = (ROOT / "code/web_application/routers/recalls.py").read_text()
        home = (ROOT / "code/web_application/frontend/src/components/Home.jsx").read_text()
        redux = (ROOT / "code/web_application/frontend/src/features/recalls/recallsSlice.js").read_text()
        self.assertIn("offset((page - 1) * page_size)", router)
        self.assertIn("total = db.scalar(count_statement)", router)
        self.assertIn("Showing {firstShown}-{lastShown} of {total}", home)
        self.assertIn("Page {page} of {totalPages}", home)
        self.assertIn("state.total = action.payload.total", redux)

    def test_retry_interrupts_hanging_operation_at_deadline(self) -> None:
        started = time.perf_counter()
        result = call_with_retry(
            lambda: time.sleep(0.20),
            RetryPolicy(max_attempts=1, timeout_seconds=0.03),
        )
        elapsed = time.perf_counter() - started
        self.assertFalse(result.ok)
        self.assertIn("timed out", result.error or "")
        self.assertLess(elapsed, 0.12)


if __name__ == "__main__":
    unittest.main()
