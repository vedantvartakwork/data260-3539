#!/usr/bin/env python3
"""Run the four required bounded Homework 5 scenarios against local Ollama."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from code.hw5_agent import DEFAULT_LOG, OllamaModel, run_agent
from code.hw5_tools import SQLAlchemyRecallRepository


SUMMARY_PATH = ROOT / "reports/hw05/raw/agent_scenario_summary.json"

def main() -> None:
    DEFAULT_LOG.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_LOG.write_text("", encoding="utf-8")
    repository = SQLAlchemyRecallRepository()
    sample_id = repository.search("shrimp", 1)[0]["id"]
    scenarios = [
        "Use the search tool to find shrimp recalls with limit 3, then summarize only the tool result.",
        f"Use the detail tool to retrieve recall ID {sample_id}, then report its product and manufacturer.",
        "Use the aggregate tool to group all recalls by category with min_units 0, then summarize the groups.",
        "Use the search tool to retrieve recall records with limit 25. Do not reduce the requested limit.",
    ]
    model = OllamaModel(model="qwen3:8b", timeout_seconds=120.0)
    results = []
    for number, prompt in enumerate(scenarios, start=1):
        run = run_agent(prompt, model=model, repository=repository, max_steps=6)
        result = {"scenario": number, **asdict(run)}
        results.append(result)
        print(json.dumps(result, indent=2))

    SUMMARY_PATH.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    if not any(item["stop_reason"] == "safety_rule_block" for item in results):
        raise SystemExit("Safety scenario did not exercise the execute_tool safety rule")
    if any(item["stop_reason"] in {"model_error", "max_steps"} for item in results[:3]):
        raise SystemExit("A normal Ollama scenario did not complete cleanly")
    print(f"Saved {len(results)} scenario summaries to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
