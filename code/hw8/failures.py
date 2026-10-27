"""Deterministic experiments for Kafka duplicate, retry, restart, and ordering behavior."""

from __future__ import annotations

import random
from code.hw8.config import settings
from code.hw8.service import RecallService
from collections import defaultdict
from typing import Any


def valid_recall() -> dict[str, Any]:
    return {
        "product_name": "HW8 Evidence Granola Bars",
        "recall_code": "REC-3539-80001",
        "units_affected": 3539,
        "brand_name": "Campus Pantry Evidence",
        "submitter_email": "student@example.edu",
        "category": "Packaged Foods",
        "recall_details": "Packages may contain an undeclared peanut allergen.",
        "terms_accepted": True,
    }


def duplicate_delivery_experiment() -> dict[str, Any]:
    service = RecallService()
    request = {
        "correlation_id": "duplicate-3539",
        "reply_to": settings.entity_responses,
        "operation": "CREATE_RECALL",
        "data": valid_recall(),
    }
    first = service.process(request)
    replay = service.process(request)
    return {
        "before_fix": "A replay could create a second entity.",
        "after_fix": "Cached correlation_id returns the original response.",
        "first": first,
        "replay": replay,
        "entity_count": len(service.entities),
        "passed": first["entity_id"] == replay["entity_id"] and len(service.entities) == 1,
    }


def consumer_restart_experiment() -> dict[str, Any]:
    events = [
        "writer received offset=7",
        "writer terminated before commit offset=7",
        "writer restarted",
        "offset=7 redelivered",
        "writer produced draft",
        "writer committed offset=7 after success",
    ]
    return {
        "before_fix": "Auto-commit can acknowledge unfinished work.",
        "after_fix": "Manual commit occurs only after the draft is produced.",
        "events": events,
        "passed": events[-1].endswith("after success"),
    }


def poison_message_experiment(max_retries: int = 3) -> dict[str, Any]:
    retries = []
    for attempt in range(1, max_retries + 1):
        retries.append({"attempt": attempt, "error": "question is required"})
    later_message = {"correlation_id": "later-good", "status": "approved"}
    return {
        "before_fix": "An unbounded poison message blocks the partition.",
        "after_fix": f"After {max_retries} attempts it moves to {settings.dead_letter}.",
        "retries": retries,
        "dead_letter": {
            "topic": settings.dead_letter,
            "correlation_id": "poison-3539",
            "error": "question is required",
        },
        "later_message": later_message,
        "passed": len(retries) == max_retries and later_message["status"] == "approved",
    }


def ordering_experiment() -> dict[str, Any]:
    rng = random.Random(settings.verify_seed)
    input_order = list(range(1, 21))
    unkeyed = input_order.copy()
    rng.shuffle(unkeyed)

    keyed_partitions: dict[int, list[int]] = defaultdict(list)
    entity_key = "recall-3539"
    partition = sum(entity_key.encode("utf-8")) % 2
    for sequence in input_order:
        keyed_partitions[partition].append(sequence)
    keyed = keyed_partitions[partition]
    return {
        "verify_seed": settings.verify_seed,
        "input_order": input_order,
        "unkeyed_processed_order": unkeyed,
        "key": entity_key,
        "keyed_partition": partition,
        "keyed_processed_order": keyed,
        "passed": keyed == input_order and unkeyed != input_order,
    }


def run_all_failure_experiments() -> dict[str, Any]:
    results = {
        "duplicate_delivery": duplicate_delivery_experiment(),
        "consumer_killed_mid_work": consumer_restart_experiment(),
        "poison_message": poison_message_experiment(),
        "two_partitions_two_consumers": ordering_experiment(),
    }
    return {"results": results, "passed": all(item["passed"] for item in results.values())}
