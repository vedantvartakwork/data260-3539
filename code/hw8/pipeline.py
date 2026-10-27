"""Planner, Writer, and Reviewer logic plus shared Kafka message handling."""

from __future__ import annotations

from code.hw8.config import settings
from copy import deepcopy
from typing import Any

ROLE_TOPICS = {
    "planner": (settings.inbox, settings.tasks),
    "writer": (settings.tasks, settings.drafts),
    "reviewer": (settings.drafts, settings.final),
}


def planner_answer(question: str) -> str:
    return (
        "1. Identify the requested decision and constraints. "
        "2. Collect the relevant grocery-recall facts. "
        "3. Draft a concise answer with consumer guidance."
    )


def writer_answer(question: str, plan: str) -> str:
    return (
        f"Question: {question}\n"
        "Draft: Review the recall code, affected product, and official consumer guidance. "
        "Do not use the product if the notice identifies a safety risk; follow the listed return "
        "or disposal instructions."
    )


def reviewer_answer(draft: str) -> str:
    return f"Approved: {draft}"


def process_stage(role: str, message: dict[str, Any]) -> dict[str, Any]:
    if role not in ROLE_TOPICS:
        raise ValueError(f"Unknown role: {role}")
    correlation_id = message.get("correlation_id")
    if not correlation_id:
        raise ValueError("correlation_id is required")
    question = str(message.get("question", "")).strip()
    if not question:
        raise ValueError("question is required")

    output = deepcopy(message)
    if role == "planner":
        output["plan"] = planner_answer(question)
        output["status"] = "planned"
    elif role == "writer":
        if not output.get("plan"):
            raise ValueError("plan is required")
        output["draft"] = writer_answer(question, output["plan"])
        output["status"] = "drafted"
    else:
        if not output.get("draft"):
            raise ValueError("draft is required")
        output["answer"] = reviewer_answer(output["draft"])
        output["status"] = "approved"
    output.setdefault("journey", []).append(role)
    return output
