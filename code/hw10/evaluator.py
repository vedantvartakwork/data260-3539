"""Correlation-aware Planner Writer Reviewer evaluation."""

from __future__ import annotations

from code.hw10.judge import LocalGEvalJudge
from dataclasses import asdict
from typing import Any


class PipelineEvaluator:
    def __init__(self, judge: LocalGEvalJudge | None = None) -> None:
        self.judge = judge or LocalGEvalJudge()

    def evaluate(self, message: dict[str, Any]) -> dict[str, Any]:
        trace_id = str(message["correlation_id"])
        question = str(message["question"])
        plan = self.judge.evaluate(question, str(message["plan"]), "Plan Quality")
        draft = self.judge.evaluate(question, str(message["draft"]), "Writer Helpfulness")
        final = self.judge.evaluate(question, str(message["answer"]), "Final Answer Helpfulness")
        return {
            "trace_id": trace_id,
            "plan": asdict(plan),
            "writer": asdict(draft),
            "final": asdict(final),
            "improvement": final.score - draft.score,
            "interpretation": (
                "Reviewer improved the Writer draft."
                if final.score > draft.score
                else "Reviewer preserved quality; no measured improvement was observed."
            ),
        }


def replay_evaluator(message: dict[str, Any]) -> dict[str, Any]:
    """Fast bounded replay used only for the 50-miss timing experiment."""
    draft = str(message.get("draft", ""))
    final = str(message.get("answer", ""))
    writer_score = 4 if "return" in draft.lower() or "disposal" in draft.lower() else 3
    final_score = min(5, writer_score + (1 if final.startswith("Approved:") else 0))
    return {
        "trace_id": str(message["correlation_id"]),
        "plan": {"score": 4, "reason": "Frozen rubric replay."},
        "writer": {"score": writer_score, "reason": "Frozen rubric replay."},
        "final": {"score": final_score, "reason": "Frozen rubric replay."},
        "improvement": final_score - writer_score,
        "interpretation": "Bounded replay for stage-latency measurement.",
    }
