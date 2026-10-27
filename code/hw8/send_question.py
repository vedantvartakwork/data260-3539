"""Submit one question and read its final approved JSON from Kafka."""

from __future__ import annotations

import asyncio
import json
import uuid
from code.hw8.config import settings


async def main() -> None:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

    correlation_id = str(uuid.uuid4())
    message = {
        "correlation_id": correlation_id,
        "entity_key": "recall-3539",
        "question": "What should a customer do after finding a matching grocery recall?",
        "journey": [],
    }
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )
    consumer = AIOKafkaConsumer(
        settings.final,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=f"{settings.prefix}-final-reader-{correlation_id}",
        auto_offset_reset="latest",
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    await consumer.start()
    await producer.start()
    try:
        metadata = await producer.send_and_wait(
            settings.inbox, message, key=message["entity_key"].encode("utf-8")
        )
        print("Vedant Vartak - DATA 260 Homework 8 three-agent pipeline")
        print(
            f"[USER SEND] topic={metadata.topic} partition={metadata.partition} "
            f"offset={metadata.offset} message={json.dumps(message, sort_keys=True)}"
        )
        async with asyncio.timeout(20):
            async for record in consumer:
                result = record.value
                if result.get("correlation_id") == correlation_id:
                    print(
                        f"[USER FINAL] topic={record.topic} correlation_id={correlation_id} "
                        f"message={json.dumps(result, sort_keys=True)}"
                    )
                    print("PASS journey=inbox -> tasks -> drafts -> final")
                    return
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
