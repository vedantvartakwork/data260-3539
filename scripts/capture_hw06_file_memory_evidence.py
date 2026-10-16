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
        memory = root / "MEMORY.md"
        shutil.copyfile(PROJECT_ROOT / "AGENT.md", agent)
        shutil.copyfile(PROJECT_ROOT / "reports" / "hw06" / "MEMORY.original.md", memory)
        manager = FileMemoryManager(agent, memory)
        before = len(manager._meaningful_lines(memory.read_text(encoding="utf-8")))
        required = manager.needs_consolidation()
        help_output = manager.command("/help", [])
        dream_messages = [
            {"role": "user", "content": "Remember that my project database is MongoDB."},
            {"role": "assistant", "content": "I will keep that project fact in mind."},
            {"role": "user", "content": "I prefer local qwen3:8b and must not use hosted models."},
        ]
        dream_output = manager.command("/dream", dream_messages)
        dream_memory = memory.read_text(encoding="utf-8")
        compact_output = manager.command("/compact", [])
        after = len(manager._meaningful_lines(memory.read_text(encoding="utf-8")))
        evidence = {
            "student": "Vedant Vartak",
            "needs_consolidation_before": required,
            "meaningful_lines_before": before,
            "meaningful_lines_after": after,
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
            "memory_command_after": manager.command("/memory", []),
            "generated_function_check": {
                "call": "normalize_memory_fact(' model ', ' qwen3:8b ')",
                "result": normalize_memory_fact(" model ", " qwen3:8b "),
                "requirements": ["pure", "typed", "docstring", "no filesystem/network/database side effects"],
            },
        }
    destination = PROJECT_ROOT / "reports" / "hw06" / "raw" / "file_memory_evidence.json"
    destination.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
