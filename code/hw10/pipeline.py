"""HW8/HW9 pipeline extended with semantic cache evaluation and tracing."""

from __future__ import annotations

import time
import uuid
from code.hw8.in_memory import InMemoryBroker
from code.hw8.pipeline import process_stage
from code.hw9.semantic_cache import InMemorySemanticCache
from code.hw10.config import settings
from code.hw10.evaluator import PipelineEvaluator, replay_evaluator
from code.hw10.tracing import TraceStore, utc_now
from pathlib import Path
from typing import Any


class ObservableRecallPipeline:
    def __init__(
        self,
        output_dir: Path | None = None,
        *,
        evaluator: PipelineEvaluator | None = None,
    ) -> None:
        self.output_dir = output_dir or settings.raw_dir
        self.trace_store = TraceStore(self.output_dir)
        self.broker = InMemoryBroker()
        self.cache = InMemorySemanticCache()
        self.evaluator = evaluator

    def reset(self) -> None:
        self.trace_store.reset()
        self.cache.clear()

    def run(
        self,
        question: str,
        *,
        trace_id: str | None = None,
        use_cache: bool = True,
        judge_mode: str = "replay",
        fail_stage: str | None = None,
    ) -> dict[str, Any]:
        trace_id = trace_id or str(uuid.uuid4())
        request_started = time.perf_counter()
        cache_hit = False
        error: str | None = None
        output: dict[str, Any] = {}
        try:
            with self.trace_store.span(trace_id, "cache_lookup") as span:
                match = self.cache.lookup(question, settings.cache_threshold) if use_cache else None
                cache_hit = match is not None
                span["cache_result"] = "hit" if cache_hit else "miss"
                span["status"] = "cache_hit" if cache_hit else "cache_miss"
            if cache_hit and match is not None:
                output = {
                    "correlation_id": trace_id,
                    "trace_id": trace_id,
                    "question": question,
                    "answer": match.answer,
                    "cache_result": "hit",
                    "journey": ["cache_lookup"],
                }
                return output

            message: dict[str, Any] = {
                "correlation_id": trace_id,
                "trace_id": trace_id,
                "question": question,
                "created_at": utc_now(),
                "metadata": {"domain": "grocery_recall", "seed": settings.seed},
                "journey": [],
            }
            with self.trace_store.span(trace_id, "inbox"):
                self.broker.send(f"{settings.prefix}.inbox", message, key=trace_id)

            with self.trace_store.span(trace_id, "planner"):
                if fail_stage == "planner":
                    raise RuntimeError("intentional planner failure for trace evidence")
                message = process_stage("planner", message)
                self.broker.send(f"{settings.prefix}.tasks", message, key=trace_id)

            with self.trace_store.span(trace_id, "queue_wait"):
                time.sleep(0.0005)

            with self.trace_store.span(trace_id, "writer"):
                if fail_stage == "writer":
                    raise RuntimeError("intentional writer failure for trace evidence")
                message = process_stage("writer", message)
                self.broker.send(f"{settings.prefix}.drafts", message, key=trace_id)

            with self.trace_store.span(trace_id, "reviewer"):
                if fail_stage == "reviewer":
                    raise RuntimeError("intentional reviewer failure for trace evidence")
                message = process_stage("reviewer", message)
                self.broker.send(f"{settings.prefix}.final", message, key=trace_id)

            with self.trace_store.span(trace_id, "evaluator"):
                if judge_mode == "live":
                    if self.evaluator is None:
                        self.evaluator = PipelineEvaluator()
                    evaluation = self.evaluator.evaluate(message)
                else:
                    evaluation = replay_evaluator(message)
                self.broker.send(f"{settings.prefix}.evaluations", evaluation, key=trace_id)

            answer = str(message["answer"])
            self.cache.put(
                question,
                answer,
                answer_id=f"answer-{trace_id[:8]}",
                entity_id=f"recall-{trace_id[:8]}",
                data_version=1,
            )
            output = {
                **message,
                "trace_id": trace_id,
                "cache_result": "miss",
                "evaluation": evaluation,
            }
            return output
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            elapsed_ms = round((time.perf_counter() - request_started) * 1000, 3)
            self.trace_store.request(
                {
                    "trace_id": trace_id,
                    "timestamp": utc_now(),
                    "question": question,
                    "cache_result": "hit" if cache_hit else "miss",
                    "status": "error" if error else "ok",
                    "error": error,
                    "e2e_latency_ms": elapsed_ms,
                }
            )
