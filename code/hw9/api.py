"""FastAPI ingress for the Homework 9 Redis semantic cache."""

from __future__ import annotations

from code.hw9.agent_adapter import GroceryRecallAgent
from code.hw9.config import settings
from code.hw9.query_service import SemanticQueryService
from code.hw9.semantic_cache import RedisSemanticCache
from code.hw9.store import RecallStore
from contextlib import asynccontextmanager
from pathlib import Path

import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    decode_responses=False,
)
store = RecallStore(ROOT / "reports" / "hw09" / "raw" / "hw09.db", redis_client)
cache = RedisSemanticCache(redis_client)
service = SemanticQueryService(cache, GroceryRecallAgent(store))


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    threshold: float = Field(default=settings.cache_threshold, ge=0.0, le=1.0)


class UnitsUpdate(BaseModel):
    units_affected: int = Field(gt=0)


@asynccontextmanager
async def lifespan(_: FastAPI):
    redis_client.ping()
    print(
        f"Vedant Vartak - DATA 260 Homework 9 API ready on {settings.port_base + 1}",
        flush=True,
    )
    yield
    store.close()
    redis_client.close()


app = FastAPI(title="DATA 260 HW9 Recall Cache", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "ok": bool(redis_client.ping()),
        "student": "Vedant Vartak",
        "prefix": settings.prefix,
        "model": settings.model,
    }


@app.post("/api/hw9/query")
def query(payload: QuestionRequest) -> dict[str, object]:
    return service.query(payload.question, threshold=payload.threshold, enforce_version=True)


@app.post("/api/hw9/recalls/{recall_code}/view")
def increment_view(recall_code: str) -> dict[str, object]:
    try:
        count = store.increment_recall_views(recall_code)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"recall_code": recall_code, "view_count": count}


@app.put("/api/hw9/recalls/{recall_code}/units")
def update_units(recall_code: str, payload: UnitsUpdate) -> dict[str, object]:
    try:
        result = service.update_recall_and_invalidate(recall_code, payload.units_affected)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"recall_code": recall_code, "units_affected": payload.units_affected, **result}
