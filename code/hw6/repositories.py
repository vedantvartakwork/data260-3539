"""Persistence adapters for the Homework 6 document and memory APIs."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.database import Database

from code.hw6.db import ensure_collections


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    result = dict(document)
    if "_id" in result:
        result["id"] = str(result.pop("_id"))
    return result


class DocumentRepository:
    """MongoDB CRUD for the Part 1 recall-document collection."""

    def __init__(self, database: Database | None = None) -> None:
        self.db = ensure_collections(database)
        self.collection = self.db.recall_documents

    def create(self, values: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        document = {**values, "created_at": now, "updated_at": now}
        inserted = self.collection.insert_one(document)
        return self.get(str(inserted.inserted_id))  # type: ignore[return-value]

    def list(self, *, limit: int = 50, skip: int = 0) -> list[dict[str, Any]]:
        cursor = (
            self.collection.find()
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        return [_serialize(item) for item in cursor]  # type: ignore[misc]

    def get(self, document_id: str) -> dict[str, Any] | None:
        if not ObjectId.is_valid(document_id):
            return None
        return _serialize(self.collection.find_one({"_id": ObjectId(document_id)}))

    def update(self, document_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        if not ObjectId.is_valid(document_id):
            return None
        self.collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {**values, "updated_at": utc_now()}},
        )
        return self.get(document_id)

    def delete(self, document_id: str) -> bool:
        if not ObjectId.is_valid(document_id):
            return False
        return self.collection.delete_one({"_id": ObjectId(document_id)}).deleted_count == 1


class MemoryRepository:
    """MongoDB storage for messages, summaries, and episodic facts."""

    def __init__(self, database: Database | None = None) -> None:
        self.db = ensure_collections(database)

    def add_message(
        self, user_id: str, session_id: str, role: str, content: str
    ) -> dict[str, Any]:
        document = {
            "user_id": user_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": utc_now(),
        }
        inserted = self.db.messages.insert_one(document)
        document["id"] = str(inserted.inserted_id)
        return document

    def messages(
        self,
        user_id: str,
        *,
        session_id: str | None = None,
        limit: int = 16,
        before_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"user_id": user_id}
        if session_id is not None:
            query["session_id"] = session_id
        if before_id and ObjectId.is_valid(before_id):
            query["_id"] = {"$lt": ObjectId(before_id)}
        newest_first = list(
            self.db.messages.find(query).sort("created_at", DESCENDING).limit(limit)
        )
        return [_serialize(item) for item in reversed(newest_first)]  # type: ignore[misc]

    def user_message_count(self, user_id: str, session_id: str) -> int:
        return self.db.messages.count_documents(
            {"user_id": user_id, "session_id": session_id, "role": "user"}
        )

    def add_summary(
        self, user_id: str, session_id: str | None, scope: str, text: str
    ) -> dict[str, Any]:
        document = {
            "user_id": user_id,
            "session_id": session_id,
            "scope": scope,
            "text": text,
            "created_at": utc_now(),
        }
        inserted = self.db.summaries.insert_one(document)
        document["id"] = str(inserted.inserted_id)
        return document

    def latest_summary(
        self, user_id: str, scope: str, session_id: str | None = None
    ) -> dict[str, Any] | None:
        query: dict[str, Any] = {"user_id": user_id, "scope": scope}
        if scope == "session":
            query["session_id"] = session_id
        return _serialize(self.db.summaries.find_one(query, sort=[("created_at", DESCENDING)]))

    def recent_summaries(self, user_id: str, *, limit: int = 8) -> list[dict[str, Any]]:
        cursor = self.db.summaries.find({"user_id": user_id}).sort(
            "created_at", DESCENDING
        ).limit(limit)
        return [_serialize(item) for item in cursor]  # type: ignore[misc]

    def add_episode(
        self,
        user_id: str,
        session_id: str,
        fact: str,
        importance: float,
        embedding: list[float],
    ) -> dict[str, Any]:
        document = {
            "user_id": user_id,
            "session_id": session_id,
            "fact": fact[:240],
            "importance": float(importance),
            "embedding": [float(value) for value in embedding],
            "created_at": utc_now(),
        }
        inserted = self.db.episodes.insert_one(document)
        document["id"] = str(inserted.inserted_id)
        return document

    def episodes(self, user_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        cursor = self.db.episodes.find({"user_id": user_id}).sort(
            "created_at", DESCENDING
        ).limit(limit)
        return [_serialize(item) for item in cursor]  # type: ignore[misc]

    def recent_episodes(self, user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        return self.episodes(user_id, limit=limit)

    def aggregate(self, user_id: str) -> dict[str, Any]:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        counts = [
            {"date": row["_id"], "message_count": row["count"]}
            for row in self.db.messages.aggregate(pipeline)
        ]
        return {"user_id": user_id, "daily_message_counts": counts, "recent_summaries": self.recent_summaries(user_id)}


class InMemoryMemoryRepository:
    """Deterministic repository used by offline tests and experiments."""

    def __init__(self) -> None:
        self.message_rows: list[dict[str, Any]] = []
        self.summary_rows: list[dict[str, Any]] = []
        self.episode_rows: list[dict[str, Any]] = []
        self._counter = 0

    def _id(self) -> str:
        self._counter += 1
        return f"{self._counter:024x}"

    def add_message(self, user_id: str, session_id: str, role: str, content: str) -> dict[str, Any]:
        row = {"id": self._id(), "user_id": user_id, "session_id": session_id, "role": role, "content": content, "created_at": utc_now()}
        self.message_rows.append(row)
        return dict(row)

    def messages(self, user_id: str, *, session_id: str | None = None, limit: int = 16, before_id: str | None = None) -> list[dict[str, Any]]:
        rows = [row for row in self.message_rows if row["user_id"] == user_id and (session_id is None or row["session_id"] == session_id)]
        if before_id:
            rows = [row for row in rows if row["id"] < before_id]
        return [dict(row) for row in rows[-limit:]]

    def user_message_count(self, user_id: str, session_id: str) -> int:
        return sum(row["user_id"] == user_id and row["session_id"] == session_id and row["role"] == "user" for row in self.message_rows)

    def add_summary(self, user_id: str, session_id: str | None, scope: str, text: str) -> dict[str, Any]:
        row = {"id": self._id(), "user_id": user_id, "session_id": session_id, "scope": scope, "text": text, "created_at": utc_now()}
        self.summary_rows.append(row)
        return dict(row)

    def latest_summary(self, user_id: str, scope: str, session_id: str | None = None) -> dict[str, Any] | None:
        rows = [row for row in self.summary_rows if row["user_id"] == user_id and row["scope"] == scope and (scope != "session" or row["session_id"] == session_id)]
        return dict(rows[-1]) if rows else None

    def recent_summaries(self, user_id: str, *, limit: int = 8) -> list[dict[str, Any]]:
        return [dict(row) for row in reversed([row for row in self.summary_rows if row["user_id"] == user_id][-limit:])]

    def add_episode(self, user_id: str, session_id: str, fact: str, importance: float, embedding: list[float]) -> dict[str, Any]:
        row = {"id": self._id(), "user_id": user_id, "session_id": session_id, "fact": fact[:240], "importance": float(importance), "embedding": list(embedding), "created_at": utc_now()}
        self.episode_rows.append(row)
        return dict(row)

    def episodes(self, user_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        return [dict(row) for row in reversed([row for row in self.episode_rows if row["user_id"] == user_id][-limit:])]

    def recent_episodes(self, user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        return self.episodes(user_id, limit=limit)

    def aggregate(self, user_id: str) -> dict[str, Any]:
        counts = Counter(row["created_at"].date().isoformat() for row in self.message_rows if row["user_id"] == user_id)
        return {"user_id": user_id, "daily_message_counts": [{"date": day, "message_count": count} for day, count in sorted(counts.items())], "recent_summaries": self.recent_summaries(user_id)}
