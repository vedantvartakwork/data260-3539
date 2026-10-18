"""Durable AGENT.md and MEMORY.md support for Homework 6 Part 4."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from code.hw6.config import PROJECT_ROOT


def normalize_memory_fact(key: str, value: str) -> str:
    """Return one canonical, Markdown-safe memory fact.

    The function is intentionally pure and typed so consolidation can be tested
    without filesystem, network, model, or database access.
    """
    clean_key = " ".join(key.strip().split()).rstrip(":")
    clean_value = " ".join(value.strip().split())
    if not clean_key or not clean_value:
        raise ValueError("memory facts require both a key and a value")
    return f"- {clean_key}: {clean_value}"


class FileMemoryManager:
    def __init__(
        self,
        agent_path: Path = PROJECT_ROOT / "AGENT.md",
        memory_path: Path = PROJECT_ROOT / "MEMORY.md",
    ) -> None:
        self.agent_path = agent_path
        self.memory_path = memory_path

    @staticmethod
    def _meaningful_lines(text: str) -> list[str]:
        return [
            line.strip()
            for line in text.splitlines()
            if line.strip()
            and not line.lstrip().startswith("#")
            and not line.lstrip().startswith("<!--")
        ]

    def prompt_context(self) -> str:
        agent = self.agent_path.read_text(encoding="utf-8") if self.agent_path.exists() else ""
        memory = self.memory_path.read_text(encoding="utf-8") if self.memory_path.exists() else ""
        return f"Durable project instructions:\n{agent}\n\nDurable user/project memory:\n{memory}"

    def needs_consolidation(self, now: datetime | None = None) -> bool:
        if not self.memory_path.exists():
            return False
        now = now or datetime.now(timezone.utc)
        count = len(self._meaningful_lines(self.memory_path.read_text(encoding="utf-8")))
        age_seconds = now.timestamp() - self.memory_path.stat().st_mtime
        return count > 40 or age_seconds > 24 * 60 * 60

    def consolidate(self) -> dict[str, Any]:
        if not self.memory_path.exists():
            return {"before": 0, "after": 0, "duplicates_removed": 0, "conflicts_resolved": 0}
        original = self.memory_path.read_text(encoding="utf-8")
        lines = self._meaningful_lines(original)
        values: dict[str, list[str]] = {}
        freeform: list[str] = []
        for line in lines:
            normalized = line[2:] if line.startswith("- ") else line
            if ":" not in normalized:
                if normalized not in freeform:
                    freeform.append(normalized)
                continue
            key, value = (part.strip() for part in normalized.split(":", 1))
            values.setdefault(key, []).append(value)

        output = ["# Consolidated Homework 6 Memory", f"<!-- consolidated_at_utc: {datetime.now(timezone.utc).isoformat()} -->"]
        conflicts = 0
        duplicates_removed = sum(len(items) - len(dict.fromkeys(items)) for items in values.values())
        for key, occurrences in values.items():
            unique_options = list(dict.fromkeys(occurrences))
            chosen = occurrences[-1]
            output.append(normalize_memory_fact(key, chosen))
            if len(unique_options) > 1:
                conflicts += 1
                rejected = "; ".join(option for option in unique_options if option != chosen)
                output.append(f"- Resolution for {key}: kept '{chosen}' as the newest value; rejected '{rejected}' as conflicting or outdated.")
        output.extend(f"- {line}" for line in freeform)
        output.append("")
        self.memory_path.write_text("\n".join(output), encoding="utf-8")
        return {
            "before": len(lines),
            "after": len(self._meaningful_lines(self.memory_path.read_text(encoding="utf-8"))),
            "duplicates_removed": max(0, duplicates_removed),
            "conflicts_resolved": conflicts,
        }

    def _dream_facts(self, recent_messages: list[dict[str, Any]]) -> list[str]:
        """Extract up to three durable facts from recent user messages.

        The extraction is intentionally local and deterministic.  It favors
        explicit memory requests and concrete configuration/preferences while
        ignoring assistant replies and short conversational filler.
        """
        candidates: list[str] = []
        cues = (
            "remember", "prefer", "my ", "project", "database", "model",
            "port", "deadline", "allergy", "must", "should", "uses ",
        )
        for row in reversed(recent_messages):
            if row.get("role", "user") != "user":
                continue
            content = " ".join(str(row.get("content", "")).split())
            for sentence in re.split(r"(?<=[.!?])\s+", content):
                fact = sentence.strip().strip("- ")
                if len(fact) < 12 or not any(cue in fact.lower() for cue in cues):
                    continue
                fact = re.sub(r"^(please\s+)?remember\s+(that\s+)?", "", fact, flags=re.IGNORECASE)
                fact = fact.rstrip(".!? ") + "."
                if fact.casefold() not in {item.casefold() for item in candidates}:
                    candidates.append(fact)
                if len(candidates) == 3:
                    return list(reversed(candidates))
        return list(reversed(candidates))

    def _append_dream_facts(self, facts: list[str]) -> int:
        if not facts:
            return 0
        existing = self.memory_path.read_text(encoding="utf-8") if self.memory_path.exists() else "# Homework 6 Memory\n"
        existing_values = {
            line.split(":", 1)[1].strip().casefold()
            for line in self._meaningful_lines(existing)
            if line.startswith("- dream_fact_") and ":" in line
        }
        used_indexes = [
            int(match.group(1))
            for match in (re.match(r"- dream_fact_(\d+):", line) for line in existing.splitlines())
            if match
        ]
        next_index = max(used_indexes, default=0) + 1
        additions: list[str] = []
        for fact in facts:
            if fact.casefold() in existing_values:
                continue
            additions.append(normalize_memory_fact(f"dream_fact_{next_index}", fact))
            existing_values.add(fact.casefold())
            next_index += 1
        if additions:
            separator = "" if existing.endswith("\n") else "\n"
            self.memory_path.write_text(existing + separator + "\n".join(additions) + "\n", encoding="utf-8")
        return len(additions)

    def command(self, command: str, recent_messages: list[dict[str, Any]]) -> str | None:
        name = command.strip().lower()
        if name == "/help":
            return "Commands: /memory shows durable memory; /compact consolidates it; /dream reflects on recent messages; /help shows this list."
        if name == "/memory":
            if not self.memory_path.exists():
                return "No durable MEMORY.md exists yet."
            count = len(self._meaningful_lines(self.memory_path.read_text(encoding="utf-8")))
            return f"Durable memory has {count} meaningful lines.\n\n{self.memory_path.read_text(encoding='utf-8')}"
        if name == "/compact":
            result = self.consolidate()
            return (
                f"Compacted MEMORY.md from {result['before']} to {result['after']} meaningful lines; "
                f"removed {result['duplicates_removed']} duplicate lines and documented {result['conflicts_resolved']} conflict resolutions."
            )
        if name == "/dream":
            if not recent_messages:
                return "Dream reflection: there are no recent messages to reflect on."
            facts = self._dream_facts(recent_messages)
            added = self._append_dream_facts(facts)
            if not facts:
                return "Dream reflection: no durable long-term facts were identified in the recent messages."
            return (
                f"Dream reflection: identified {len(facts)} useful long-term fact(s) "
                f"and added {added} new fact(s) to MEMORY.md."
            )
        return None
