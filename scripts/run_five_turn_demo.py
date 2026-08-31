#!/usr/bin/env python3
"""Run and save the required five-turn token-accounting demonstration."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hw1_client import ReviewSession
from src.model_client import OllamaClient


PROMPTS = [
    "Review this JavaScript: const total = prices.reduce((sum, price) => sum + price, 0);",
    "Review this validation: if (details.length < 25) alert('Too short');",
    "Review this Python: tags = list(set(tags))[:3]",
    "Review this shell command: docker run -p 8839:8839 data260-3539",
    "Review this JSON parsing: data = json.loads(response)",
]


def main() -> None:
    instructions = Path("AGENT.md").read_text(encoding="utf-8")
    session = ReviewSession(OllamaClient(model="qwen3:8b"), instructions)
    records: list[dict[str, object]] = []
    for turn, prompt in enumerate(PROMPTS, start=1):
        response, usage = session.submit(prompt)
        record: dict[str, object] = {"turn": turn, "prompt": prompt, "response": response, "usage": usage}
        records.append(record)
        print(f"Turn {turn}\n{response}\nTokens: {usage}")
        if turn in {3, 5}:
            snapshot = session.stats_snapshot()
            record["stats_after_turn"] = snapshot
            print(f"/stats after turn {turn}: {json.dumps(snapshot)}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "qwen3:8b",
        "model_turns": 5,
        "stats_commands": 2,
        "turns": records,
        "final_stats": session.stats_snapshot(),
    }
    output_path = Path("reports/hw01/raw/five_turn_demo.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with Path("reports/hw01/RUN_LOG.txt").open("a", encoding="utf-8") as handle:
        handle.write(f"[{output['generated_at']}] Completed five-turn demo; output={output_path}\n")


if __name__ == "__main__":
    main()
