"""Deterministic offline tests for Homework 6."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from code.hw6.file_memory import FileMemoryManager, normalize_memory_fact
from code.hw6.memory import ChatService, DeterministicEmbedder, DeterministicModel, cosine_similarity, extract_facts
from code.hw6.repositories import InMemoryMemoryRepository
from code.hw6.routes.documents import router as document_router
from code.hw6.schemas import ChatRequest, RecallDocumentCreate, RecallDocumentUpdate


def service(repo: InMemoryMemoryRepository | None = None, **kwargs) -> ChatService:
    return ChatService(
        repo or InMemoryMemoryRepository(),
        DeterministicModel(),
        DeterministicEmbedder(),
        metrics_path=None,
        **kwargs,
    )


class HW6Tests(unittest.TestCase):
    def test_document_schema_valid_and_default(self) -> None:
        row = RecallDocumentCreate(
            title="Frozen berries recall",
            category="Produce",
            recalled_at=datetime.now(timezone.utc),
        )
        self.assertEqual(row.status.value, "active")

    def test_document_schema_rejects_missing_enum_and_type(self) -> None:
        with self.assertRaises(ValidationError):
            RecallDocumentCreate.model_validate(
                {"title": "X", "category": "Unknown", "recalled_at": "not-a-date"}
            )

    def test_document_update_requires_a_field(self) -> None:
        with self.assertRaises(ValidationError):
            RecallDocumentUpdate()

    def test_chat_request_rejects_unsafe_identifier(self) -> None:
        with self.assertRaises(ValidationError):
            ChatRequest(user_id="bad user/id", message="hello")

    def test_short_term_window_is_bounded(self) -> None:
        repo = InMemoryMemoryRepository()
        chat = service(repo, short_term_n=4, summarize_every=99)
        for index in range(4):
            result = chat.chat("vedant", "s1", f"message {index} should be remembered")
        self.assertEqual(result["memory_used"]["short_term_count"], 4)

    def test_periodic_session_summary_is_created(self) -> None:
        repo = InMemoryMemoryRepository()
        chat = service(repo, short_term_n=4, summarize_every=2)
        chat.chat("vedant", "s1", "My project uses MongoDB.")
        chat.chat("vedant", "s1", "The database is s3539_doc.")
        self.assertIsNotNone(repo.latest_summary("vedant", "session", "s1"))

    def test_episodic_fact_is_stored_and_retrieved(self) -> None:
        repo = InMemoryMemoryRepository()
        chat = service(repo, short_term_n=2, summarize_every=99)
        chat.chat("vedant", "s1", "Remember that my allergy is peanuts.")
        result = chat.chat("vedant", "s1", "What allergy should you remember?")
        facts = result["memory_used"]["episodic_facts"]
        self.assertTrue(any("peanuts" in row["fact"] for row in facts))

    def test_memory_aggregate_counts_messages(self) -> None:
        repo = InMemoryMemoryRepository()
        chat = service(repo, short_term_n=2, summarize_every=99)
        chat.chat("vedant", "s1", "Remember this fact please.")
        aggregate = repo.aggregate("vedant")
        self.assertEqual(aggregate["daily_message_counts"][0]["message_count"], 2)

    def test_cosine_and_fact_extraction(self) -> None:
        embedder = DeterministicEmbedder()
        self.assertGreater(cosine_similarity(embedder.embed("mongo database"), embedder.embed("mongo memory database")), 0)
        self.assertLessEqual(len(extract_facts("One important fact. Another fact. Third fact. Fourth fact.")), 3)

    def test_file_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agent = root / "AGENT.md"
            memory = root / "MEMORY.md"
            agent.write_text("# Rules\n- Test offline.\n", encoding="utf-8")
            memory.write_text("# Memory\n- name: Vedant\n", encoding="utf-8")
            manager = FileMemoryManager(agent, memory)
            self.assertIn("/compact", manager.command("/help", []))
            self.assertIn("Vedant", manager.command("/memory", []))
            dream = manager.command(
                "/dream",
                [{"role": "user", "content": "Remember that my project database is MongoDB."}],
            )
            self.assertIn("added 1 new fact", dream)
            self.assertIn("dream_fact_1: my project database is MongoDB.", memory.read_text(encoding="utf-8"))

    def test_document_update_exposes_required_put_route(self) -> None:
        route_methods = {
            method
            for route in document_router.routes
            if route.path == "/api/v1/documents/{document_id}"
            for method in route.methods
        }
        self.assertIn("PUT", route_methods)

    def test_compaction_merges_duplicates_and_documents_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agent = root / "AGENT.md"
            memory = root / "MEMORY.md"
            agent.write_text("# Rules\n", encoding="utf-8")
            source = ["# Memory"] + ["- name: Vedant"] * 40 + ["- window: 12", "- window: 8", "- window: 12"]
            memory.write_text("\n".join(source), encoding="utf-8")
            manager = FileMemoryManager(agent, memory)
            self.assertTrue(manager.needs_consolidation())
            result = manager.consolidate()
            self.assertLess(result["after"], 40)
            self.assertLess(len(memory.read_text(encoding="utf-8").splitlines()), 40)
            self.assertEqual(result["conflicts_resolved"], 1)
            self.assertIn("rejected '8'", memory.read_text(encoding="utf-8"))
            self.assertIn("- window: 12", memory.read_text(encoding="utf-8"))

    def test_generated_normalizer_follows_agent_rules(self) -> None:
        self.assertEqual(normalize_memory_fact(" model ", " qwen3:8b "), "- model: qwen3:8b")
        with self.assertRaises(ValueError):
            normalize_memory_fact("", "missing key")


if __name__ == "__main__":
    unittest.main()
