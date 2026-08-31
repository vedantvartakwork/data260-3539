#!/usr/bin/env python3
"""Planner -> Reviewer -> deterministic Finalizer pipeline for Homework 1."""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from src.model_client import CompletionResult, OllamaClient


class PipelineValidationError(ValueError):
    pass


@dataclass
class StageRecord:
    stage: str
    output: dict[str, Any]
    input_tokens: int
    output_tokens: int


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def normalize_tag(tag: str) -> str:
    return " ".join(tag.casefold().split())


def validate_publish(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PipelineValidationError("output must be a JSON object")
    if set(value) != {"tags", "summary"}:
        raise PipelineValidationError("output must contain only tags and summary")

    tags = value.get("tags")
    summary = value.get("summary")
    if not isinstance(tags, list) or len(tags) != 3:
        raise PipelineValidationError("tags must contain exactly three strings")
    if not all(isinstance(tag, str) and len(tag.strip()) >= 2 for tag in tags):
        raise PipelineValidationError("each tag must be a meaningful non-empty string")
    normalized = [normalize_tag(tag) for tag in tags]
    if len(set(normalized)) != 3:
        raise PipelineValidationError("tags must not be duplicates")
    if any(tag in {"tag", "general", "information", "miscellaneous"} for tag in normalized):
        raise PipelineValidationError("tags must be topical rather than generic")

    if not isinstance(summary, str) or not summary.strip():
        raise PipelineValidationError("summary must be a non-empty string")
    summary = " ".join(summary.split())
    if word_count(summary) > 25:
        raise PipelineValidationError("summary must contain no more than 25 words")
    if len(re.findall(r"[.!?](?:[\"']|$)", summary)) != 1:
        raise PipelineValidationError("summary must be one sentence")

    return {"tags": [tag.strip() for tag in tags], "summary": summary}


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise PipelineValidationError("response did not contain a JSON object")
        try:
            value = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise PipelineValidationError(f"malformed JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise PipelineValidationError("JSON response must be an object")
    return value


def request_valid_json(
    client: OllamaClient,
    messages: list[dict[str, str]],
    validator: Callable[[Any], dict[str, Any]],
    temperature: float,
) -> tuple[dict[str, Any], list[CompletionResult]]:
    attempts: list[CompletionResult] = []
    current_messages = list(messages)
    last_error = "unknown validation error"
    for attempt in range(2):
        result = client.complete(current_messages, temperature=temperature, json_mode=True)
        attempts.append(result)
        try:
            return validator(extract_json_object(result.content)), attempts
        except PipelineValidationError as exc:
            last_error = str(exc)
            if attempt == 0:
                current_messages = current_messages + [
                    {"role": "assistant", "content": result.content},
                    {
                        "role": "user",
                        "content": (
                            f"The response failed validation: {last_error}. "
                            "Return one corrected JSON object only."
                        ),
                    },
                ]
    raise PipelineValidationError(f"model output remained invalid after one retry: {last_error}")


def validate_review(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PipelineValidationError("review must be an object")
    publish = validate_publish({"tags": value.get("tags"), "summary": value.get("summary")})
    notes = value.get("notes", [])
    if not isinstance(notes, list) or not all(isinstance(note, str) for note in notes):
        raise PipelineValidationError("review notes must be an array of strings")
    return {**publish, "notes": notes}


def run_pipeline(
    title: str,
    content: str,
    *,
    model: str = "qwen3:8b",
    temperature: float = 0.0,
    client: OllamaClient | None = None,
) -> dict[str, Any]:
    client = client or OllamaClient(model=model, temperature=temperature)
    source = f"Title: {title}\nContent: {content}"

    planner_messages = [
        {
            "role": "system",
            "content": (
                "You are the Planner. Derive topical labels and a concise summary only from the supplied title and content. "
                "Return valid JSON with exactly two keys: tags and summary. tags must be three distinct meaningful strings. "
                "summary must be one sentence of no more than 25 words. Do not use markdown."
            ),
        },
        {"role": "user", "content": source},
    ]
    planner, planner_calls = request_valid_json(client, planner_messages, validate_publish, temperature)

    reviewer_messages = [
        {
            "role": "system",
            "content": (
                "You are the Reviewer. Check whether the proposed tags are distinct, specific, and supported by the original input. "
                "Check that the summary is factual, one sentence, and at most 25 words. Correct problems when needed. "
                "Return only JSON with tags, summary, and notes. tags must contain exactly three strings; notes must be an array of short strings."
            ),
        },
        {
            "role": "user",
            "content": f"Original input:\n{source}\n\nPlanner proposal:\n{json.dumps(planner, ensure_ascii=False)}",
        },
    ]
    reviewer, reviewer_calls = request_valid_json(client, reviewer_messages, validate_review, temperature)

    final_publish = validate_publish({"tags": reviewer["tags"], "summary": reviewer["summary"]})
    changed = (
        [normalize_tag(tag) for tag in planner["tags"]] != [normalize_tag(tag) for tag in final_publish["tags"]]
        or planner["summary"].strip() != final_publish["summary"].strip()
    )

    def totals(calls: list[CompletionResult]) -> tuple[int, int]:
        return sum(call.input_tokens for call in calls), sum(call.output_tokens for call in calls)

    planner_in, planner_out = totals(planner_calls)
    reviewer_in, reviewer_out = totals(reviewer_calls)
    transcript = [
        asdict(StageRecord("Planner", planner, planner_in, planner_out)),
        asdict(StageRecord("Reviewer", {**reviewer, "changed": changed}, reviewer_in, reviewer_out)),
        asdict(StageRecord("Finalizer", final_publish, 0, 0)),
    ]
    return {
        "model": model,
        "temperature": temperature,
        "title": title,
        "content": content,
        "reviewer_changed": changed,
        "transcript": transcript,
        "publish": final_publish,
        "token_usage": {
            "input_tokens": planner_in + reviewer_in,
            "output_tokens": planner_out + reviewer_out,
        },
    }


def load_input(path: Path) -> tuple[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return str(value["title"]), str(value["content"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title")
    parser.add_argument("--content")
    parser.add_argument("--input-file", type=Path)
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--result-file", type=Path)
    args = parser.parse_args()

    if args.input_file:
        title, content = load_input(args.input_file)
    elif args.title and args.content:
        title, content = args.title, args.content
    else:
        parser.error("provide --input-file or both --title and --content")

    started = time.perf_counter()
    result = run_pipeline(title, content, model=args.model, temperature=args.temperature)
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)

    if not args.quiet:
        for record in result["transcript"]:
            print(f"\n--- {record['stage']} ---")
            print(json.dumps(record["output"], indent=2, ensure_ascii=False))
        print("\n--- Final Publish JSON ---")
        print(json.dumps(result["publish"], indent=2, ensure_ascii=False))
        print(f"\nLatency: {result['latency_ms']:.2f} ms")

    if args.result_file:
        args.result_file.parent.mkdir(parents=True, exist_ok=True)
        args.result_file.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

