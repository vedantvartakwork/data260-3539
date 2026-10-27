"""Fixed personal configuration and Kafka topic names for Homework 8."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class HW8Settings:
    sid4: int = 3539
    port_base: int = 8839
    prefix: str = "s3539"
    seed: int = 3539
    verify_seed: int = 263539
    domain_id: int = 3
    model: str = "qwen3:8b"
    kafka_bootstrap: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    @property
    def entity_requests(self) -> str:
        return f"{self.prefix}_entity_requests"

    @property
    def entity_responses(self) -> str:
        return f"{self.prefix}_entity_responses"

    @property
    def inbox(self) -> str:
        return f"{self.prefix}_inbox"

    @property
    def tasks(self) -> str:
        return f"{self.prefix}_tasks"

    @property
    def drafts(self) -> str:
        return f"{self.prefix}_drafts"

    @property
    def final(self) -> str:
        return f"{self.prefix}_final"

    @property
    def dead_letter(self) -> str:
        return f"{self.prefix}_dead_letter"


settings = HW8Settings()
