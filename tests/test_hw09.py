"""Deterministic offline checks for Homework 9."""

from __future__ import annotations

import json
from code.hw9.agent_adapter import GroceryRecallAgent
from code.hw9.config import settings
from code.hw9.embedding import DomainEmbeddingModel, cosine_similarity
from code.hw9.query_service import SemanticQueryService
from code.hw9.self_improving import SelfImprovingSystem
from code.hw9.semantic_cache import InMemorySemanticCache
from code.hw9.store import RecallStore
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "reports" / "hw09" / "data"


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def delete(self, key: str) -> int:
        return int(self.values.pop(key, None) is not None)


@pytest.fixture
def store(tmp_path: Path) -> RecallStore:
    instance = RecallStore(tmp_path / "hw09-test.db", FakeRedis())
    yield instance
    instance.close()


def test_personal_configuration_and_prefixes() -> None:
    assert settings.sid4 == 3539
    assert settings.port_base == 8839
    assert settings.verify_seed == 263539
    assert settings.domain_id == 3
    assert settings.view_prefix.startswith("s3539:")
    assert settings.semantic_prefix.startswith("s3539:")


def test_counter_increments_every_access_and_syncs_each_tenth(store: RecallStore) -> None:
    code = "REC-3539-00001"
    values = [store.increment_recall_views(code) for _ in range(25)]
    row = store.get_recall(code)
    assert values == list(range(1, 26))
    assert row is not None
    assert row["view_count"] == 20


def test_cache_cases_are_frozen_and_balanced() -> None:
    cases = json.loads((DATA / "cache_cases.yaml").read_text(encoding="utf-8"))
    counts = {
        label: 0
        for label in ("exact_duplicate", "paraphrase", "similar_different_answer", "unrelated")
    }
    for case in cases:
        counts[case["group"]] += 1
    assert len(cases) == 40
    assert counts == {label: 10 for label in counts}


def test_domain_embedding_separates_paraphrase_from_wrong_entity() -> None:
    model = DomainEmbeddingModel()
    seed = model.embed("How many units are affected by REC-3539-00001?")
    paraphrase = model.embed("What quantity is impacted in recall REC-3539-00001?")
    wrong_entity = model.embed("How many units are affected by REC-3539-00002?")
    assert cosine_similarity(seed, paraphrase) > 0.90
    assert cosine_similarity(seed, wrong_entity) < 0.90


def test_semantic_cache_hit_and_entity_invalidation(store: RecallStore) -> None:
    cache = InMemorySemanticCache()
    service = SemanticQueryService(cache, GroceryRecallAgent(store, use_ollama=False))
    first = service.query("How many units are affected by REC-3539-00001?", threshold=0.90)
    second = service.query("What quantity is impacted in recall REC-3539-00001?", threshold=0.90)
    update = service.update_recall_and_invalidate("REC-3539-00001", 6646)
    third = service.query("How many units are affected by REC-3539-00001?", threshold=0.90)
    assert first["is_cached"] is False
    assert second["is_cached"] is True
    assert update["invalidated_entries"] == 1
    assert third["is_cached"] is False
    assert "6,646" in third["answer"]


def test_input_splits_do_not_contain_expected_answers() -> None:
    for filename in ("training_data.json", "validation_data.json", "test_data.json"):
        rows = json.loads((DATA / filename).read_text(encoding="utf-8"))
        assert rows
        assert all(set(row) == {"question_id", "question"} for row in rows)


def test_two_attempt_repair_and_lesson_reuse(tmp_path: Path) -> None:
    lessons = tmp_path / "lessons.json"
    system = SelfImprovingSystem(DATA / "reference_dataset.json", lessons)
    training = json.loads((DATA / "training_data.json").read_text(encoding="utf-8"))
    validation = json.loads((DATA / "validation_data.json").read_text(encoding="utf-8"))
    revision = system.run_case(training[0], repair=True, use_lessons=False)
    lesson = system.learn_from_failure(training[0]["question_id"])
    reuse = system.run_case(training[1], repair=False, use_lessons=True)
    validation_result = system.validate_lesson(lesson["lesson_id"], validation)
    assert revision.attempts == 2
    assert revision.final_evaluation == "PASS"
    assert reuse.attempts == 1
    assert reuse.final_evaluation == "PASS"
    assert reuse.lessons_used == [lesson["lesson_id"]]
    assert validation_result["kept"] is True


def test_test_split_remains_held_out_until_final_evaluation(tmp_path: Path) -> None:
    system = SelfImprovingSystem(DATA / "reference_dataset.json", tmp_path / "lessons.json")
    test = json.loads((DATA / "test_data.json").read_text(encoding="utf-8"))
    result = system.evaluate_dataset(test, repair=True, use_lessons=False)
    assert len(result["results"]) == len(test)
    assert result["correct"] == len(test)
    assert max(item["attempts"] for item in result["results"]) <= 2
