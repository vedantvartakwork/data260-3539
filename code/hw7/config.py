"""Fixed personal configuration for DATA 260 Homework 7."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HW7Settings:
    sid4: int = 3539
    port_base: int = 8839
    prefix: str = "s3539"
    seed: int = 3539
    verify_seed: int = 263539
    domain_id: int = 3
    model: str = "qwen3:8b"


settings = HW7Settings()
