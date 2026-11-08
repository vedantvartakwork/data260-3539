"""Personal Homework 9 configuration derived from SID4 3539."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class HW9Settings:
    sid4: int = 3539
    port_base: int = 8839
    prefix: str = "s3539"
    seed: int = 3539
    verify_seed: int = 263539
    domain_id: int = 3
    model: str = "qwen3:8b"
    redis_host: str = os.getenv("HW9_REDIS_HOST", "127.0.0.1")
    redis_port: int = int(os.getenv("HW9_REDIS_PORT", "6399"))
    initial_cache_threshold: float = 0.85
    cache_threshold: float = float(os.getenv("HW9_CACHE_THRESHOLD", "0.95"))
    cache_ttl_seconds: int = int(os.getenv("HW9_CACHE_TTL", "900"))
    vector_dim: int = 384

    @property
    def view_prefix(self) -> str:
        return f"{self.prefix}:views:recall:"

    @property
    def semantic_prefix(self) -> str:
        return f"{self.prefix}:semantic:"

    @property
    def semantic_index(self) -> str:
        return f"{self.prefix}:semantic:vectors"


settings = HW9Settings()
