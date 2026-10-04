"""Bounded Ollama tool-agent loop for Homework 5."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import httpx

from code.hw5_tools import RecallRepository, execute_tool


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "reports/hw05/raw/agent_runs.jsonl"
TOOLS = {
    "search": {"query": "string", "limit": "integer 1-10"},
    "detail": {"recall_id": "positive integer"},
    "aggregate": {"group_by": "category|manufacturer", "min_units": "integer >= 0"},
}


class AgentModel(Protocol):
    def next_action(self, messages: list[dict[str, str]]) -> dict[str, Any]: ...


class OllamaModel:
    def __init__(
        self,
        model: str = "qwen3:8b",
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 45.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def next_action(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "format": "json",
                "options": {"seed": 3539, "temperature": 0},
                "messages": messages,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        content = response.json()["message"]["content"]
        action = json.loads(content)
        if not isinstance(action, dict):
            raise ValueError("model response must be a JSON object")
        return action


class MockModel:
    """Offline deterministic model used by the required max_steps test."""

    def __init__(self, actions: list[dict[str, Any]], *, repeat_last: bool = False):
        self.actions = list(actions)
        self.repeat_last = repeat_last
        self.index = 0

    def next_action(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        del messages
        if self.index < len(self.actions):
            action = self.actions[self.index]
            self.index += 1
            return action
        if self.repeat_last and self.actions:
            return self.actions[-1]
        return {"final": "No further action."}


@dataclass
class AgentRun:
    user_input: str
    final_answer: str
    step_count: int
    tool_call_count: int
    stop_reason: str


def _write_event(path: Path | None, event: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True) + "\n")


def run_agent(
    user_input: str,
    *,
    model: AgentModel | None = None,
    repository: RecallRepository | None = None,
    max_steps: int = 6,
    log_path: Path | None = DEFAULT_LOG,
) -> AgentRun:
    """Run a bounded tool loop and record every step and stop reason."""
    active_model = model or OllamaModel()
    system = (
        "You are a grocery-recall assistant. Respond with exactly one JSON object. "
        f"To call a tool use {{\"tool\": name, \"inputs\": object}} from {TOOLS}. "
        "When finished use {\"final\": answer}. Base answers only on tool results."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_input},
    ]
    run_id = datetime.now(timezone.utc).isoformat()
    tool_calls = 0
    final_answer = ""
    stop_reason = "max_steps"

    for step in range(1, max_steps + 1):
        try:
            action = active_model.next_action(messages)
        except Exception as exc:
            final_answer = f"Agent model error: {exc}"
            stop_reason = "model_error"
            _write_event(
                log_path,
                {"run_id": run_id, "step": step, "event": "model_error", "error": str(exc)},
            )
            break

        if "final" in action:
            final_answer = str(action["final"])
            stop_reason = "normal_completion"
            _write_event(
                log_path,
                {"run_id": run_id, "step": step, "event": "final", "answer": final_answer},
            )
            break

        name = action.get("tool")
        inputs = action.get("inputs")
        if not isinstance(name, str) or not isinstance(inputs, dict):
            result = json.dumps(
                {"ok": False, "data": None, "error": "Invalid model action schema"}
            )
        else:
            result = execute_tool(name, inputs, repository)
            tool_calls += 1

        parsed_result = json.loads(result)
        _write_event(
            log_path,
            {
                "run_id": run_id,
                "step": step,
                "event": "tool_call",
                "tool": name,
                "inputs": inputs,
                "result": parsed_result,
            },
        )
        messages.append({"role": "assistant", "content": json.dumps(action)})
        messages.append({"role": "tool", "content": result})

        if not parsed_result.get("ok") and str(parsed_result.get("error", "")).startswith(
            "Safety rule blocked"
        ):
            final_answer = parsed_result["error"]
            stop_reason = "safety_rule_block"
            break
    else:
        step = max_steps
        final_answer = "Stopped after reaching max_steps."

    run = AgentRun(
        user_input=user_input,
        final_answer=final_answer,
        step_count=step,
        tool_call_count=tool_calls,
        stop_reason=stop_reason,
    )
    _write_event(
        log_path,
        {"run_id": run_id, "event": "stop", **asdict(run)},
    )
    return run
