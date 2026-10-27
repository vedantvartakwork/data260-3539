"""Exercise all four Part 3 failures against the running Kafka stack."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.hw8.config import settings
from code.hw8.failures import valid_recall

REPORT = ROOT / "reports" / "hw08"
RAW = REPORT / "raw"
COMPOSE = ["docker", "compose", "-p", "data260-hw8", "-f", "docker-compose.hw8.yml"]


def compose(*args: str) -> str:
    return subprocess.check_output([*COMPOSE, *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT)


async def producer_and_consumer(topic: str, group_suffix: str):
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=f"{settings.prefix}-evidence-{group_suffix}-{uuid.uuid4()}",
        auto_offset_reset="latest",
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    await consumer.start()
    await producer.start()
    return producer, consumer


async def matching(
    consumer, correlation_ids: set[str], timeout: float = 30
) -> list[dict[str, Any]]:
    found: set[str] = set()
    arrival: list[dict[str, Any]] = []

    async def collect() -> None:
        async for record in consumer:
            value = record.value
            correlation_id = value.get("correlation_id")
            if correlation_id in correlation_ids and correlation_id not in found:
                found.add(correlation_id)
                arrival.append(
                    {
                        "partition": record.partition,
                        "offset": record.offset,
                        "value": value,
                    }
                )
                if found == correlation_ids:
                    return

    await asyncio.wait_for(collect(), timeout=timeout)
    return arrival


async def duplicate_case() -> dict[str, Any]:
    correlation_id = f"live-duplicate-{uuid.uuid4()}"
    payload = {
        "correlation_id": correlation_id,
        "operation": "CREATE_RECALL",
        "data": valid_recall(),
    }
    endpoint = f"http://127.0.0.1:{settings.port_base}/api/hw8/entities"
    async with httpx.AsyncClient(timeout=20) as client:
        first = (await client.post(endpoint, json=payload)).json()
        replay = (await client.post(endpoint, json=payload)).json()
    return {
        "correlation_id": correlation_id,
        "first": first,
        "replay": replay,
        "passed": first["entity_id"] == replay["entity_id"] and replay.get("duplicate") is True,
    }


async def poison_case() -> dict[str, Any]:
    producer, dead_consumer = await producer_and_consumer(settings.dead_letter, "dead-letter")
    final_consumer = None
    try:
        from aiokafka import AIOKafkaConsumer

        final_consumer = AIOKafkaConsumer(
            settings.final,
            bootstrap_servers=settings.kafka_bootstrap,
            group_id=f"{settings.prefix}-evidence-final-{uuid.uuid4()}",
            auto_offset_reset="latest",
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )
        await final_consumer.start()
        poison_id = f"live-poison-{uuid.uuid4()}"
        good_id = f"live-after-poison-{uuid.uuid4()}"
        await producer.send_and_wait(
            settings.inbox,
            {"correlation_id": poison_id, "question": "", "journey": []},
        )
        dead = (await matching(dead_consumer, {poison_id}, timeout=20))[0]
        await producer.send_and_wait(
            settings.inbox,
            {
                "correlation_id": good_id,
                "entity_key": "recall-3539",
                "question": "What is the safe action for this recalled product?",
                "journey": [],
            },
            key=b"recall-3539",
        )
        good = (await matching(final_consumer, {good_id}, timeout=20))[0]
        return {
            "poison_correlation_id": poison_id,
            "dead_letter": dead,
            "later_good_message": good,
            "passed": dead["value"]["failed_role"] == "planner"
            and good["value"]["status"] == "approved",
        }
    finally:
        if final_consumer:
            await final_consumer.stop()
        await dead_consumer.stop()
        await producer.stop()


async def consumer_death_case() -> dict[str, Any]:
    producer, final_consumer = await producer_and_consumer(settings.final, "restart-final")
    correlation_id = f"live-restart-{uuid.uuid4()}"
    message = {
        "correlation_id": correlation_id,
        "entity_key": "recall-restart-3539",
        "question": "Explain restart recovery.",
        "plan": "Produce one restart-safe draft.",
        "journey": ["planner"],
        "status": "planned",
        "simulate_delay_role": "writer",
        "simulate_delay_seconds": 8,
    }
    try:
        await producer.send_and_wait(settings.tasks, message, key=b"recall-restart-3539")
        await asyncio.sleep(2)
        stop_output = compose("stop", "writer-1", "writer-2")
        await asyncio.sleep(1)
        start_output = compose("start", "writer-1", "writer-2")
        final = (await matching(final_consumer, {correlation_id}, timeout=35))[0]
        return {
            "correlation_id": correlation_id,
            "stop_output": stop_output.strip(),
            "start_output": start_output.strip(),
            "final": final,
            "passed": final["value"]["status"] == "approved",
        }
    finally:
        await final_consumer.stop()
        await producer.stop()


async def ordering_case() -> dict[str, Any]:
    producer, drafts = await producer_and_consumer(settings.drafts, "ordering")
    try:
        unkeyed_ids: list[str] = []
        keyed_ids: list[str] = []
        for sequence in range(1, 21):
            correlation_id = f"live-unkeyed-{uuid.uuid4()}"
            unkeyed_ids.append(correlation_id)
            await producer.send_and_wait(
                settings.tasks,
                {
                    "correlation_id": correlation_id,
                    "entity_key": f"unkeyed-{sequence}",
                    "sequence": sequence,
                    "question": "Ordering test",
                    "plan": "Preserve sequence evidence.",
                    "journey": ["planner"],
                    "simulate_delay_role": "writer",
                    "simulate_delay_seconds": 0.08 if sequence % 2 else 0.0,
                },
            )
        unkeyed_records = await matching(drafts, set(unkeyed_ids), timeout=35)
        unkeyed_order = [record["value"]["sequence"] for record in unkeyed_records]

        for sequence in range(1, 21):
            correlation_id = f"live-keyed-{uuid.uuid4()}"
            keyed_ids.append(correlation_id)
            await producer.send_and_wait(
                settings.tasks,
                {
                    "correlation_id": correlation_id,
                    "entity_key": "related-recall-3539",
                    "sequence": sequence,
                    "question": "Ordering test",
                    "plan": "Preserve sequence evidence.",
                    "journey": ["planner"],
                    "simulate_delay_role": "writer",
                    "simulate_delay_seconds": 0.01,
                },
                key=b"related-recall-3539",
            )
        keyed_records = await matching(drafts, set(keyed_ids), timeout=35)
        keyed_records.sort(key=lambda record: record["offset"])
        keyed_order = [record["value"]["sequence"] for record in keyed_records]
        keyed_partitions = sorted({record["partition"] for record in keyed_records})
        return {
            "verify_seed": settings.verify_seed,
            "input_order": list(range(1, 21)),
            "unkeyed_processed_order": unkeyed_order,
            "keyed_processed_order": keyed_order,
            "keyed_partitions": keyed_partitions,
            "passed": keyed_order == list(range(1, 21)) and len(keyed_partitions) == 1,
        }
    finally:
        await drafts.stop()
        await producer.stop()


async def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    payload = {
        "student": "Vedant Vartak",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "duplicate_delivery": await duplicate_case(),
        "consumer_killed_mid_work": await consumer_death_case(),
        "poison_message": await poison_case(),
        "two_partitions_two_consumers": await ordering_case(),
    }
    payload["passed"] = all(
        value["passed"]
        for key, value in payload.items()
        if isinstance(value, dict) and "passed" in value
    )
    target = RAW / "live_failure_experiments.json"
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("Vedant Vartak - DATA 260 HW8 live Kafka failure experiments")
    for key, value in payload.items():
        if isinstance(value, dict) and "passed" in value:
            print(f"{'PASS' if value['passed'] else 'FAIL'} {key}")
    print(f"PASS all={payload['passed']}")
    print(f"raw_json={target}")
    if not payload["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
