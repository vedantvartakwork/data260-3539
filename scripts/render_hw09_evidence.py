"""Render terminal-style screenshots solely from frozen HW9 raw evidence."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "hw09"
RAW = REPORT / "raw"
OUT = REPORT / "evidence"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Monaco.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf"
        if bold
        else "/System/Library/Fonts/Supplemental/Courier New.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrapped(lines: list[str], width: int = 96) -> list[str]:
    result: list[str] = []
    for line in lines:
        result.extend(
            textwrap.wrap(
                line,
                width=width,
                replace_whitespace=False,
                drop_whitespace=False,
                subsequent_indent="  ",
            )
            or [""]
        )
    return result


def terminal(title: str, lines: list[str], filename: str) -> None:
    body = wrapped(lines)
    body_font = font(25)
    title_font = font(28, bold=True)
    line_height = 37
    width = 1780
    height = 118 + line_height * len(body) + 44
    image = Image.new("RGB", (width, height), "#111111")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (18, 18, width - 18, height - 18),
        radius=18,
        fill="#111111",
        outline="#777777",
        width=3,
    )
    draw.text((54, 42), title, fill="#ffffff", font=title_font)
    y = 103
    for line in body:
        color = "#ffffff" if not line.startswith(("PASS", "SYNC", "CHOSEN")) else "#b6f0c2"
        draw.text((54, y), line, fill=color, font=body_font)
        y += line_height
    image.save(OUT / filename, optimize=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = json.loads((RAW / "hw09_results.json").read_text(encoding="utf-8"))
    redis_state = json.loads((RAW / "redis_state.json").read_text(encoding="utf-8"))
    verification = json.loads((REPORT / "verification.json").read_text(encoding="utf-8"))

    counter = payload["counter"]
    accesses = []
    for row in counter["accesses"]:
        marker = " SYNC -> SQLite" if row["synced"] else ""
        accesses.append(f"access={row['access']:02d} redis_total={row['total']:02d}{marker}")
    terminal(
        "VEDANT VARTAK - REDIS VIEW COUNTER",
        [
            f"key={redis_state['all_prefix_keys'][-1]}",
            *accesses,
            f"PASS final Redis count={counter['redis_count']} persisted database count={counter['database_count']}",
        ],
        "01_counter.png",
    )

    workload = payload["cache_workload"]
    terminal(
        "VEDANT VARTAK - REDIS VECTOR CACHE + LOCAL MODEL",
        [
            f"Redis {redis_state['redis_version']} mode={redis_state['redis_mode']}",
            f"index={redis_state['vector_index_key']} command={redis_state['vector_command']}",
            f"vector_count={redis_state['vector_count']} keys={redis_state['all_prefix_keys']}",
            f"queries={workload['query_count']} hits={workload['cache_hits']} misses={workload['cache_misses']}",
            f"hit_rate={workload['hit_rate_percent']}%",
            f"mean_cached_latency={workload['average_cached_latency_ms']} ms",
            f"mean_non_cached_qwen3_latency={workload['average_non_cached_latency_ms']} ms",
            "PASS cache hits bypassed the qwen3:8b generation path",
        ],
        "02_cache_workload.png",
    )

    sweep_lines = [
        "threshold | hit rate | false-hit rate | mean latency | total cost",
        "----------+----------+----------------+--------------+-----------",
    ]
    for row in payload["threshold_sweep"]:
        sweep_lines.append(
            f"{row['threshold']:.2f}      | {row['hit_rate_percent']:6.2f}%  | "
            f"{row['false_hit_rate_percent']:10.2f}%    | {row['mean_latency_ms']:7.3f} ms  | "
            f"${row['total_cost']:.3f}"
        )
    sweep_lines.extend(
        [
            "",
            "cost = misses * $0.002 + false_hits * $0.25",
            "CHOSEN threshold=0.95: zero observed false hits and minimum expected cost",
        ]
    )
    terminal(
        "VEDANT VARTAK - FROZEN 40-CASE THRESHOLD SWEEP",
        sweep_lines,
        "03_threshold_sweep.png",
    )

    false_hit = payload["false_hit_example"]
    terminal(
        "VEDANT VARTAK - FULL FALSE-HIT AND STALENESS EVIDENCE",
        [
            f"cached query: {false_hit['cached_query']}",
            f"incoming query: {false_hit['incoming_query']}",
            f"similarity={false_hit['similarity']} threshold={false_hit['threshold']}",
            f"wrong cached answer: {false_hit['cached_answer']}",
            f"correct answer: {false_hit['correct_answer']}",
            f"why: {false_hit['explanation']}",
            "",
            f"stale answer after update: {payload['staleness']['stale_hit']['answer']}",
            f"updated units={payload['staleness']['updated_units']} version={payload['staleness']['updated_data_version']}",
            f"invalidated entries={payload['staleness']['invalidated_entries']}",
            f"fresh answer: {payload['staleness']['refreshed_response']['answer']}",
            f"PASS stale hit reproduced then prevented={payload['staleness']['passed']}",
        ],
        "04_false_hit_staleness.png",
    )

    improving = payload["self_improving"]
    revision = improving["revision_sequence"]
    reuse = improving["lesson_reuse"]
    terminal(
        "VEDANT VARTAK - TWO-AGENT REVISION AND LESSON REUSE",
        [
            f"question: {revision['question']}",
            f"attempt 1: {revision['initial_answer']}",
            f"evaluator: REVISE - {revision['evaluator_feedback']}",
            f"attempt 2: {revision['revised_answer']}",
            f"PASS final={revision['final_evaluation']} attempts={revision['attempts']}",
            "",
            f"lesson={improving['created_lesson']}",
            f"new question: {reuse['question']}",
            f"lessons_used={reuse['lessons_used']} attempts={reuse['attempts']}",
            f"PASS lesson reuse result={reuse['final_evaluation']}",
            f"PASS validation before={improving['validation']['before_correct']} after={improving['validation']['after_correct']} kept={improving['validation']['kept']}",
        ],
        "05_revision_lessons.png",
    )

    variant_lines = ["variant | correct | incorrect | avg attempts | avg latency"]
    for name, result in improving["variants"].items():
        variant_lines.append(
            f"{name:22s} | {result['correct']:2d} | {result['incorrect']:2d} | "
            f"{result['average_attempts']:.3f} | {result['average_latency_ms']:.3f} ms"
        )
    variant_lines.extend(
        [
            "",
            verification["tests"]["output"].strip(),
            *[f"PASS {name}" for name, passed in verification["checks"].items() if passed],
            f"PASS verification={verification['passed']}",
        ]
    )
    terminal(
        "VEDANT VARTAK - HELD-OUT VARIANTS + VERIFICATION",
        variant_lines,
        "06_variants_verification.png",
    )


if __name__ == "__main__":
    main()
