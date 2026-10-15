"""FastAPI routes for Homework 6 long-term chat memory."""

from __future__ import annotations

import uuid
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from pymongo.errors import PyMongoError

from code.hw6.file_memory import FileMemoryManager
from code.hw6.memory import ChatService, SentenceTransformerEmbedder
from code.hw6.repositories import MemoryRepository
from code.hw6.schemas import ChatRequest, ChatResponse
from src.model_client import OllamaClient


router = APIRouter(prefix="/api", tags=["HW6 memory"])


@lru_cache(maxsize=1)
def service() -> ChatService:
    return ChatService(
        MemoryRepository(),
        OllamaClient(),
        SentenceTransformerEmbedder(),
        file_memory=FileMemoryManager(),
    )


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> dict:
    try:
        session_id = payload.session_id or f"session-{uuid.uuid4().hex[:12]}"
        return service().chat(payload.user_id, session_id, payload.message)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Local model or embedding failure: {exc}") from exc


@router.get("/memory/{user_id}")
def get_memory(user_id: str) -> dict:
    try:
        repo = MemoryRepository()
        return {
            "user_id": user_id,
            "messages": repo.messages(user_id, limit=16),
            "summaries": repo.recent_summaries(user_id, limit=8),
            "episodes": repo.recent_episodes(user_id, limit=20),
        }
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable") from exc


@router.get("/aggregate/{user_id}")
def aggregate_memory(user_id: str) -> dict:
    try:
        return MemoryRepository().aggregate(user_id)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB is unavailable") from exc
