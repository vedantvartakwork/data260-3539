#!/usr/bin/env python3
"""Render readable terminal-style evidence from the frozen HW10 artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "hw10"
RAW = REPORT / "raw"
EVIDENCE = REPORT / "evidence"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = [
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        if bold
        else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for name in names:
        path = Path(name)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def terminal(name: str, title: str, lines: list[str]) -> None:
    width = 1800
    line_height = 34
    height = 100 + line_height * len(lines)
    image = Image.new("RGB", (width, height), "#111111")
    draw = ImageDraw.Draw(image)
    draw.text((35, 25), title, fill="white", font=font(28, True))
    for index, line in enumerate(lines):
        color = "#8ee6a3" if line.startswith("PASS") else "#f0f0f0"
        draw.text((35, 80 + index * line_height), line, fill=color, font=font(22))
    image.save(EVIDENCE / name)


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    summary = json.loads((RAW / "evaluation_summary.json").read_text(encoding="utf-8"))
    metrics = json.loads((RAW / "stage_metrics.json").read_text(encoding="utf-8"))
    verification = json.loads((REPORT / "verification.json").read_text(encoding="utf-8"))
    terminal(
        "experiment_summary.png",
        "Vedant Vartak — DATA 260 Homework 10 experiment",
        [
            "PREFIX=s3539  MODEL=qwen3:8b  VERIFY_SEED=263539",
            "PASS frozen judge cases: 20; repeat runs: 3",
            f"PASS Spearman: {summary['spearman']:.3f}",
            f"PASS mean absolute difference: {summary['mean_absolute_difference']:.3f}",
            f"PASS changed-score frequency: {summary['changed_score_frequency']:.1%}",
            f"PASS confirmed cache misses: {metrics['confirmed_cache_misses']}",
            f"PASS cache-served count during miss run: {metrics['cache_served_count']}",
            f"PASS miss E2E p50/p95: {metrics['e2e_p50_ms']:.3f} / {metrics['e2e_p95_ms']:.3f} ms",
            f"PASS dominant stage: {metrics['dominant_stage']}",
            f"dataset_commit={summary['dataset_commit']}",
        ],
    )
    test_line = verification["tests"]["stdout"].replace("\n", " | ")
    terminal(
        "verification_terminal.png",
        "HW10 final verification",
        [
            f"status={verification['status']}",
            f"implementation_commit={verification['implementation_commit']}",
            f"resolved_hw10_tag={verification['resolved_hw10_tag']}",
            f"PASS ruff: {verification['ruff']['passed']}",
            f"PASS tests: {test_line}",
            *[
                f"{'PASS' if check['passed'] else 'FAIL'} {check['name']}"
                for check in verification["checks"]
            ],
        ],
    )


if __name__ == "__main__":
    main()
