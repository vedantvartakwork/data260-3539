from __future__ import annotations

import unittest
from code.hw8.config import settings
from code.hw8.failures import (
    consumer_restart_experiment,
    duplicate_delivery_experiment,
    ordering_experiment,
    poison_message_experiment,
    run_all_failure_experiments,
    valid_recall,
)
from code.hw8.in_memory import InMemoryBroker
from code.hw8.pipeline import process_stage
from code.hw8.service import RecallService


def request(operation: str, data: dict, correlation_id: str = "cid-1") -> dict:
    return {
        "correlation_id": correlation_id,
        "reply_to": settings.entity_responses,
        "operation": operation,
        "data": data,
    }


class HW8Tests(unittest.TestCase):
    def test_personal_configuration(self) -> None:
        self.assertEqual(
            (settings.port_base, settings.verify_seed, settings.domain_id), (8839, 263539, 3)
        )

    def test_exact_entity_topics(self) -> None:
        self.assertEqual(settings.entity_requests, "s3539_entity_requests")
        self.assertEqual(settings.entity_responses, "s3539_entity_responses")

    def test_exact_pipeline_topics(self) -> None:
        self.assertEqual(
            [settings.inbox, settings.tasks, settings.drafts, settings.final],
            ["s3539_inbox", "s3539_tasks", "s3539_drafts", "s3539_final"],
        )

    def test_create_and_get_round_trip(self) -> None:
        service = RecallService()
        created = service.process(request("CREATE_RECALL", valid_recall(), "create-1"))
        fetched = service.process(
            request("GET_RECALL", {"entity_id": created["entity_id"]}, "get-1")
        )
        self.assertTrue(created["success"])
        self.assertEqual(fetched["entity"]["recall_code"], "REC-3539-80001")

    def test_correlation_id_preserved_on_success(self) -> None:
        result = RecallService().process(request("CREATE_RECALL", valid_recall(), "preserve-me"))
        self.assertEqual(result["correlation_id"], "preserve-me")

    def test_missing_field_rejected(self) -> None:
        data = valid_recall()
        del data["product_name"]
        result = RecallService().process(request("CREATE_RECALL", data))
        self.assertEqual(result["error"], "product_name is required")

    def test_invalid_email_rejected(self) -> None:
        data = valid_recall()
        data["submitter_email"] = "not-an-email"
        self.assertIn(
            "valid email", RecallService().process(request("CREATE_RECALL", data))["error"]
        )

    def test_invalid_units_rejected(self) -> None:
        data = valid_recall()
        data["units_affected"] = 0
        self.assertIn(
            "positive integer", RecallService().process(request("CREATE_RECALL", data))["error"]
        )

    def test_get_unknown_entity_clean_error(self) -> None:
        result = RecallService().process(request("GET_RECALL", {"entity_id": "missing"}))
        self.assertEqual(result["error"], "Entity not found")

    def test_unknown_operation_clean_error(self) -> None:
        result = RecallService().process(request("DELETE_RECALL", {}))
        self.assertEqual(result["error"], "Unknown operation")

    def test_duplicate_delivery_idempotent(self) -> None:
        result = duplicate_delivery_experiment()
        self.assertTrue(result["passed"])
        self.assertEqual(result["entity_count"], 1)
        self.assertTrue(result["replay"]["duplicate"])

    def test_pipeline_preserves_correlation_and_journey(self) -> None:
        message = {"correlation_id": "pipeline-1", "question": "What should I do?", "journey": []}
        for role in ("planner", "writer", "reviewer"):
            message = process_stage(role, message)
        self.assertEqual(message["correlation_id"], "pipeline-1")
        self.assertEqual(message["journey"], ["planner", "writer", "reviewer"])
        self.assertEqual(message["status"], "approved")

    def test_pipeline_rejects_poison_message(self) -> None:
        with self.assertRaisesRegex(ValueError, "question is required"):
            process_stage("planner", {"correlation_id": "bad", "question": ""})

    def test_consumer_restart_commits_after_success(self) -> None:
        self.assertTrue(consumer_restart_experiment()["passed"])

    def test_poison_message_dead_letter_and_progress(self) -> None:
        result = poison_message_experiment()
        self.assertTrue(result["passed"])
        self.assertEqual(result["dead_letter"]["topic"], "s3539_dead_letter")

    def test_verify_seed_ordering_experiment(self) -> None:
        result = ordering_experiment()
        self.assertTrue(result["passed"])
        self.assertEqual(result["verify_seed"], 263539)
        self.assertEqual(len(result["input_order"]), 20)

    def test_all_failure_experiments_pass(self) -> None:
        self.assertTrue(run_all_failure_experiments()["passed"])

    def test_in_memory_key_keeps_partition(self) -> None:
        broker = InMemoryBroker({settings.tasks: 2})
        records = [broker.send(settings.tasks, {"n": n}, key="recall-3539") for n in range(20)]
        self.assertEqual(len({record.partition for record in records}), 1)
        self.assertEqual([record.offset for record in records], list(range(20)))


if __name__ == "__main__":
    unittest.main()
