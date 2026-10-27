"""Reusable Kafka process for the Planner, Writer, or Reviewer stage."""

from __future__ import annotations

import asyncio
import json
from code.hw8.config import settings
from code.hw8.pipeline import ROLE_TOPICS, process_stage
from typing import Any


async def run_agent_worker(role: str, *, max_retries: int = 3) -> None:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

    input_topic, output_topic = ROLE_TOPICS[role]
    consumer = AIOKafkaConsumer(
        input_topic,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=f"{settings.prefix}-{role}-group",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )
    processed: dict[str, dict[str, Any]] = {}
    await consumer.start()
    await producer.start()
    print(
        f"Vedant Vartak - {role.title()} ready: {input_topic} -> {output_topic}",
        flush=True,
    )
    try:
        async for record in consumer:
            message = record.value
            correlation_id = str(message.get("correlation_id", ""))
            print(
                f"[{role.upper()} RECEIVE] topic={record.topic} partition={record.partition} "
                f"offset={record.offset} correlation_id={correlation_id}",
                flush=True,
            )
            if correlation_id in processed:
                output = processed[correlation_id]
                print(f"[{role.upper()} IDEMPOTENT] replay ignored; reusing output", flush=True)
            else:
                output = None
                last_error = "unknown"
                for attempt in range(1, max_retries + 1):
                    try:
                        if message.get("simulate_delay_role") == role:
                            await asyncio.sleep(float(message.get("simulate_delay_seconds", 0)))
                        output = process_stage(role, message)
                        break
                    except ValueError as exc:
                        last_error = str(exc)
                        print(
                            f"[{role.upper()} RETRY] attempt={attempt}/{max_retries} "
                            f"correlation_id={correlation_id} error={last_error}",
                            flush=True,
                        )
                if output is None:
                    dead = {
                        "correlation_id": correlation_id,
                        "failed_role": role,
                        "error": last_error,
                        "original_message": message,
                    }
                    await producer.send_and_wait(settings.dead_letter, dead)
                    print(
                        f"[{role.upper()} DEAD LETTER] topic={settings.dead_letter} "
                        f"correlation_id={correlation_id}",
                        flush=True,
                    )
                    await consumer.commit()
                    continue
                processed[correlation_id] = output
            key = str(output.get("entity_key", correlation_id)).encode("utf-8")
            metadata = await producer.send_and_wait(output_topic, output, key=key)
            print(
                f"[{role.upper()} SEND] topic={metadata.topic} partition={metadata.partition} "
                f"offset={metadata.offset} correlation_id={correlation_id} "
                f"status={output['status']}",
                flush=True,
            )
            await consumer.commit()
            print(f"[{role.upper()} COMMIT] after_success=true", flush=True)
    finally:
        await consumer.stop()
        await producer.stop()


def run(role: str) -> None:
    asyncio.run(run_agent_worker(role))
