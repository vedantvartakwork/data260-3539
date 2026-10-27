"""FastAPI wrapper for the Homework 8 Kafka RPC service."""

from __future__ import annotations

from code.hw8.config import settings
from code.hw8.rpc import KafkaRPC
from code.hw8.service import RecallService
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

rpc = KafkaRPC()
direct_service = RecallService()


class OperationRequest(BaseModel):
    operation: str = Field(examples=["CREATE_RECALL"])
    data: dict[str, Any]
    correlation_id: str | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    await rpc.start()
    yield
    await rpc.stop()


app = FastAPI(title="DATA 260 HW8 Grocery Recall Kafka Service", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "student": "Vedant Vartak",
        "port": settings.port_base,
        "request_topic": settings.entity_requests,
        "response_topic": settings.entity_responses,
    }


@app.post("/api/hw8/entities")
async def entity_operation(request: OperationRequest) -> dict[str, Any]:
    return await rpc.request(
        request.operation,
        request.data,
        correlation_id=request.correlation_id,
    )


@app.post("/api/hw8/entities-direct")
def direct_entity_operation(request: OperationRequest) -> dict[str, Any]:
    """Direct endpoint retained only for optional JMeter comparison."""
    correlation_id = request.correlation_id or "jmeter-direct"
    return direct_service.process(
        {
            "correlation_id": correlation_id,
            "reply_to": settings.entity_responses,
            "operation": request.operation,
            "data": request.data,
        }
    )
