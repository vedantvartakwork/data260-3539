"""Asynchronous Kafka request/response client used by FastAPI."""

from __future__ import annotations

import asyncio
import json
import uuid
from code.hw8.config import settings
from typing import Any


class KafkaRPC:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds
        self.producer: Any = None
        self.consumer: Any = None
        self.consumer_task: asyncio.Task[None] | None = None
        self.pending: dict[str, asyncio.Future[dict[str, Any]]] = {}

    async def start(self) -> None:
        from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )
        self.consumer = AIOKafkaConsumer(
            settings.entity_responses,
            bootstrap_servers=settings.kafka_bootstrap,
            group_id=f"{settings.prefix}-fastapi-responses",
            auto_offset_reset="latest",
            enable_auto_commit=True,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )
        await self.producer.start()
        await self.consumer.start()
        self.consumer_task = asyncio.create_task(self._consume_responses())
        print("Vedant Vartak - FastAPI Kafka RPC started", flush=True)
        print(f"[FASTAPI] listening topic={settings.entity_responses}", flush=True)

    async def stop(self) -> None:
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()

    async def _consume_responses(self) -> None:
        async for record in self.consumer:
            response = record.value
            correlation_id = response.get("correlation_id")
            print(
                f"[FASTAPI RECEIVE] topic={record.topic} partition={record.partition} "
                f"offset={record.offset} correlation_id={correlation_id} "
                f"message={json.dumps(response, sort_keys=True)}",
                flush=True,
            )
            future = self.pending.pop(correlation_id, None)
            if future and not future.done():
                future.set_result(response)

    async def request(
        self,
        operation: str,
        data: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        if not self.producer:
            raise RuntimeError("Kafka RPC is not started")
        correlation_id = correlation_id or str(uuid.uuid4())
        message = {
            "correlation_id": correlation_id,
            "reply_to": settings.entity_responses,
            "operation": operation,
            "data": data,
        }
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self.pending[correlation_id] = future
        metadata = await self.producer.send_and_wait(settings.entity_requests, message)
        print(
            f"[FASTAPI SEND] topic={metadata.topic} partition={metadata.partition} "
            f"offset={metadata.offset} correlation_id={correlation_id} "
            f"message={json.dumps(message, sort_keys=True)}",
            flush=True,
        )
        try:
            return await asyncio.wait_for(future, timeout=self.timeout_seconds)
        except TimeoutError:
            self.pending.pop(correlation_id, None)
            return {
                "correlation_id": correlation_id,
                "success": False,
                "error": "Kafka response timed out",
            }
