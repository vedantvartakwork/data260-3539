"""Kafka grocery-recall worker with idempotency and manual offset commits."""

from __future__ import annotations

import asyncio
import json
from code.hw8.config import settings
from code.hw8.service import RecallService


async def run_worker() -> None:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

    service = RecallService()
    consumer = AIOKafkaConsumer(
        settings.entity_requests,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=f"{settings.prefix}-recall-worker",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )
    await consumer.start()
    await producer.start()
    print("Vedant Vartak - Consumer is ready and listening...", flush=True)
    print(f"[WORKER] request_topic={settings.entity_requests}", flush=True)
    try:
        async for record in consumer:
            message = record.value
            correlation_id = message.get("correlation_id", "")
            print(
                f"[WORKER RECEIVE] topic={record.topic} partition={record.partition} "
                f"offset={record.offset} correlation_id={correlation_id} "
                f"message={json.dumps(message, sort_keys=True)}",
                flush=True,
            )
            response = service.process(message)
            reply_to = message.get("reply_to", settings.entity_responses)
            metadata = await producer.send_and_wait(reply_to, response)
            print(
                f"[WORKER REPLY] topic={metadata.topic} partition={metadata.partition} "
                f"offset={metadata.offset} correlation_id={correlation_id} "
                f"response={json.dumps(response, sort_keys=True)}",
                flush=True,
            )
            await consumer.commit()
            print(f"[WORKER COMMIT] correlation_id={correlation_id} after_success=true", flush=True)
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
