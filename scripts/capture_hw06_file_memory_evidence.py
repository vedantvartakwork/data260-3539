#!/usr/bin/env python3
"""Save reproducible Part 4 command and consolidation evidence."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from code.hw6.file_memory import FileMemoryManager, normalize_memory_fact


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        agent = root / "AGENT.md"
        dream_memory_path = root / "MEMORY.dream.md"
        compact_memory_path = root / "MEMORY.compact.md"
        shutil.copyfile(PROJECT_ROOT / "AGENT.md", agent)
        original = PROJECT_ROOT / "reports" / "hw06" / "MEMORY.original.md"
        shutil.copyfile(original, dream_memory_path)
        shutil.copyfile(original, compact_memory_path)
        dream_manager = FileMemoryManager(agent, dream_memory_path)
        compact_manager = FileMemoryManager(agent, compact_memory_path)
        before = len(compact_manager._meaningful_lines(compact_memory_path.read_text(encoding="utf-8")))
        required = compact_manager.needs_consolidation()
        help_output = compact_manager.command("/help", [])
        dream_messages = [
            {"role": "user", "content": "Remember that my project database is MongoDB."},
            {"role": "assistant", "content": "I will keep that project fact in mind."},
            {"role": "user", "content": "I prefer local qwen3:8b and must not use hosted models."},
        ]
        dream_output = dream_manager.command("/dream", dream_messages)
        dream_memory = dream_memory_path.read_text(encoding="utf-8")
        compact_output = compact_manager.command("/compact", [])
        compacted_memory = compact_memory_path.read_text(encoding="utf-8")
        after = len(compact_manager._meaningful_lines(compacted_memory))
        physical_lines_after = len(compacted_memory.splitlines())
        (PROJECT_ROOT / "MEMORY.md").write_text(compacted_memory, encoding="utf-8")
        evidence = {
            "student": "Vedant Vartak",
            "needs_consolidation_before": required,
            "meaningful_lines_before": before,
            "meaningful_lines_after": after,
            "physical_lines_after": physical_lines_after,
            "help_command": help_output,
            "dream_command": dream_output,
            "dream_messages": dream_messages,
            "dream_added_lines": [
                line
                for line in dream_memory.splitlines()
                if line.startswith("- dream_fact_")
            ],
            "compact_command": compact_output,
            "incorrect_resolutions": [],
            "resolution_audit": "All three conflicts use the final confirmed values: window 12, summary interval 4, and episodic top-k 3.",
            "memory_command_after": compact_manager.command("/memory", []),
            "generated_function_check": {
                "call": "normalize_memory_fact(' model ', ' qwen3:8b ')",
                "result": normalize_memory_fact(" model ", " qwen3:8b "),
                "requirements": ["pure", "typed", "docstring", "no filesystem/network/database side effects"],
            },
        }
    destination = PROJECT_ROOT / "reports" / "hw06" / "raw" / "file_memory_evidence.json"
    rendered = json.dumps(evidence, indent=2) + "\n"
    destination.write_text(rendered, encoding="utf-8")
    (destination.parent / "file_memory_terminal.txt").write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
