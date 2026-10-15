"""Durable AGENT.md and MEMORY.md support for Homework 6 Part 4."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
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
        return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]

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

        output = ["# Consolidated Homework 6 Memory", "", f"<!-- consolidated_at_utc: {datetime.now(timezone.utc).isoformat()} -->", ""]
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
            topics = ", ".join(row["content"][:45] for row in recent_messages[-4:])
            return f"Dream reflection: recent themes include {topics}. Preserve confirmed facts and revisit unresolved questions."
        return None
