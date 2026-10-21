"""Sandboxed file tools and a pure-Python command safety gate."""

from __future__ import annotations

import difflib
import glob
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

SAFE_PREFIXES = ("pwd", "ls", "find", "rg", "grep", "head", "tail", "wc", "python -m compileall")
DESTRUCTIVE_PATTERNS = (
    re.compile(r"(^|\s)(rm|find\s+\S+\s+-delete)\b.*(-r|-R|--recursive|-delete)"),
    re.compile(r"(^|\s)(sudo|su)\b"),
    re.compile(r"(^|\s)(chmod|chown|chgrp)\b"),
    re.compile(r"(^|\s)(dd|shred)\b.*(/dev/|of=/dev/)"),
    re.compile(r"(^|\s)(mkfs|newfs|diskutil\s+erase)\b"),
    re.compile(r"(^|\s)(>|>>|tee)\s*/(?!tmp(?:/|\s|$))"),
)


def _inside(root: Path, candidate: Path) -> Path:
    root_resolved = root.resolve()
    resolved = candidate.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ValueError("path leaves the course sandbox")
    return resolved


def read_file(path: str | Path, *, sandbox: str | Path, max_lines: int = 200) -> str:
    target = _inside(Path(sandbox), Path(sandbox) / path)
    return "".join(target.read_text(encoding="utf-8").splitlines(keepends=True)[:max_lines])


def write_file(path: str | Path, content: str, *, sandbox: str | Path) -> dict[str, Any]:
    target = _inside(Path(sandbox), Path(sandbox) / path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": str(target), "bytes": len(content.encode())}


def edit_file(path: str | Path, old: str, new: str, *, sandbox: str | Path) -> dict[str, Any]:
    target = _inside(Path(sandbox), Path(sandbox) / path)
    before = target.read_text(encoding="utf-8")
    if old not in before:
        raise ValueError("edit target text was not found")
    after = before.replace(old, new, 1)
    target.write_text(after, encoding="utf-8")
    diff = "".join(
        difflib.unified_diff(
            before.splitlines(True), after.splitlines(True), fromfile=str(path), tofile=str(path)
        )
    )
    return {"path": str(target), "diff": "\n".join(diff.splitlines()[:20])}


def glob_files(pattern: str, *, sandbox: str | Path) -> list[str]:
    root = Path(sandbox).resolve()
    matches = []
    for raw in glob.glob(str(root / pattern), recursive=True):
        target = _inside(root, Path(raw))
        if target.is_file():
            matches.append(str(target.relative_to(root)))
    return sorted(matches)


def search_in_files(
    query: str, *, sandbox: str | Path, file_pattern: str = "**/*"
) -> list[dict[str, Any]]:
    results = []
    for relative in glob_files(file_pattern, sandbox=sandbox):
        for number, line in enumerate(
            read_file(relative, sandbox=sandbox, max_lines=10_000).splitlines(), 1
        ):
            if query in line:
                results.append({"path": relative, "line": number, "text": line})
    return results


def is_destructive(command: str) -> bool:
    normalized = " ".join(command.strip().split())
    return any(pattern.search(normalized) for pattern in DESTRUCTIVE_PATTERNS)


def confirm_bash(command: str, auto_approve: bool = False) -> dict[str, Any]:
    """Return an observable allow/block decision without executing the command."""
    if is_destructive(command):
        if auto_approve:
            return {
                "allowed": True,
                "reason": "explicit confirmation supplied for destructive command",
            }
        return {"allowed": False, "reason": "destructive command requires explicit confirmation"}
    if any(command.strip().startswith(prefix) for prefix in SAFE_PREFIXES):
        return {"allowed": True, "reason": "command matches SAFE_PREFIXES"}
    if auto_approve:
        return {"allowed": True, "reason": "explicit confirmation supplied"}
    return {"allowed": False, "reason": "command is not allow-listed"}


def bash(command: str, *, sandbox: str | Path, auto_approve: bool = False) -> dict[str, Any]:
    root = Path(sandbox).resolve()
    decision = confirm_bash(command, auto_approve)
    if not decision["allowed"]:
        return {**decision, "returncode": None, "stdout": "", "stderr": ""}
    # shell=False prevents redirects, command substitution, and pipelines from gaining meaning.
    completed = subprocess.run(
        shlex.split(command), cwd=root, text=True, capture_output=True, timeout=15
    )
    return {
        **decision,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
