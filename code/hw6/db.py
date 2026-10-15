"""PyMongo connection and MongoDB JSON-schema setup for Homework 6."""

from __future__ import annotations

from threading import Lock

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from code.hw6.config import settings


_client: MongoClient | None = None
_schema_lock = Lock()
_initialized_databases: set[str] = set()


RECALL_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["title", "status", "category", "recalled_at", "created_at", "updated_at"],
        "properties": {
            "title": {"bsonType": "string", "minLength": 2, "maxLength": 100},
            "description": {"bsonType": ["string", "null"], "maxLength": 1000},
            "status": {"enum": ["active", "monitoring", "resolved"]},
            "category": {
                "enum": ["Produce", "Meat and Seafood", "Dairy and Refrigerated", "Packaged Foods"]
            },
            "recalled_at": {"bsonType": "date"},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    }
}


MEMORY_VALIDATORS = {
    "messages": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "session_id", "role", "content", "created_at"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "session_id": {"bsonType": "string"},
                "role": {"enum": ["user", "assistant"]},
                "content": {"bsonType": "string"},
                "created_at": {"bsonType": "date"},
            },
        }
    },
    "summaries": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "session_id", "scope", "text", "created_at"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "session_id": {"bsonType": ["string", "null"]},
                "scope": {"enum": ["session", "user"]},
                "text": {"bsonType": "string"},
                "created_at": {"bsonType": "date"},
            },
        }
    },
    "episodes": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "session_id", "fact", "importance", "embedding", "created_at"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "session_id": {"bsonType": "string"},
                "fact": {"bsonType": "string", "maxLength": 240},
                "importance": {"bsonType": ["double", "int"], "minimum": 0, "maximum": 1},
                "embedding": {"bsonType": "array", "items": {"bsonType": ["double", "int"]}},
                "created_at": {"bsonType": "date"},
            },
        }
    },
}


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
    return _client


def get_db() -> Database:
    return get_client()[settings.mongo_database]


def _ensure_collection(db: Database, name: str, validator: dict) -> None:
    if name not in db.list_collection_names():
        db.create_collection(name, validator=validator, validationLevel="strict")
    else:
        db.command("collMod", name, validator=validator, validationLevel="strict")


def ensure_collections(db: Database | None = None) -> Database:
    database = db or get_db()
    key = f"{database.client.address}:{database.name}"
    if key in _initialized_databases:
        return database
    with _schema_lock:
        if key in _initialized_databases:
            return database
        _ensure_collection(database, "recall_documents", RECALL_VALIDATOR)
        for name, validator in MEMORY_VALIDATORS.items():
            _ensure_collection(database, name, validator)
        database.recall_documents.create_index([("created_at", DESCENDING)])
        database.messages.create_index(
            [("user_id", ASCENDING), ("session_id", ASCENDING), ("created_at", DESCENDING)]
        )
        database.summaries.create_index(
            [("user_id", ASCENDING), ("scope", ASCENDING), ("created_at", DESCENDING)]
        )
        database.episodes.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)]
        )
        _initialized_databases.add(key)
    return database
