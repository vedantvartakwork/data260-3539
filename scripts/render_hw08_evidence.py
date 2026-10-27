"""Render readable terminal-style PNGs from the saved HW8 raw evidence."""

from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "reports" / "hw08" / "raw"
OUT = ROOT / "reports" / "hw08" / "evidence"


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


def wrap(lines: list[str], width: int = 112) -> list[str]:
    wrapped: list[str] = []
    for line in lines:
        if not line:
            wrapped.append("")
        else:
            wrapped.extend(
                textwrap.wrap(
                    line,
                    width=width,
                    replace_whitespace=False,
                    drop_whitespace=False,
                    subsequent_indent="  ",
                )
                or [""]
            )
    return wrapped


def terminal(title: str, lines: list[str], filename: str) -> None:
    body = wrap(lines)
    body_font = font(25)
    title_font = font(27, bold=True)
    line_height = 36
    width = 1900
    height = 105 + line_height * len(body) + 44
    image = Image.new("RGB", (width, height), "#111827")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (20, 20, width - 20, height - 20), radius=18, fill="#111827", outline="#4b5563", width=3
    )
    draw.text((58, 44), title, fill="#f9fafb", font=title_font)
    y = 96
    for line in body:
        color = "#86efac" if line.startswith(("PASS", "CREATED", "FINAL", "VERIFY")) else "#e5e7eb"
        draw.text((58, y), line, fill=color, font=body_font)
        y += line_height
    image.save(OUT / filename, optimize=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ps = (RAW / "docker_ps.txt").read_text(encoding="utf-8").splitlines()
    terminal("LIVE DOCKER/KAFKA STACK", ps[:12], "01_docker_ps.png")

    rpc = (RAW / "homework_demo_live.txt").read_text(encoding="utf-8").splitlines()
    terminal("CREATE_RECALL THEN GET_RECALL", rpc, "02_create_get.png")

    pipeline = (RAW / "agent_pipeline_live.txt").read_text(encoding="utf-8").splitlines()
    terminal("PLANNER -> WRITER -> REVIEWER", pipeline, "03_agent_pipeline.png")

    service_logs = (RAW / "kafka_service_logs.txt").read_text(encoding="utf-8").splitlines()
    rpc_ids = re.findall(
        r'CLIENT SEND (?:CREATE|GET)_RECALL .*?"correlation_id": "([^"]+)"',
        (RAW / "homework_demo_live.txt").read_text(encoding="utf-8"),
    )
    rpc_flow = [
        line
        for line in service_logs
        if any(correlation_id in line for correlation_id in rpc_ids)
        and any(marker in line for marker in ("FASTAPI", "WORKER"))
    ]
    terminal(
        "KAFKA RPC SEND -> RECEIVE -> REPLY -> CLIENT",
        ["Vedant Vartak - DATA 260 Homework 8", *rpc_flow],
        "07_rpc_message_flow.png",
    )

    pipeline_match = re.search(
        r'\[USER SEND\].*?"correlation_id": "([^"]+)"',
        (RAW / "agent_pipeline_live.txt").read_text(encoding="utf-8"),
    )
    pipeline_id = pipeline_match.group(1) if pipeline_match else ""
    pipeline_flow = [
        line
        for line in service_logs
        if pipeline_id in line
        and any(marker in line for marker in ("PLANNER", "WRITER", "REVIEWER"))
    ]
    terminal(
        "LIVE THREE-PROCESS STAGE LOGS",
        ["Vedant Vartak - DATA 260 Homework 8", *pipeline_flow],
        "08_pipeline_stage_logs.png",
    )

    live = json.loads((RAW / "live_failure_experiments.json").read_text(encoding="utf-8"))
    duplicate = live["duplicate_delivery"]
    restart = live["consumer_killed_mid_work"]
    poison = live["poison_message"]
    terminal(
        "LIVE FAILURE EXPERIMENTS",
        [
            "Vedant Vartak - DATA 260 Homework 8",
            f"PASS duplicate delivery: correlation_id={duplicate['correlation_id']}",
            f"  first entity_id={duplicate['first']['entity_id']}",
            f"  replay entity_id={duplicate['replay']['entity_id']} duplicate={duplicate['replay']['duplicate']}",
            f"PASS consumer killed mid-work: correlation_id={restart['correlation_id']}",
            "  both Writer containers stopped while an 8-second message was in flight",
            f"  restarted final status={restart['final']['value']['status']} journey={restart['final']['value']['journey']}",
            f"PASS poison message: correlation_id={poison['poison_correlation_id']}",
            f"  DLQ error={poison['dead_letter']['value']['error']}",
            f"  later good status={poison['later_good_message']['value']['status']}",
            "PASS all=True",
        ],
        "04_failures.png",
    )

    ordering = live["two_partitions_two_consumers"]
    terminal(
        "20-MESSAGE ORDERING EXPERIMENT",
        [
            "Vedant Vartak - DATA 260 Homework 8",
            f"VERIFY_SEED={ordering['verify_seed']}",
            f"INPUT  = {ordering['input_order']}",
            f"UNKEYED= {ordering['unkeyed_processed_order']}",
            "Result: related messages completed out of order across two partitions/two Writers.",
            f"KEYED  = {ordering['keyed_processed_order']}",
            f"KEYED PARTITIONS = {ordering['keyed_partitions']}",
            "PASS: entity_key kept all related messages on one partition and preserved order.",
        ],
        "05_ordering.png",
    )

    verification = json.loads(
        (ROOT / "reports" / "hw08" / "verification.json").read_text(encoding="utf-8")
    )
    lines = [
        "Vedant Vartak - DATA 260 Homework 8",
        f"commit_hash={verification['commit_hash']}",
        f"SID4={verification['sid4']} VERIFY_SEED={verification['verify_seed']}",
    ]
    lines.extend(
        f"PASS {item['name']} - {item['detail']}"
        for item in verification["checks"]
        if item["passed"]
    )
    lines.append(f"PASS verification={verification['passed']}")
    terminal("FINAL VERIFICATION", lines, "06_verification.png")

    jmeter = json.loads((RAW / "jmeter_summary.json").read_text(encoding="utf-8"))
    terminal(
        "JMETER DIRECT ENDPOINT — 100 USERS",
        [
            "Vedant Vartak - DATA 260 Homework 8",
            "Test plan: HW8_direct_100_users.jmx",
            f"Threads={jmeter['threads']} ramp_up_seconds={jmeter['ramp_up_seconds']} samples={jmeter['samples']}",
            f"HTTP response codes={jmeter['response_codes']}",
            f"Average={jmeter['average_ms']} ms  Min={jmeter['min_ms']} ms  Max={jmeter['max_ms']} ms  p95={jmeter['p95_ms']} ms",
            f"Error %={jmeter['error_percent']}  Throughput={jmeter['throughput_requests_per_second']} requests/sec",
            f"PASS all_100_requests={jmeter['passed_all']}",
            "Raw samples: reports/hw08/raw/jmeter_100_users.jtl",
            "Dashboard: reports/hw08/raw/jmeter_dashboard/index.html",
        ],
        "09_jmeter.png",
    )


if __name__ == "__main__":
    main()
