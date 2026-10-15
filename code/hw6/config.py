"""Central configuration for Homework 6."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True)
class HW6Settings:
    sid4: int = 3539
    port_base: int = 8839
    prefix: str = "s3539"
    seed: int = 3539
    verify_seed: int = 263539
    domain_id: int = 3
    mongo_uri: str = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
    mongo_database: str = os.getenv("MONGODB_DB", "s3539_doc")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    short_term_n: int = _positive_int("SHORT_TERM_N", 12)
    summarize_every_user_messages: int = _positive_int(
        "SUMMARIZE_EVERY_USER_MSGS", 4
    )
    episodic_top_k: int = _positive_int("EPISODIC_TOP_K", 3)
    embedding_model: str = os.getenv(
        "HW6_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    metrics_path: Path = PROJECT_ROOT / "reports" / "hw06" / "raw" / "chat_metrics.jsonl"


settings = HW6Settings()
