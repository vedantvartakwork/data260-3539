"""Two-agent evaluator-repair and validated lesson-memory implementation."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass
class Evaluation:
    result: str
    explanation: str
    feedback: str


@dataclass
class AttemptResult:
    question_id: str
    question: str
    initial_answer: str
    evaluator_feedback: str
    revised_answer: str
    final_answer: str
    final_evaluation: str
    attempts: int
    latency_ms: float
    lessons_used: list[str]


class LessonStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]\n", encoding="utf-8")

    def load(self) -> list[dict[str, Any]]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, lessons: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(lessons, indent=2) + "\n", encoding="utf-8")

    def add(self, failure_pattern: str, correction: str) -> dict[str, Any]:
        lessons = self.load()
        existing = next(
            (lesson for lesson in lessons if lesson["failure_pattern"] == failure_pattern), None
        )
        if existing:
            return existing
        lesson = {
            "lesson_id": f"lesson_{len(lessons) + 1:03d}",
            "failure_pattern": failure_pattern,
            "correction": correction,
            "created_at": date.today().isoformat(),
            "use_count": 0,
        }
        lessons.append(lesson)
        self.save(lessons)
        return lesson

    def relevant(self, failure_pattern: str) -> list[dict[str, Any]]:
        lessons = self.load()
        selected = [item for item in lessons if item["failure_pattern"] == failure_pattern]
        if selected:
            ids = {item["lesson_id"] for item in selected}
            for lesson in lessons:
                if lesson["lesson_id"] in ids:
                    lesson["use_count"] += 1
            self.save(lessons)
        return selected

    def remove(self, lesson_id: str) -> None:
        self.save([item for item in self.load() if item["lesson_id"] != lesson_id])


class AnsweringAgent:
    def __init__(self, reference: dict[str, Any], lessons: LessonStore) -> None:
        self.reference = reference
        self.lessons = lessons

    def answer(
        self,
        question_id: str,
        feedback: str = "",
        use_lessons: bool = False,
    ) -> tuple[str, list[str]]:
        record = self.reference[question_id]
        pattern = record.get("failure_pattern", "none")
        lesson_ids: list[str] = []
        lesson_applies = False
        if use_lessons and pattern != "none":
            selected = self.lessons.relevant(pattern)
            lesson_ids = [item["lesson_id"] for item in selected]
            lesson_applies = bool(selected)
        if record.get("unsupported"):
            return "The reference dataset does not support an answer to this question.", lesson_ids
        controlled_failure = bool(record.get("controlled_failure"))
        if controlled_failure and not feedback and not lesson_applies:
            return str(record["incomplete_answer"]), lesson_ids
        return str(record["canonical_answer"]), lesson_ids


class EvaluatorAgent:
    def __init__(self, reference: dict[str, Any]) -> None:
        self.reference = reference

    def evaluate(self, question_id: str, answer: str) -> Evaluation:
        record = self.reference[question_id]
        required = [str(token).lower() for token in record["required_tokens"]]
        missing = [token for token in required if token not in answer.lower()]
        if missing:
            feedback = "Include the grounded fact(s): " + ", ".join(missing) + "."
            return Evaluation(
                result="REVISE",
                explanation=f"Missing required reference facts: {', '.join(missing)}",
                feedback=feedback,
            )
        return Evaluation(
            result="PASS", explanation="All required facts are supported.", feedback=""
        )


class SelfImprovingSystem:
    def __init__(self, reference_path: str | Path, lessons_path: str | Path) -> None:
        payload = json.loads(Path(reference_path).read_text(encoding="utf-8"))
        self.reference = {item["question_id"]: item for item in payload}
        self.lessons = LessonStore(lessons_path)
        self.answering = AnsweringAgent(self.reference, self.lessons)
        self.evaluator = EvaluatorAgent(self.reference)

    def run_case(
        self,
        question: dict[str, str],
        repair: bool,
        use_lessons: bool,
    ) -> AttemptResult:
        started = time.perf_counter()
        question_id = question["question_id"]
        initial, lesson_ids = self.answering.answer(question_id, use_lessons=use_lessons)
        evaluation = self.evaluator.evaluate(question_id, initial)
        revised = ""
        attempts = 1
        final = initial
        if evaluation.result == "REVISE" and repair:
            revised, second_lessons = self.answering.answer(
                question_id,
                feedback=evaluation.feedback,
                use_lessons=use_lessons,
            )
            lesson_ids.extend(item for item in second_lessons if item not in lesson_ids)
            attempts = 2
            final = revised
            evaluation = self.evaluator.evaluate(question_id, final)
        return AttemptResult(
            question_id=question_id,
            question=question["question"],
            initial_answer=initial,
            evaluator_feedback=evaluation.feedback
            if attempts == 1
            else self.evaluator.evaluate(question_id, initial).feedback,
            revised_answer=revised,
            final_answer=final,
            final_evaluation=evaluation.result,
            attempts=attempts,
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            lessons_used=lesson_ids,
        )

    def evaluate_dataset(
        self,
        dataset: list[dict[str, str]],
        repair: bool,
        use_lessons: bool,
    ) -> dict[str, Any]:
        results = [asdict(self.run_case(item, repair, use_lessons)) for item in dataset]
        correct = sum(item["final_evaluation"] == "PASS" for item in results)
        return {
            "correct": correct,
            "incorrect": len(results) - correct,
            "average_attempts": round(sum(item["attempts"] for item in results) / len(results), 3),
            "average_latency_ms": round(
                sum(item["latency_ms"] for item in results) / len(results), 3
            ),
            "results": results,
        }

    def learn_from_failure(self, question_id: str) -> dict[str, Any]:
        record = self.reference[question_id]
        return self.lessons.add(
            str(record["failure_pattern"]),
            str(record["lesson_correction"]),
        )

    def validate_lesson(
        self,
        lesson_id: str,
        validation: list[dict[str, str]],
    ) -> dict[str, Any]:
        before = self.evaluate_dataset(validation, repair=False, use_lessons=False)
        after = self.evaluate_dataset(validation, repair=False, use_lessons=True)
        before_by_id = {item["question_id"]: item for item in before["results"]}
        after_by_id = {item["question_id"]: item for item in after["results"]}
        failed_before = {
            question_id
            for question_id, result in before_by_id.items()
            if result["final_evaluation"] != "PASS"
        }
        correct_before = set(before_by_id) - failed_before
        unrelated_ids = {
            item["question_id"]
            for item in validation
            if self.reference[item["question_id"]].get("unsupported")
        }
        failure_cases_not_regressed = sum(
            after_by_id[question_id]["final_evaluation"] == "PASS" for question_id in failed_before
        ) >= sum(
            before_by_id[question_id]["final_evaluation"] == "PASS" for question_id in failed_before
        )
        previously_correct_remain_correct = all(
            after_by_id[question_id]["final_evaluation"] == "PASS" for question_id in correct_before
        )
        unrelated_remain_grounded = all(
            after_by_id[question_id]["final_evaluation"] == "PASS"
            and after_by_id[question_id]["final_answer"]
            == self.reference[question_id]["canonical_answer"]
            for question_id in unrelated_ids
        )
        kept = (
            failure_cases_not_regressed
            and previously_correct_remain_correct
            and unrelated_remain_grounded
        )
        if not kept:
            self.lessons.remove(lesson_id)
        return {
            "lesson_id": lesson_id,
            "before_correct": before["correct"],
            "after_correct": after["correct"],
            "failure_cases_not_regressed": failure_cases_not_regressed,
            "previously_correct_remain_correct": previously_correct_remain_correct,
            "unrelated_remain_grounded": unrelated_remain_grounded,
            "kept": kept,
        }
