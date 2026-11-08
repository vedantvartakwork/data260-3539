"""Ingress semantic-cache handler in front of the grounded agent adapter."""

from __future__ import annotations

import time
from code.hw9.agent_adapter import GroceryRecallAgent
from code.hw9.config import settings
from code.hw9.semantic_cache import CacheMatch
from dataclasses import asdict
from typing import Any


class SemanticQueryService:
    def __init__(self, cache: Any, agent: GroceryRecallAgent) -> None:
        self.cache = cache
        self.agent = agent

    def query(
        self,
        question: str,
        threshold: float | None = None,
        enforce_version: bool = False,
    ) -> dict[str, Any]:
        threshold = settings.cache_threshold if threshold is None else threshold
        started = time.perf_counter()
        match: CacheMatch | None = self.cache.lookup(question, threshold)
        if match is not None:
            if enforce_version and match.entity_id:
                record = self.agent.store.get_recall(match.entity_id)
                if record is None or int(record["data_version"]) != match.data_version:
                    self.cache.invalidate_entity(match.entity_id)
                    match = None
            if match is not None:
                latency_ms = (time.perf_counter() - started) * 1000
                print(f"CACHE HIT similarity={match.similarity:.4f} query={question}")
                return {
                    "answer": match.answer,
                    "answer_id": match.answer_id,
                    "entity_id": match.entity_id,
                    "data_version": match.data_version,
                    "matched_query": match.query,
                    "is_cached": True,
                    "similarity": round(match.similarity, 6),
                    "latency_ms": round(latency_ms, 3),
                }

        answer = self.agent.answer(question)
        self.cache.put(
            question,
            answer.text,
            answer.answer_id,
            answer.entity_id,
            answer.data_version,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        print(f"CACHE MISS query={question}")
        return {
            **asdict(answer),
            "answer": answer.text,
            "is_cached": False,
            "similarity": 0.0,
            "latency_ms": round(latency_ms, 3),
        }

    def update_recall_and_invalidate(self, recall_code: str, units_affected: int) -> dict[str, int]:
        version = self.agent.store.update_units(recall_code, units_affected)
        removed = self.cache.invalidate_entity(recall_code)
        return {"data_version": version, "invalidated_entries": removed}
