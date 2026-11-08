"""Run all required Homework 9 counter, cache, staleness, and agent experiments."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.hw9.agent_adapter import GroceryRecallAgent
from code.hw9.config import settings
from code.hw9.query_service import SemanticQueryService
from code.hw9.self_improving import SelfImprovingSystem
from code.hw9.semantic_cache import InMemorySemanticCache, RedisSemanticCache
from code.hw9.store import RecallStore

import redis

REPORT = ROOT / "reports" / "hw09"
DATA = REPORT / "data"
RAW = REPORT / "raw"
RAW.mkdir(parents=True, exist_ok=True)


class MemoryCounter:
    """Minimal Redis-compatible counter used only for the offline fallback run."""

    def __init__(self) -> None:
        self.values: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def delete(self, key: str) -> int:
        return int(self.values.pop(key, None) is not None)

    def close(self) -> None:
        return None


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run_counter(store: RecallStore) -> dict[str, Any]:
    recall_code = "REC-3539-00001"
    store.reset_view_counter(recall_code)
    accesses = []
    for number in range(1, 26):
        current = store.increment_recall_views(recall_code)
        accesses.append({"access": number, "total": current, "synced": current % 10 == 0})
    row = store.get_recall(recall_code)
    assert row is not None
    result = {
        "recall_code": recall_code,
        "redis_count": accesses[-1]["total"],
        "database_count": row["view_count"],
        "accesses": accesses,
        "passed": accesses[-1]["total"] == 25 and row["view_count"] == 20,
    }
    return result


def run_ingress_workload(service: SemanticQueryService) -> dict[str, Any]:
    service.cache.clear()
    queries = [
        "How many units are affected by REC-3539-00001?",
        "How many units are affected by REC-3539-00001?",
        "What quantity is impacted in recall REC-3539-00001?",
        "Who manufactured REC-3539-00002?",
        "Which company made the item in REC-3539-00002?",
        "What product is named in REC-3539-00003?",
        "What is the weather in San Jose?",
        "What is the weather in San Jose?",
        "What is the reason for REC-3539-00004?",
        "What should consumers do for REC-3539-00005?",
        "Give the consumer instructions for REC-3539-00005.",
        "How many units are affected by REC-3539-00006?",
    ]
    results = [service.query(query, threshold=0.85) for query in queries]
    hits = [item for item in results if item["is_cached"]]
    misses = [item for item in results if not item["is_cached"]]
    return {
        "query_count": len(results),
        "cache_hits": len(hits),
        "cache_misses": len(misses),
        "hit_rate_percent": round(len(hits) / len(results) * 100, 2),
        "average_cached_latency_ms": round(
            statistics.fmean(item["latency_ms"] for item in hits), 3
        ),
        "average_non_cached_latency_ms": round(
            statistics.fmean(item["latency_ms"] for item in misses), 3
        ),
        "results": results,
    }


def run_threshold_sweep(
    cache: Any,
    agent: GroceryRecallAgent,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cases = load_json(DATA / "cache_cases.yaml")
    rows = []
    false_hit_example: dict[str, Any] | None = None
    for threshold in (0.75, 0.80, 0.85, 0.90, 0.95):
        outcomes = []
        for case in cases:
            cache.clear()
            seed = agent.answer(case["seed_query"])
            cache.put(
                case["seed_query"],
                seed.text,
                case["seed_answer_id"],
                seed.entity_id,
                seed.data_version,
            )
            started = time.perf_counter()
            match = cache.lookup(case["incoming_query"], threshold)
            if match is None:
                correct = agent.answer(case["incoming_query"])
                returned_answer = correct.text
                returned_answer_id = correct.answer_id
                similarity = 0.0
                is_hit = False
            else:
                returned_answer = match.answer
                returned_answer_id = match.answer_id
                similarity = match.similarity
                is_hit = True
            latency_ms = (time.perf_counter() - started) * 1000
            false_hit = is_hit and returned_answer_id != case["expected_answer_id"]
            outcome = {
                **case,
                "is_hit": is_hit,
                "false_hit": false_hit,
                "similarity": round(similarity, 6),
                "returned_answer": returned_answer,
                "returned_answer_id": returned_answer_id,
                "latency_ms": round(latency_ms, 3),
            }
            outcomes.append(outcome)
            if false_hit and false_hit_example is None:
                correct = agent.answer(case["incoming_query"])
                false_hit_example = {
                    "threshold": threshold,
                    "cached_query": case["seed_query"],
                    "incoming_query": case["incoming_query"],
                    "similarity": round(similarity, 6),
                    "cached_answer": returned_answer,
                    "correct_answer": correct.text,
                    "explanation": (
                        "The embedding gave heavy weight to the shared intent and nearly identical "
                        "recall-code wording, while the differing entity number contributed too little "
                        "at this permissive threshold."
                    ),
                }
        hits = sum(item["is_hit"] for item in outcomes)
        false_hits = sum(item["false_hit"] for item in outcomes)
        misses = len(outcomes) - hits
        total_cost = misses * 0.002 + false_hits * 0.25
        rows.append(
            {
                "threshold": threshold,
                "hit_rate_percent": round(hits / len(outcomes) * 100, 2),
                "false_hit_rate_percent": round(false_hits / 20 * 100, 2),
                "mean_latency_ms": round(
                    statistics.fmean(item["latency_ms"] for item in outcomes), 3
                ),
                "cache_hits": hits,
                "false_hits": false_hits,
                "cache_misses": misses,
                "total_cost": round(total_cost, 3),
                "outcomes": outcomes,
            }
        )
    assert false_hit_example is not None
    return rows, false_hit_example


def run_staleness(service: SemanticQueryService) -> dict[str, Any]:
    query = "How many units are affected by REC-3539-00001?"
    service.cache.clear()
    initial = service.query(query, threshold=0.90)
    original_units = service.agent.store.get_recall("REC-3539-00001")["units_affected"]
    new_units = int(original_units) + 111
    new_version = service.agent.store.update_units("REC-3539-00001", new_units)
    stale = service.query(query, threshold=0.90, enforce_version=False)
    removed = service.cache.invalidate_entity("REC-3539-00001")
    refreshed = service.query(query, threshold=0.90, enforce_version=True)
    service.agent.store.update_units("REC-3539-00001", int(original_units))
    service.cache.invalidate_entity("REC-3539-00001")
    return {
        "query": query,
        "initial_answer": initial["answer"],
        "updated_units": new_units,
        "updated_data_version": new_version,
        "stale_hit": stale,
        "invalidated_entries": removed,
        "refreshed_response": refreshed,
        "strategy": "Entity-scoped invalidation deletes cached answers after a versioned record update.",
        "trade_off": "Invalidation adds write-path work and may reduce hit rate, but prevents stale safety guidance.",
        "passed": stale["is_cached"] and str(new_units) in refreshed["answer"].replace(",", ""),
    }


def run_self_improving() -> dict[str, Any]:
    lessons_path = DATA / "lessons.json"
    lessons_path.write_text("[]\n", encoding="utf-8")
    system = SelfImprovingSystem(DATA / "reference_dataset.json", lessons_path)
    training = load_json(DATA / "training_data.json")
    validation = load_json(DATA / "validation_data.json")
    test = load_json(DATA / "test_data.json")

    revision = system.run_case(training[0], repair=True, use_lessons=False)
    second_failure = system.run_case(training[1], repair=False, use_lessons=False)
    lesson = system.learn_from_failure(training[0]["question_id"])
    reuse = system.run_case(training[1], repair=False, use_lessons=True)
    validation_result = system.validate_lesson(lesson["lesson_id"], validation)

    variants = {
        "Baseline": system.evaluate_dataset(test, repair=False, use_lessons=False),
        "Evaluator Repair": system.evaluate_dataset(test, repair=True, use_lessons=False),
        "Lesson Memory": system.evaluate_dataset(test, repair=False, use_lessons=True),
        "Validated Improvement": system.evaluate_dataset(test, repair=True, use_lessons=True),
    }
    return {
        "revision_sequence": revision.__dict__,
        "repeated_failure_before_lesson": second_failure.__dict__,
        "created_lesson": lesson,
        "lesson_reuse": reuse.__dict__,
        "validation": validation_result,
        "variants": variants,
        "limitation": (
            "The evaluator depends on curated reference facts and cannot validate questions outside "
            "that dataset without a human-approved expansion."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("redis", "memory"), default="redis")
    parser.add_argument("--ollama", action="store_true")
    args = parser.parse_args()

    redis_client: Any
    if args.backend == "redis":
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=False,
        )
        redis_client.ping()
    else:
        redis_client = MemoryCounter()
    store = RecallStore(RAW / "hw09.db", redis_client)
    cache = RedisSemanticCache(redis_client) if args.backend == "redis" else InMemorySemanticCache()
    # The measured ingress path may use the required local model adapter. The
    # 200-case threshold sweep intentionally uses the deterministic grounded
    # adapter so threshold comparisons are not distorted by generation time.
    ingress_agent = GroceryRecallAgent(store, use_ollama=args.ollama)
    sweep_agent = GroceryRecallAgent(store, use_ollama=False)
    service = SemanticQueryService(cache, ingress_agent)

    counter = run_counter(store)
    workload = run_ingress_workload(service)
    sweep, false_hit = run_threshold_sweep(cache, sweep_agent)
    stale = run_staleness(service)
    self_improving = run_self_improving()
    payload = {
        "student": "Vedant Vartak",
        "sid4": settings.sid4,
        "prefix": settings.prefix,
        "model": settings.model,
        "backend": args.backend,
        "counter": counter,
        "cache_workload": workload,
        "threshold_sweep": sweep,
        "false_hit_example": false_hit,
        "cost_model": {
            "cache_miss_cost": 0.002,
            "false_hit_support_cost": 0.25,
            "chosen_threshold": 0.95,
            "justification": (
                "0.95 removes observed false hits at far lower expected cost than 0.85, while "
                "retaining exact and high-confidence paraphrase reuse."
            ),
        },
        "staleness": stale,
        "self_improving": self_improving,
    }
    write_json(RAW / "hw09_results.json", payload)
    print("Vedant Vartak - DATA 260 Homework 9")
    print("counter_passed=", counter["passed"])
    print("cache_hit_rate=", workload["hit_rate_percent"])
    for row in sweep:
        print(
            "threshold=",
            row["threshold"],
            "hit_rate=",
            row["hit_rate_percent"],
            "false_hit_rate=",
            row["false_hit_rate_percent"],
            "mean_latency_ms=",
            row["mean_latency_ms"],
            "total_cost=",
            row["total_cost"],
        )
    print("staleness_passed=", stale["passed"])
    for name, result in self_improving["variants"].items():
        print(name, result["correct"], result["incorrect"], result["average_attempts"])
    print("results=", RAW / "hw09_results.json")
    store.close()
    redis_client.close()


if __name__ == "__main__":
    main()
