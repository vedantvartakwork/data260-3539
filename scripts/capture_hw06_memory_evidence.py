#!/usr/bin/env python3
"""Run the required ten-message MongoDB memory demonstration and save evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from code.hw6.file_memory import FileMemoryManager
from code.hw6.memory import ChatService, SentenceTransformerEmbedder
from code.hw6.repositories import MemoryRepository
from src.model_client import OllamaClient


MESSAGES = [
    "My name is Vedant Vartak and my project prefix is s3539.",
    "Remember that my grocery safety project uses MongoDB.",
    "The database is named s3539_doc.",
    "I prefer concise JSON responses when we debug APIs.",
    "The local language model is qwen3:8b through Ollama.",
    "The document API runs on port 8839.",
    "Never call a hosted model for this assignment.",
    "Session summaries should be made every four user messages.",
    "Episodic facts should be retrieved with cosine similarity.",
    "What are my name, database, local model, and API port? Answer in one concise sentence.",
]


def clean(row: dict) -> dict:
    return {key: (str(value) if key in {"_id", "created_at"} else value) for key, value in row.items()}


def readable_evidence(output: dict) -> dict:
    """Remove large embedding arrays while preserving screenshot-ready proof."""
    episodes = [
        {key: value for key, value in row.items() if key != "embedding"}
        for row in output["memory_endpoint"]["episodes"]
    ]
    return {
        "student": output["student"],
        "conversation": [
            {"turn": row["turn"], "message": row["message"], "reply": row["response"]["reply"]}
            for row in output["conversation"]
        ],
        "GET /api/memory/vedant-hw6": {
            "message_count_returned": len(output["memory_endpoint"]["messages"]),
            "summary_count_returned": len(output["memory_endpoint"]["summaries"]),
            "episodes": episodes,
        },
        "GET /api/aggregate/vedant-hw6": output["aggregate_endpoint"],
        "mongo_collection_counts": {
            key: value for key, value in output["mongo_collections"].items() if key.endswith("_count")
        },
    }


def main() -> None:
    repo = MemoryRepository()
    repo.db.messages.delete_many({"user_id": "vedant-hw6"})
    repo.db.summaries.delete_many({"user_id": "vedant-hw6"})
    repo.db.episodes.delete_many({"user_id": "vedant-hw6"})
    chat = ChatService(
        repo,
        OllamaClient(temperature=0.0),
        SentenceTransformerEmbedder(),
        file_memory=FileMemoryManager(),
    )
    transcript = []
    for turn, message in enumerate(MESSAGES, start=1):
        response = chat.chat("vedant-hw6", "demo-3539", message)
        transcript.append({"turn": turn, "message": message, "response": response})

    memory = {
        "user_id": "vedant-hw6",
        "messages": repo.messages("vedant-hw6", limit=16),
        "summaries": repo.recent_summaries("vedant-hw6", limit=8),
        "episodes": repo.recent_episodes("vedant-hw6", limit=20),
    }
    aggregate = repo.aggregate("vedant-hw6")
    collections = {
        "message_count": repo.db.messages.count_documents({"user_id": "vedant-hw6"}),
        "summary_count": repo.db.summaries.count_documents({"user_id": "vedant-hw6"}),
        "episode_count": repo.db.episodes.count_documents({"user_id": "vedant-hw6"}),
        "message_sample": [clean(row) for row in repo.db.messages.find({"user_id": "vedant-hw6"}).sort("created_at", -1).limit(3)],
        "summary_sample": [clean(row) for row in repo.db.summaries.find({"user_id": "vedant-hw6"}).sort("created_at", -1).limit(3)],
        "episode_sample": [clean(row) for row in repo.db.episodes.find({"user_id": "vedant-hw6"}).sort("created_at", -1).limit(3)],
    }
    output = {"student": "Vedant Vartak", "conversation": transcript, "memory_endpoint": memory, "aggregate_endpoint": aggregate, "mongo_collections": collections}
    destination = PROJECT_ROOT / "reports" / "hw06" / "raw" / "memory_api_evidence.json"
    destination.write_text(json.dumps(output, indent=2, default=str) + "\n", encoding="utf-8")
    readable = readable_evidence(output)
    (destination.parent / "memory_api_readable.json").write_text(
        json.dumps(readable, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(json.dumps(readable, indent=2, default=str))


if __name__ == "__main__":
    main()
