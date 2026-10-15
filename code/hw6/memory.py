"""Long-term chat memory, episodic retrieval, and per-turn telemetry."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from code.hw6.config import PROJECT_ROOT, settings


class Completion(Protocol):
    content: str
    input_tokens: int
    output_tokens: int
    model: str


class ModelAdapter(Protocol):
    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> Completion: ...


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class SentenceTransformerEmbedder:
    """Lazy local embedding adapter; no network service is called at runtime."""

    def __init__(self, model_name: str = settings.embedding_model) -> None:
        self.model_name = model_name
        self._model: Any = None

    def embed(self, text: str) -> list[float]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self.model_name,
                cache_folder=str(PROJECT_ROOT / ".cache" / "huggingface"),
            )
        vector = self._model.encode(text, normalize_embeddings=True)
        return [float(value) for value in vector]


class DeterministicEmbedder:
    """Small offline embedder for repeatable unit tests."""

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            vector[int.from_bytes(digest[:2], "big") % self.dimensions] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    denominator = math.sqrt(sum(v * v for v in left)) * math.sqrt(sum(v * v for v in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0


def extract_facts(message: str) -> list[tuple[str, float]]:
    """Extract up to three short episodic facts from an incoming message."""
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", message) if part.strip()]
    facts: list[tuple[str, float]] = []
    for sentence in sentences:
        if len(sentence) < 8:
            continue
        lower = sentence.lower()
        importance = 0.9 if any(word in lower for word in ("remember", "prefer", "deadline", "allergy", "rec-")) else 0.65
        facts.append((sentence[:240], importance))
        if len(facts) == 3:
            break
    return facts


def _summary_text(messages: list[dict[str, Any]], limit: int = 900) -> str:
    """Create compact bullet memory without making an extra model request."""
    chunks: list[str] = []
    for row in messages:
        bullet = f"- {row['role'].title()}: {row['content']}"
        if bullet not in chunks:
            chunks.append(bullet)
    selected = chunks[-12:]
    while len("\n".join(selected)) > limit and len(selected) > 1:
        selected.pop(0)
    text = "\n".join(selected)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _token_count(text: str) -> int:
    """Return a deterministic local token estimate for prompt components."""
    return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))


@dataclass
class SimpleCompletion:
    content: str
    input_tokens: int
    output_tokens: int
    model: str = "offline-deterministic"


class DeterministicModel:
    """Offline stand-in used only by tests and reproducible experiments."""

    def complete(self, messages: list[dict[str, str]], **_: Any) -> SimpleCompletion:
        last = messages[-1]["content"]
        reply = f"I understand and will remember: {last[:180]}"
        input_tokens = max(1, sum(len(item["content"].split()) for item in messages))
        return SimpleCompletion(reply, input_tokens, max(1, len(reply.split())))


class ChatService:
    """Orchestrates short-, summary-, episodic-, and file-backed memory."""

    def __init__(
        self,
        repository: Any,
        model: ModelAdapter,
        embedder: Embedder,
        *,
        short_term_n: int = settings.short_term_n,
        summarize_every: int = settings.summarize_every_user_messages,
        episodic_top_k: int = settings.episodic_top_k,
        metrics_path: Path | None = settings.metrics_path,
        file_memory: Any | None = None,
    ) -> None:
        self.repository = repository
        self.model = model
        self.embedder = embedder
        self.short_term_n = short_term_n
        self.summarize_every = summarize_every
        self.episodic_top_k = episodic_top_k
        self.metrics_path = metrics_path
        self.file_memory = file_memory

    def _retrieve_episodes(self, user_id: str, message: str) -> list[dict[str, Any]]:
        query = self.embedder.embed(message)
        ranked = []
        for episode in self.repository.episodes(user_id, limit=100):
            score = cosine_similarity(query, episode.get("embedding", []))
            ranked.append({**episode, "similarity": round(score, 6)})
        return sorted(ranked, key=lambda row: (row["similarity"], row["importance"]), reverse=True)[: self.episodic_top_k]

    def _system_prompt(
        self,
        session_summary: str | None,
        lifetime_summary: str | None,
        episodes: list[dict[str, Any]],
    ) -> str:
        parts = ["You are a precise local assistant. Use remembered facts only when relevant."]
        if self.file_memory is not None:
            parts.append(self.file_memory.prompt_context())
        if lifetime_summary:
            parts.append(f"Lifetime summary: {lifetime_summary}")
        if session_summary:
            parts.append(f"Session summary: {session_summary}")
        if episodes:
            parts.append("Relevant episodic facts:\n" + "\n".join(f"- {item['fact']}" for item in episodes))
        return "\n\n".join(parts)

    def _record_metrics(self, row: dict[str, Any]) -> None:
        if self.metrics_path is None:
            return
        self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
        with self.metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, default=str) + "\n")

    def chat(self, user_id: str, session_id: str, message: str) -> dict[str, Any]:
        if message.startswith("/") and self.file_memory is not None:
            command_reply = self.file_memory.command(
                message, self.repository.messages(user_id, session_id=session_id, limit=20)
            )
            if command_reply is not None:
                return {
                    "user_id": user_id,
                    "session_id": session_id,
                    "reply": command_reply,
                    "memory_used": {"short_term_count": 0, "short_term_messages": [], "session_summary": None, "lifetime_summary": None, "episodic_facts": []},
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "latency_ms": 0.0, "model": "command"},
                }

        started = time.perf_counter()
        user_row = self.repository.add_message(user_id, session_id, "user", message)
        short_term = self.repository.messages(
            user_id,
            session_id=session_id,
            limit=self.short_term_n,
            before_id=user_row["id"],
        )
        session_row = self.repository.latest_summary(user_id, "session", session_id)
        lifetime_row = self.repository.latest_summary(user_id, "user")
        session_summary = session_row["text"] if session_row else None
        lifetime_summary = lifetime_row["text"] if lifetime_row else None
        episodes = self._retrieve_episodes(user_id, message)

        system_prompt = self._system_prompt(session_summary, lifetime_summary, episodes)
        model_messages = [{"role": "system", "content": system_prompt}]
        model_messages.extend({"role": row["role"], "content": row["content"]} for row in short_term)
        model_messages.append({"role": "user", "content": message})

        completion = self.model.complete(model_messages, temperature=0.2)
        self.repository.add_message(user_id, session_id, "assistant", completion.content)

        for fact, importance in extract_facts(message):
            self.repository.add_episode(user_id, session_id, fact, importance, self.embedder.embed(fact))

        user_count = self.repository.user_message_count(user_id, session_id)
        if user_count % self.summarize_every == 0:
            current = self.repository.messages(user_id, session_id=session_id, limit=30)
            self.repository.add_summary(user_id, session_id, "session", _summary_text(current))
        if user_count % (self.summarize_every * 3) == 0:
            recent = self.repository.recent_summaries(user_id, limit=10)
            if recent:
                text = " || ".join(row["text"] for row in reversed(recent))[-1200:]
                self.repository.add_summary(user_id, None, "user", text)

        components = {
            "system": _token_count(system_prompt),
            "long_term": _token_count((session_summary or "") + " " + (lifetime_summary or "")),
            "short_term": sum(_token_count(row["content"]) for row in short_term),
            "episodes": sum(_token_count(row["fact"]) for row in episodes),
        }
        latency_ms = (time.perf_counter() - started) * 1000
        metrics = {
            "user_id": user_id,
            "session_id": session_id,
            "short_term_n": self.short_term_n,
            "prompt_tokens": completion.input_tokens,
            "completion_tokens": completion.output_tokens,
            "component_tokens": components,
            "latency_ms": round(latency_ms, 3),
            "model": completion.model,
        }
        self._record_metrics(metrics)
        return {
            "user_id": user_id,
            "session_id": session_id,
            "reply": completion.content,
            "memory_used": {
                "short_term_count": len(short_term),
                "short_term_messages": [{"role": row["role"], "content": row["content"]} for row in short_term],
                "session_summary": session_summary,
                "lifetime_summary": lifetime_summary,
                "episodic_facts": [{"fact": row["fact"], "importance": row["importance"], "similarity": row["similarity"]} for row in episodes],
            },
            "usage": {"prompt_tokens": completion.input_tokens, "completion_tokens": completion.output_tokens, "latency_ms": round(latency_ms, 3), "model": completion.model},
        }
