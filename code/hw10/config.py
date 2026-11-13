"""Personal Homework 10 configuration derived from SID4 3539."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class HW10Settings:
    sid4: int = 3539
    prefix: str = "s3539"
    port_base: int = 8839
    seed: int = 3539
    verify_seed: int = 263539
    domain_id: int = 3
    model: str = "qwen3:8b"
    ollama_url: str = "http://127.0.0.1:11434/api/chat"
    judge_timeout_seconds: float = 60.0
    cache_threshold: float = 0.995
    report_dir: Path = ROOT / "reports" / "hw10"

    @property
    def raw_dir(self) -> Path:
        return self.report_dir / "raw"

    @property
    def data_dir(self) -> Path:
        return self.report_dir / "data"


settings = HW10Settings()
