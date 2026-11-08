"""Grounded grocery-recall answer adapter with optional local Ollama generation."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from code.hw9.config import settings
from code.hw9.store import RecallStore
from dataclasses import dataclass
from typing import Any

CODE_RE = re.compile(r"REC-3539-\d{5}", re.IGNORECASE)


@dataclass
class AgentAnswer:
    text: str
    answer_id: str
    entity_id: str
    data_version: int
    model: str


class GroceryRecallAgent:
    """Adapter that grounds every answer in the versioned recall store."""

    def __init__(self, store: RecallStore, use_ollama: bool | None = None) -> None:
        self.store = store
        self.use_ollama = (
            os.getenv("HW9_USE_OLLAMA", "0") == "1" if use_ollama is None else use_ollama
        )

    @staticmethod
    def _intent(query: str) -> str:
        lowered = query.lower()
        if any(term in lowered for term in ("unit", "amount", "many", "quantity")):
            return "units"
        if any(term in lowered for term in ("manufacturer", "maker", "company", "brand")):
            return "manufacturer"
        if any(term in lowered for term in ("reason", "problem", "issue", "detail")):
            return "details"
        if any(term in lowered for term in ("guidance", "instruction", "action", "should")):
            return "guidance"
        if any(term in lowered for term in ("product", "item", "food", "name")):
            return "product"
        return "summary"

    @staticmethod
    def _grounded_answer(recall: dict[str, Any], intent: str) -> str:
        code = recall["recall_code"]
        if intent == "units":
            return f"{code} affects {recall['units_affected']:,} units."
        if intent == "manufacturer":
            return f"{code} was issued by {recall['manufacturer']}."
        if intent == "details":
            return f"The reason for {code} is: {recall['recall_details']}."
        if intent == "guidance":
            return f"Consumer guidance for {code}: {recall['guidance']}"
        if intent == "product":
            return f"{code} applies to {recall['product_name']}."
        return (
            f"{code} covers {recall['product_name']} from {recall['manufacturer']} and affects "
            f"{recall['units_affected']:,} units. {recall['guidance']}"
        )

    def _ollama_polish(self, query: str, grounded: str) -> str:
        prompt = (
            "Answer the grocery recall question using only the supplied grounded answer. "
            "Preserve every code and number exactly. Return one concise sentence.\n"
            f"Question: {query}\nGrounded answer: {grounded}"
        )
        payload = json.dumps(
            {
                "model": settings.model,
                "prompt": prompt,
                "stream": False,
                "options": {"seed": settings.seed},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.loads(response.read().decode("utf-8"))
            text = str(result.get("response", "")).strip()
            return text or grounded
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return grounded

    def answer(self, query: str) -> AgentAnswer:
        match = CODE_RE.search(query.upper())
        if not match:
            return AgentAnswer(
                text="I can only answer questions that identify a REC-3539 recall code.",
                answer_id="unsupported",
                entity_id="",
                data_version=0,
                model=settings.model,
            )
        recall_code = match.group(0).upper()
        recall = self.store.get_recall(recall_code)
        if recall is None:
            return AgentAnswer(
                text=f"No supported recall record exists for {recall_code}.",
                answer_id=f"missing:{recall_code}",
                entity_id=recall_code,
                data_version=0,
                model=settings.model,
            )
        intent = self._intent(query)
        grounded = self._grounded_answer(recall, intent)
        text = self._ollama_polish(query, grounded) if self.use_ollama else grounded
        return AgentAnswer(
            text=text,
            answer_id=f"{recall_code}:{intent}",
            entity_id=recall_code,
            data_version=int(recall["data_version"]),
            model=settings.model,
        )
