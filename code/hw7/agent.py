"""Hand-written bounded tool agent built on the HW1 Ollama adapter."""

from __future__ import annotations

import json
import time
from code.hw5_tools import RecallRepository, execute_tool
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from src.model_client import OllamaClient

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG = ROOT / "reports/hw07/raw/agent_tool_calls.jsonl"
TOOL_SCHEMA = {
    "search": {"query": "string, 2-80 chars", "limit": "integer, 1-10"},
    "detail": {"recall_id": "positive integer"},
    "aggregate": {"group_by": "category|manufacturer", "min_units": "integer >= 0"},
}


class ActionModel(Protocol):
    def next_action(self, messages: list[dict[str, str]]) -> tuple[str, int]: ...


class OllamaActionModel:
    """JSON-action adapter that reuses the HW1 model client."""

    def __init__(self, model: str = "qwen3:8b") -> None:
        self.client = OllamaClient(model=model, temperature=0, timeout=90)

    def next_action(self, messages: list[dict[str, str]]) -> tuple[str, int]:
        result = self.client.complete(messages, json_mode=True, temperature=0)
        return result.content, result.total_tokens


class ScriptedActionModel:
    """Deterministic model double for objective offline tests and repair cases."""

    def __init__(self, actions: list[Any]) -> None:
        self.actions = list(actions)
        self.index = 0

    def next_action(self, messages: list[dict[str, str]]) -> tuple[str, int]:
        del messages
        action = self.actions[min(self.index, len(self.actions) - 1)]
        self.index += 1
        return (action if isinstance(action, str) else json.dumps(action), 12)


@dataclass
class ToolInvocation:
    step: int
    tool: str
    inputs: dict[str, Any]
    observation: dict[str, Any]


@dataclass
class AgentResult:
    user_input: str
    answer: str
    stop_reason: str
    steps: int
    tool_calls: int
    tokens: int
    latency_ms: float
    repairs: int
    initial_failure: str | None
    invocations: list[ToolInvocation] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _append_jsonl(path: Path | None, value: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")


def _parse_action(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None, "malformed arguments: response was not valid JSON"
    if not isinstance(value, dict):
        return None, "malformed arguments: action must be a JSON object"
    if "final" in value and isinstance(value["final"], str):
        return value, None
    if "tool" not in value:
        return None, "text when a tool was required: use a tool action before the final answer"
    if value.get("tool") not in TOOL_SCHEMA:
        return None, f"unknown tool: {value.get('tool')!r}; allowed tools are {sorted(TOOL_SCHEMA)}"
    if not isinstance(value.get("inputs"), dict):
        return None, "malformed arguments: inputs must be a JSON object"
    return value, None


def run_agent(
    user_input: str,
    *,
    model: ActionModel | None = None,
    repository: RecallRepository | None = None,
    max_steps: int = 8,
    max_tool_calls: int = 6,
    max_tokens: int = 2800,
    log_path: Path | None = DEFAULT_LOG,
) -> AgentResult:
    """Execute tool calls, append tool-role observations, repair once, and stop cleanly."""
    active_model = model or OllamaActionModel()
    system = (
        "You are a verification agent. Return exactly one JSON object per turn. "
        f"Tools: {json.dumps(TOOL_SCHEMA)}. A tool action is "
        '{"tool":"name","inputs":{...}}. Finish with {"final":"grounded answer"}. '
        "Use every tool needed by the request and never invent observations."
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user_input}]
    invocations: list[ToolInvocation] = []
    repairs = 0
    tokens = 0
    initial_failure: str | None = None
    answer = ""
    stop_reason = "iteration_ceiling"
    started = time.perf_counter()

    for step in range(1, max_steps + 1):
        if len(invocations) >= max_tool_calls or tokens >= max_tokens:
            stop_reason = "budget_exhausted"
            answer = "Stopped after reaching the tool-call or token budget."
            break
        try:
            raw, turn_tokens = active_model.next_action(messages)
            tokens += turn_tokens
        except Exception as exc:  # model boundary must stop cleanly
            stop_reason = "model_error"
            answer = f"Model request failed: {exc}"
            break

        action, problem = _parse_action(raw)
        if problem:
            initial_failure = initial_failure or problem.split(":", 1)[0]
            if repairs >= 1:
                stop_reason = "repair_exhausted"
                answer = f"Stopped after one failed repair: {problem}"
                break
            repairs += 1
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": f"Repair required: {problem}. Return one valid JSON action.",
                }
            )
            continue

        assert action is not None
        if "final" in action:
            answer = action["final"]
            stop_reason = "success"
            break

        result_text = execute_tool(action["tool"], action["inputs"], repository)
        observation = json.loads(result_text)
        invocation = ToolInvocation(step, action["tool"], action["inputs"], observation)
        invocations.append(invocation)
        _append_jsonl(log_path, {"event": "tool_call", **asdict(invocation)})
        messages.append({"role": "assistant", "content": json.dumps(action)})
        messages.append({"role": "tool", "content": result_text})
    else:
        step = max_steps
        answer = "Stopped after reaching the hard iteration ceiling."

    result = AgentResult(
        user_input=user_input,
        answer=answer,
        stop_reason=stop_reason,
        steps=step,
        tool_calls=len(invocations),
        tokens=tokens,
        latency_ms=round((time.perf_counter() - started) * 1000, 3),
        repairs=repairs,
        initial_failure=initial_failure,
        invocations=invocations,
    )
    _append_jsonl(log_path, {"event": "agent_stop", **result.as_dict()})
    return result
