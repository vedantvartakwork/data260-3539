#!/usr/bin/env python3
"""Interactive model-client demonstration with token accounting."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from src.model_client import OllamaClient


@dataclass
class SessionStats:
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class ReviewSession:
    def __init__(self, client: OllamaClient, instructions: str) -> None:
        self.client = client
        self.history: list[dict[str, str]] = [{"role": "system", "content": instructions}]
        self.stats = SessionStats()

    def serialized_history_length(self) -> int:
        return len(json.dumps(self.history, ensure_ascii=False, separators=(",", ":")))

    def stats_snapshot(self) -> dict[str, int]:
        return {
            "turn_count": self.stats.turns,
            "cumulative_input_tokens": self.stats.input_tokens,
            "cumulative_output_tokens": self.stats.output_tokens,
            "serialized_history_length": self.serialized_history_length(),
        }

    def submit(self, prompt: str) -> tuple[str, dict[str, int]]:
        messages = self.history + [{"role": "user", "content": prompt}]
        result = self.client.complete(messages)
        self.history.extend(
            [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": result.content},
            ]
        )
        self.stats.turns += 1
        self.stats.input_tokens += result.input_tokens
        self.stats.output_tokens += result.output_tokens
        usage = {
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "total_tokens": result.total_tokens,
        }
        return result.content, usage


def print_stats(snapshot: dict[str, int]) -> None:
    print("Session statistics:")
    print(f"  Turn count: {snapshot['turn_count']}")
    print(f"  Cumulative input tokens: {snapshot['cumulative_input_tokens']}")
    print(f"  Cumulative output tokens: {snapshot['cumulative_output_tokens']}")
    print(f"  Serialized conversation-history length: {snapshot['serialized_history_length']} characters")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--agent-file", type=Path, default=Path(__file__).with_name("AGENT.md"))
    args = parser.parse_args()

    instructions = args.agent_file.read_text(encoding="utf-8")
    session = ReviewSession(OllamaClient(model=args.model), instructions)
    print("Bullet-only code reviewer. Enter code or a review request. Commands: /stats, /quit")

    try:
        while True:
            prompt = input("review> ").strip()
            if not prompt:
                continue
            if prompt == "/stats":
                print_stats(session.stats_snapshot())
                continue
            if prompt in {"/quit", "/exit"}:
                break
            response, usage = session.submit(prompt)
            print(response)
            print(
                f"Tokens - input: {usage['input_tokens']}, output: {usage['output_tokens']}, "
                f"total: {usage['total_tokens']}"
            )
    finally:
        print("\nFinal totals:")
        print(f"  Cumulative input tokens: {session.stats.input_tokens}")
        print(f"  Cumulative output tokens: {session.stats.output_tokens}")
        print(f"  Turn count: {session.stats.turns}")


if __name__ == "__main__":
    main()
