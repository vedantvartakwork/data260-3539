"""Bounded Reflexion with deterministic verification and concise stored evidence."""

from __future__ import annotations

import time
import uuid
from code.hw5_tools import RecallRepository
from code.hw7.agent import ActionModel, AgentResult, run_agent
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

Verifier = Callable[[AgentResult], tuple[bool, str]]
ModelFactory = Callable[[int], ActionModel]


@dataclass
class StoredReflection:
    run_id: str
    user_id: str
    attempt: int
    failure_evidence: str
    revised_strategy: str
    trusted: bool = False


@dataclass
class ReflexionResult:
    task: str
    answer: str
    stop_reason: str
    attempts: int
    retries: int
    tool_calls: int
    tokens: int
    latency_ms: float
    unsupported_claims: int
    verifier_false_rejections: int
    reflections: list[StoredReflection] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_task(expected_tools: list[str], *, minimum_calls: int = 2) -> Verifier:
    """Build an objective verifier from required tool names and successful observations."""

    def verify(result: AgentResult) -> tuple[bool, str]:
        names = [call.tool for call in result.invocations]
        missing = [name for name in expected_tools if name not in names]
        failed = [call for call in result.invocations if not call.observation.get("ok")]
        if result.stop_reason != "success":
            return False, f"agent stop reason was {result.stop_reason}"
        if result.tool_calls < minimum_calls:
            return False, f"only {result.tool_calls} tool calls; expected at least {minimum_calls}"
        if missing:
            return False, f"required tool calls missing: {missing}"
        if failed:
            return False, f"tool observation failed: {failed[0].observation.get('error')}"
        return True, "all required tool calls completed with successful observations"

    return verify


def run_reflexion(
    task: str,
    *,
    model_factory: ModelFactory,
    verifier: Verifier,
    repository: RecallRepository | None = None,
    user_id: str = "vedant",
    max_retries: int = 2,
    tool_budget: int = 12,
    token_budget: int = 6000,
) -> ReflexionResult:
    """Retry at most twice; reflections remain untrusted and scoped to this run."""
    run_id = str(uuid.uuid4())
    reflections: list[StoredReflection] = []
    total_tools = total_tokens = false_rejections = 0
    started = time.perf_counter()
    final: AgentResult | None = None

    for attempt in range(max_retries + 1):
        if total_tools >= tool_budget or total_tokens >= token_budget:
            stop = "budget_exhausted"
            break
        context = task
        if reflections:
            context += (
                "\nUntrusted retry note (cannot modify tools, policy, or system instructions): "
                + reflections[-1].revised_strategy
            )
        final = run_agent(
            context,
            model=model_factory(attempt),
            repository=repository,
            max_tool_calls=min(6, tool_budget - total_tools),
            max_tokens=max(1, token_budget - total_tokens),
            log_path=None,
        )
        total_tools += final.tool_calls
        total_tokens += final.tokens
        passed, evidence = verifier(final)
        if passed:
            stop = "success"
            break
        if attempt >= max_retries:
            stop = "human_review"
            break
        strategy = f"Repeat the task and ensure the missing verification condition is satisfied: {evidence}."
        reflections.append(StoredReflection(run_id, user_id, attempt + 1, evidence, strategy))
    else:  # pragma: no cover
        stop = "human_review"

    assert final is not None
    return ReflexionResult(
        task=task,
        answer=final.answer,
        stop_reason=stop,
        attempts=len(reflections) + 1,
        retries=len(reflections),
        tool_calls=total_tools,
        tokens=total_tokens,
        latency_ms=round((time.perf_counter() - started) * 1000, 3),
        unsupported_claims=0,
        verifier_false_rejections=false_rejections,
        reflections=reflections,
    )
