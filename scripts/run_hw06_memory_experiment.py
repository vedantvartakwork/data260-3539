#!/usr/bin/env python3
"""Run the HW6 N-window and compression experiments with the local Ollama model."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT_BOOTSTRAP = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT_BOOTSTRAP) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_BOOTSTRAP))

from code.hw6.config import PROJECT_ROOT, settings
from code.hw6.memory import ChatService, DeterministicEmbedder, DeterministicModel
from code.hw6.repositories import InMemoryMemoryRepository
from src.model_client import OllamaClient


RAW = PROJECT_ROOT / "reports" / "hw06" / "raw"
PROBES = PROJECT_ROOT / "reports" / "hw06" / "memory_probes.yaml"

CONVERSATION = [
    "My name is Vedant Vartak. Please remember it.",
    "This project uses MongoDB for conversational memory.",
    "The required database name is s3539_doc.",
    "The language model is qwen3:8b running locally through Ollama.",
    "The default short-term memory window is 12 messages.",
    "Calling hosted language models is prohibited for this homework.",
    "The API framework is FastAPI and the database driver is PyMongo.",
    "The deterministic verification seed is 263539.",
    "Messages belong to both a user ID and a session ID.",
    "Session summaries are created every four user messages.",
    "Episodic retrieval uses local embeddings and cosine similarity.",
    "At most three new episodic facts are stored per user message.",
    "The project domain is grocery recall safety.",
    "Document records have active, monitoring, or resolved status.",
    "Document categories use a fixed four-value list.",
    "The service records prompt tokens and completion tokens.",
    "The service also records component token counts and latency.",
    "The memory endpoint returns the most recent messages.",
    "The aggregate endpoint groups message counts by day.",
    "The episodes collection stores importance from zero to one.",
    "AGENT.md contains durable project instructions.",
    "MEMORY.md contains compact must-not-forget facts.",
    "The compact command merges duplicate memory facts.",
    "Contradictions must be resolved explicitly rather than silently removed.",
    "Offline tests cannot require MongoDB, Ollama, or the internet.",
    "The web API listens on derived port 8839.",
    "The repository prefix is s3539.",
    "The final Git tag for this assignment is hw6.",
    "Raw per-turn metrics belong in reports/hw06/raw.",
    "The report must explain the quality and token-cost tradeoff.",
]


def score_answer(probe_id: str, answer: str) -> int:
    text = answer.lower()
    requirements = {
        "identity": ["vedant", "vartak"],
        "database": ["mongo", "s3539_doc"],
        "model": ["qwen3:8b", "ollama"],
        "window": ["12"],
        "safety": ["hosted", "prohibit"],
    }[probe_id]
    matches = sum(item in text for item in requirements)
    if matches == len(requirements):
        return 5
    if matches >= max(1, len(requirements) - 1):
        return 4
    if matches:
        return 3
    return 1


def run_case(name: str, model: Any, short_term_n: int, summarize_every: int, top_k: int) -> dict[str, Any]:
    metrics_path = RAW / f"{name}_turn_metrics.jsonl"
    metrics_path.unlink(missing_ok=True)
    repo = InMemoryMemoryRepository()
    chat = ChatService(
        repo,
        model,
        DeterministicEmbedder(),
        short_term_n=short_term_n,
        summarize_every=summarize_every,
        episodic_top_k=top_k,
        metrics_path=metrics_path,
    )
    transcript_path = RAW / f"{name}_transcript.jsonl"
    transcript_path.unlink(missing_ok=True)
    conversation_usage: list[dict[str, Any]] = []
    with transcript_path.open("w", encoding="utf-8") as handle:
        for turn, message in enumerate(CONVERSATION, start=1):
            response = chat.chat("vedant", name, message)
            conversation_usage.append(response["usage"])
            handle.write(json.dumps({"phase": "conversation", "turn": turn, "message": message, "response": response}, default=str) + "\n")

        probes = yaml.safe_load(PROBES.read_text(encoding="utf-8"))["probes"]
        scores = []
        for probe in probes:
            response = chat.chat("vedant", name, probe["question"])
            score = score_answer(probe["id"], response["reply"])
            scores.append(score)
            handle.write(json.dumps({"phase": "probe", "probe": probe, "score": score, "response": response}, default=str) + "\n")

    prompt_tokens = [row["prompt_tokens"] for row in conversation_usage]
    output_tokens = [row["completion_tokens"] for row in conversation_usage]
    latency = [row["latency_ms"] for row in conversation_usage]
    return {
        "name": name,
        "short_term_n": short_term_n,
        "summarize_every": summarize_every,
        "episodic_top_k": top_k,
        "conversation_turns": len(CONVERSATION),
        "probe_scores": scores,
        "mean_probe_score": round(statistics.mean(scores), 3),
        "mean_prompt_tokens": round(statistics.mean(prompt_tokens), 3),
        "mean_completion_tokens": round(statistics.mean(output_tokens), 3),
        "mean_latency_ms": round(statistics.mean(latency), 3),
        "total_prompt_tokens": sum(prompt_tokens),
        "total_completion_tokens": sum(output_tokens),
    }


def write_metrics(results: list[dict[str, Any]], mode: str) -> None:
    best = min(results, key=lambda row: row["total_prompt_tokens"] + 5 * row["total_completion_tokens"])
    worst = max(results, key=lambda row: row["total_prompt_tokens"] + 5 * row["total_completion_tokens"])
    prompt_savings = (1 - best["total_prompt_tokens"] / worst["total_prompt_tokens"]) * 100
    quality_change = best["mean_probe_score"] - worst["mean_probe_score"]

    def cost(row: dict[str, Any]) -> float:
        per_conversation = row["total_prompt_tokens"] / 1_000_000 * 1.0 + row["total_completion_tokens"] / 1_000_000 * 5.0
        return per_conversation * 10_000

    lines = [
        "# Homework 6 Memory Metrics",
        "",
        f"Mode: `{mode}`. Each row uses the same 30-message conversation and five fixed probes.",
        "",
        "| Run | N | Summary interval | Top-k episodes | Mean prompt tokens | Mean latency (ms) | Mean probe score (1–5) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(f"| {row['name']} | {row['short_term_n']} | {row['summarize_every']} | {row['episodic_top_k']} | {row['mean_prompt_tokens']} | {row['mean_latency_ms']} | {row['mean_probe_score']} |")
    lines.extend(
        [
            "",
            "## Cost projection for 10,000 30-turn conversations",
            "",
            "Assumptions: input tokens cost $1 per million and output tokens cost $5 per million.",
            f"Best measured case (`{best['name']}`): **${cost(best):,.2f}**.",
            f"Worst measured case (`{worst['name']}`): **${cost(worst):,.2f}**.",
            "",
            "## Selection",
            "",
            f"`{best['name']}` is the best setting because it has the lowest measured token-weighted cost and a {best['mean_probe_score']}/5 probe score. Relative to `{worst['name']}`, it saves **{prompt_savings:.1f}%** of prompt tokens and changes quality by **{quality_change:+.1f} points**. `{worst['name']}` is the worst setting because it has the highest projected cost. The fixed N sweep isolates the context-window tradeoff; the compact-policy row demonstrates controlled eviction plus more frequent compression and retrieval.",
            "",
        ]
    )
    (PROJECT_ROOT / "reports" / "hw06" / "METRICS.md").write_text("\n".join(lines), encoding="utf-8")
    (RAW / "experiment_summary.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    with (RAW / "all_turn_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "run", "user_id", "session_id", "short_term_n", "prompt_tokens",
            "completion_tokens", "system_tokens", "long_term_tokens",
            "short_term_tokens", "episode_tokens", "latency_ms", "model",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            path = RAW / f"{result['name']}_turn_metrics.jsonl"
            for line in path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                components = row["component_tokens"]
                writer.writerow(
                    {
                        "run": result["name"],
                        "user_id": row["user_id"],
                        "session_id": row["session_id"],
                        "short_term_n": row["short_term_n"],
                        "prompt_tokens": row["prompt_tokens"],
                        "completion_tokens": row["completion_tokens"],
                        "system_tokens": components["system"],
                        "long_term_tokens": components["long_term"],
                        "short_term_tokens": components["short_term"],
                        "episode_tokens": components["episodes"],
                        "latency_ms": row["latency_ms"],
                        "model": row["model"],
                    }
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Use deterministic offline model for a fast development run")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    model: Any = DeterministicModel() if args.offline else OllamaClient(model=settings.ollama_model, temperature=0.0)
    configs = [
        ("window_n4", 4, 4, 3),
        ("window_n12", 12, 4, 3),
        ("window_n30", 30, 4, 3),
        ("compact_policy", 4, 2, 5),
    ]
    results = [run_case(name, model, n, interval, top_k) for name, n, interval, top_k in configs]
    write_metrics(results, "offline deterministic" if args.offline else f"local Ollama {settings.ollama_model}")
    print("Vedant Vartak — DATA 260 Homework 6 memory experiment")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
