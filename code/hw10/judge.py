"""Bounded local GEval judge implemented with DeepEval and Ollama."""

from __future__ import annotations

import asyncio
import json
import urllib.request
from code.hw10.config import settings
from dataclasses import dataclass
from typing import Any

from deepeval.metrics import GEval
from deepeval.metrics.g_eval.utils import Rubric
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase, SingleTurnParams


class OllamaDeepEvalModel(DeepEvalBaseLLM):
    """DeepEval model adapter with a hard HTTP timeout and JSON-schema output."""

    def __init__(self, model: str = settings.model) -> None:
        self.model_name = model
        super().__init__(model=model)

    def load_model(self) -> OllamaDeepEvalModel:
        return self

    def get_model_name(self) -> str:
        return f"local-ollama:{self.model_name}"

    def supports_structured_outputs(self) -> bool:
        return True

    def supports_json_mode(self) -> bool:
        return True

    def generate(self, prompt: str, schema: Any | None = None, **_: Any) -> Any:
        output_format: Any = "json"
        if schema is not None and hasattr(schema, "model_json_schema"):
            output_format = schema.model_json_schema()
        body = json.dumps(
            {
                "model": self.model_name,
                "stream": False,
                "think": False,
                "format": output_format,
                "messages": [{"role": "user", "content": prompt}],
                "options": {
                    "temperature": 0,
                    "seed": settings.verify_seed,
                    "num_ctx": 2048,
                    "num_predict": 192,
                },
                "keep_alive": "20m",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            settings.ollama_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=settings.judge_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = payload["message"]["content"]
        if schema is None:
            return content
        return schema.model_validate_json(content)

    async def a_generate(self, prompt: str, schema: Any | None = None, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self.generate, prompt, schema=schema, **kwargs)


RUBRIC = [
    Rubric(score_range=(1, 1), expected_outcome="Unsafe incorrect or non-responsive."),
    Rubric(score_range=(2, 2), expected_outcome="Partly relevant but missing important guidance."),
    Rubric(score_range=(3, 3), expected_outcome="Generally correct and useful but incomplete."),
    Rubric(
        score_range=(4, 4),
        expected_outcome="Correct clear and actionable with only minor omissions.",
    ),
    Rubric(score_range=(5, 5), expected_outcome="Complete precise safe and directly actionable."),
]


@dataclass(frozen=True)
class JudgeResult:
    score: int
    reason: str
    model: str


class LocalGEvalJudge:
    def __init__(self, model: OllamaDeepEvalModel | None = None) -> None:
        self.model = model or OllamaDeepEvalModel()

    def evaluate(self, question: str, output: str, criterion: str = "Helpfulness") -> JudgeResult:
        metric = GEval(
            name=criterion,
            criteria=(
                "Score the response from 1 to 5 for correctness relevance clarity safety and "
                "actionability in the grocery-recall domain. Do not reward invented facts."
            ),
            evaluation_steps=[
                "Check whether the response directly answers the user's request.",
                "Check correctness and whether safety guidance is responsible.",
                "Assess clarity completeness and practical actionability.",
                "Select exactly one integer score from the five-level rubric and briefly explain it.",
            ],
            evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
            rubric=RUBRIC,
            model=self.model,
            async_mode=False,
            threshold=0.5,
        )
        test_case = LLMTestCase(input=question, actual_output=output)
        normalized = float(metric.measure(test_case, _show_indicator=False))
        score = max(1, min(5, round(1 + (normalized * 4))))
        return JudgeResult(
            score=score, reason=str(metric.reason), model=self.model.get_model_name()
        )
