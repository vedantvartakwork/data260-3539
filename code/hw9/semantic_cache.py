"""Redis vector cache plus an in-memory backend for deterministic unit tests."""

from __future__ import annotations

import hashlib
import json
import time
from array import array
from code.hw9.config import settings
from code.hw9.embedding import DomainEmbeddingModel, cosine_similarity
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheMatch:
    answer: str
    similarity: float
    query: str
    answer_id: str
    entity_id: str
    data_version: int


class InMemorySemanticCache:
    def __init__(self, embedding_model: DomainEmbeddingModel | None = None) -> None:
        self.embedding_model = embedding_model or DomainEmbeddingModel(settings.vector_dim)
        self.entries: list[dict[str, Any]] = []

    def clear(self) -> None:
        self.entries.clear()

    def put(
        self,
        query: str,
        answer: str,
        answer_id: str,
        entity_id: str,
        data_version: int,
    ) -> None:
        self.entries.append(
            {
                "query": query,
                "answer": answer,
                "answer_id": answer_id,
                "entity_id": entity_id,
                "data_version": data_version,
                "embedding": self.embedding_model.embed(query),
            }
        )

    def lookup(self, query: str, threshold: float) -> CacheMatch | None:
        incoming = self.embedding_model.embed(query)
        if not self.entries:
            return None
        best = max(self.entries, key=lambda item: cosine_similarity(incoming, item["embedding"]))
        similarity = cosine_similarity(incoming, best["embedding"])
        if similarity < threshold:
            return None
        return CacheMatch(
            answer=best["answer"],
            similarity=similarity,
            query=best["query"],
            answer_id=best["answer_id"],
            entity_id=best["entity_id"],
            data_version=int(best["data_version"]),
        )

    def invalidate_entity(self, entity_id: str) -> int:
        before = len(self.entries)
        self.entries = [entry for entry in self.entries if entry["entity_id"] != entity_id]
        return before - len(self.entries)


class RedisSemanticCache:
    """Redis vector index, using native Vector Sets or RediSearch as available."""

    def __init__(
        self, redis_client: Any, embedding_model: DomainEmbeddingModel | None = None
    ) -> None:
        self.redis = redis_client
        self.embedding_model = embedding_model or DomainEmbeddingModel(settings.vector_dim)
        info = self.redis.execute_command("COMMAND", "INFO", "VADD")
        self.native_vectors = (
            bool(info.get("VADD")) if isinstance(info, dict) else bool(info and info[0])
        )
        self.ensure_index()

    def ensure_index(self) -> None:
        if self.native_vectors:
            return
        try:
            self.redis.execute_command("FT.INFO", settings.semantic_index)
        except Exception:
            self.redis.execute_command(
                "FT.CREATE",
                settings.semantic_index,
                "ON",
                "HASH",
                "PREFIX",
                "1",
                settings.semantic_prefix,
                "SCHEMA",
                "query",
                "TEXT",
                "answer",
                "TEXT",
                "answer_id",
                "TAG",
                "entity_id",
                "TAG",
                "data_version",
                "NUMERIC",
                "embedding",
                "VECTOR",
                "HNSW",
                "6",
                "TYPE",
                "FLOAT32",
                "DIM",
                str(settings.vector_dim),
                "DISTANCE_METRIC",
                "COSINE",
            )

    @staticmethod
    def _binary(vector: list[float]) -> bytes:
        return array("f", vector).tobytes()

    def clear(self) -> None:
        keys = list(self.redis.scan_iter(match=f"{settings.semantic_prefix}*"))
        if keys:
            self.redis.delete(*keys)

    def put(
        self,
        query: str,
        answer: str,
        answer_id: str,
        entity_id: str,
        data_version: int,
    ) -> str:
        digest = hashlib.sha256(
            f"{query}|{answer_id}|{entity_id}|{data_version}".encode()
        ).hexdigest()[:20]
        key = f"{settings.semantic_prefix}{digest}"
        mapping = {
            "query": query,
            "answer": answer,
            "answer_id": answer_id,
            "entity_id": entity_id,
            "data_version": int(data_version),
            "created_at": time.time(),
            "embedding": self._binary(self.embedding_model.embed(query)),
        }
        if self.native_vectors:
            attributes = json.dumps(
                {
                    "query": query,
                    "answer": answer,
                    "answer_id": answer_id,
                    "entity_id": entity_id,
                    "data_version": int(data_version),
                    "created_at": time.time(),
                }
            )
            self.redis.execute_command(
                "VADD",
                settings.semantic_index,
                "FP32",
                mapping["embedding"],
                digest,
                "NOQUANT",
                "SETATTR",
                attributes,
            )
            entity_key = f"{settings.semantic_prefix}entity:{entity_id}"
            self.redis.sadd(entity_key, digest)
            self.redis.expire(entity_key, settings.cache_ttl_seconds)
            self.redis.expire(settings.semantic_index, settings.cache_ttl_seconds)
            return key
        self.redis.hset(key, mapping=mapping)
        self.redis.expire(key, settings.cache_ttl_seconds)
        return key

    def lookup(self, query: str, threshold: float) -> CacheMatch | None:
        blob = self._binary(self.embedding_model.embed(query))
        if self.native_vectors:
            result = self.redis.execute_command(
                "VSIM",
                settings.semantic_index,
                "FP32",
                blob,
                "WITHSCORES",
                "WITHATTRIBS",
                "COUNT",
                "1",
            )
            if not result:
                return None
            similarity = float(result[1])
            if similarity < threshold:
                return None
            attributes = result[2]
            if isinstance(attributes, bytes):
                attributes = attributes.decode("utf-8")
            data = json.loads(attributes)
            return CacheMatch(
                answer=str(data["answer"]),
                similarity=similarity,
                query=str(data["query"]),
                answer_id=str(data["answer_id"]),
                entity_id=str(data["entity_id"]),
                data_version=int(data["data_version"]),
            )
        result = self.redis.execute_command(
            "FT.SEARCH",
            settings.semantic_index,
            "*=>[KNN 1 @embedding $vector AS distance]",
            "PARAMS",
            "2",
            "vector",
            blob,
            "SORTBY",
            "distance",
            "RETURN",
            "7",
            "query",
            "answer",
            "answer_id",
            "entity_id",
            "data_version",
            "distance",
            "created_at",
            "DIALECT",
            "2",
        )
        if not result or int(result[0]) == 0:
            return None
        values = result[2]
        if isinstance(values, list):
            data = {}
            for index in range(0, len(values), 2):
                key = values[index]
                value = values[index + 1]
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                data[str(key)] = value
        else:
            data = json.loads(values)
        similarity = 1.0 - float(data["distance"])
        if similarity < threshold:
            return None
        return CacheMatch(
            answer=str(data["answer"]),
            similarity=similarity,
            query=str(data["query"]),
            answer_id=str(data["answer_id"]),
            entity_id=str(data["entity_id"]),
            data_version=int(float(data["data_version"])),
        )

    def invalidate_entity(self, entity_id: str) -> int:
        if self.native_vectors:
            entity_key = f"{settings.semantic_prefix}entity:{entity_id}"
            members = list(self.redis.smembers(entity_key))
            if not members:
                return 0
            removed = sum(
                int(self.redis.execute_command("VREM", settings.semantic_index, member))
                for member in members
            )
            self.redis.delete(entity_key)
            return removed
        removed = 0
        for key in self.redis.scan_iter(match=f"{settings.semantic_prefix}*"):
            raw = self.redis.hget(key, "entity_id")
            if raw == entity_id or raw == entity_id.encode():
                removed += int(self.redis.delete(key))
        return removed
