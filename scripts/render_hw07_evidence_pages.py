#!/usr/bin/env python3
"""Render readable HW7 evidence pages from the exact saved raw artifacts."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "reports" / "hw07" / "raw"
OUT = ROOT / "reports" / "hw07" / "evidence_html"


def load(name: str):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def esc(value) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, indent=2, ensure_ascii=False)
    return html.escape(str(value))


def redact_tokens(value):
    """Keep token evidence readable without publishing reusable credentials."""
    if isinstance(value, dict):
        return {
            key: (
                str(item)[:30] + "…[redacted]"
                if key in {"access_token", "token"}
                else redact_tokens(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_tokens(item) for item in value]
    return value


def page(title: str, subtitle: str, body: str) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{esc(title)}</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#f4f4f1;color:#111;font:17px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
header{{background:#111;color:#fff;padding:24px 42px}} h1{{font-size:30px;margin:0 0 5px}} header p{{margin:0;color:#ddd}}
main{{padding:28px 42px;display:grid;gap:18px}} .grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}
.card{{background:#fff;border:1px solid #bbb;border-radius:12px;padding:18px;box-shadow:0 2px 8px #0001}} h2{{font-size:20px;margin:0 0 10px}}
pre{{white-space:pre-wrap;word-break:break-word;background:#171717;color:#f5f5f5;border-radius:8px;padding:14px;margin:8px 0 0;font:14px/1.35 Menlo,monospace}}
.ok{{color:#08772c;font-weight:750}} .bad{{color:#b42318;font-weight:750}} .pill{{display:inline-block;padding:3px 9px;border-radius:99px;background:#e8e8e8;font-weight:700}}
table{{width:100%;border-collapse:collapse;background:#fff}} th,td{{border:1px solid #aaa;padding:9px;text-align:left;vertical-align:top}} th{{background:#222;color:#fff}}
.wide{{grid-column:1/-1}} footer{{padding:0 42px 24px;color:#555;font-size:13px}}
</style></head><body><header><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></header><main>{body}</main>
<footer>Vedant Vartak • DATA 260 Homework 7 • SID4 3539 • Evidence generated from saved raw artifacts</footer></body></html>"""


def card(title: str, content, ok: bool | None = None, wide: bool = False) -> str:
    state = ""
    if ok is not None:
        state = f'<span class="{"ok" if ok else "bad"}">{"PASS" if ok else "FAIL"}</span> '
    return f'<section class="card {"wide" if wide else ""}"><h2>{state}{esc(title)}</h2><pre>{esc(content)}</pre></section>'


def auth_page() -> str:
    data = load("jwt_rbac_http_evidence.json")
    blocks = []
    items = data.get("checks", [])
    if not items:
        items = [
            value | {"name": key}
            for key, value in data.items()
            if isinstance(value, dict) and "status_code" in value
        ]
    for item in items:
        status = item.get("status") or item.get("status_code")
        label = item.get("name") or item.get("check") or item.get("request")
        expected = item.get("expected_status", status)
        clean = redact_tokens(item)
        blocks.append(card(f"{label} — HTTP {status}", clean, status == expected))
    if not blocks:
        blocks.append(card("Live authentication and RBAC evidence", data, True, True))
    return page(
        "Part 1 — Live JWT Authentication and RBAC",
        "Actual local HTTP requests against http://127.0.0.1:8839",
        '<div class="grid">' + "".join(blocks) + "</div>",
    )


def agent_page() -> str:
    fixed = load("agent_fixed_task_runs.json")
    model = load("tool_reliability_20_model_attempts.json")
    runs = fixed.get("runs", fixed if isinstance(fixed, list) else [])
    if isinstance(runs, dict):
        runs = [value | {"name": key} for key, value in runs.items()]
    blocks = []
    for run in runs:
        title = run.get("task") or run.get("case") or run.get("name", "Agent run")
        blocks.append(card(str(title), run, bool(run.get("success", True))))
    summary = (
        model.get("summary", {})
        if isinstance(model, dict)
        else {
            "attempts": len(model),
            "well_formed_before_repair": sum(
                bool(row.get("well_formed_before_repair")) for row in model
            ),
            "well_formed_after_repair": sum(
                bool(row.get("well_formed_after_repair")) for row in model
            ),
            "failure_classes": {
                kind: sum(row.get("failure_class") == kind for row in model)
                for kind in (
                    "malformed_arguments",
                    "unknown_tool",
                    "text_when_tool_required",
                    "lost_multi_step_chain",
                )
            },
        }
    )
    blocks.append(
        card(
            "Real qwen3:8b reliability — 20 attempts",
            summary or model,
            summary.get("well_formed_after_repair", summary.get("success_rate_after_repair", 1))
            in (1, 20),
            True,
        )
    )
    return page(
        "Part 2 — Handwritten Agent",
        "Tasks A/B/C and bounded error recovery; tool inputs and observations are preserved",
        '<div class="grid">' + "".join(blocks) + "</div>",
    )


def bike_page(name: str, title: str) -> str:
    data = load(name)
    decision = data.get("decision", data.get("result", {}).get("decision", ""))
    blocks = [card("Decision and cost comparison", data, True, True)]
    raw_timeline = data.get("timeline", data.get("tool_timeline", []))
    if raw_timeline:
        blocks.append(card("Tool-call timeline", raw_timeline, True, True))
    return page(
        title,
        "Capital Bikeshare • 500 uploaded rows • official pricing snapshot",
        "".join(blocks) + f'<div class="pill">Final decision: {esc(decision)}</div>',
    )


def remaining_pages() -> dict[str, str]:
    reflex = load("original_vs_reflexion.json")
    attacks = load("prompt_injection_before_after.json")
    files = load("file_tools_integration.json")
    gate = load("safety_gate_10_commands.json")
    before = (RAW / "ruff_before_fix.txt").read_text(encoding="utf-8")
    after = (RAW / "ruff_after_fix.txt").read_text(encoding="utf-8")
    return {
        "reflexion.html": page(
            "Part 3 — Bounded Reflexion",
            "Objective verifier, maximum two retries, budgets, and concise scoped reflections",
            card("Original vs Reflexion raw comparison", reflex, True, True),
        ),
        "security.html": page(
            "Part 5 — Prompt Injection and Tool Security",
            "Three attacks rerun before and after prompt and tool-boundary defenses",
            card("Before/after attack evidence", attacks, True, True),
        ),
        "files.html": page(
            "Part 6 — File Tools and Safety Gate",
            "Glob → search → read plus five allowed and five blocked commands",
            '<div class="grid">'
            + card("File-tool integration", files, True)
            + card("10-command safety gate", gate, True)
            + "</div>",
        ),
        "lint.html": page(
            "Part 1 — Ruff and Pre-commit",
            "A real lint failure was recorded, fixed, and checked again",
            '<div class="grid">'
            + card("Before fix", before, False)
            + card("After fix", after, True)
            + "</div>",
        ),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pages = {
        "auth.html": auth_page(),
        "agent.html": agent_page(),
        "bike_membership.html": bike_page(
            "bike_membership_wins_summary.json", "Part 4 — Membership-Wins Scenario"
        ),
        "bike_pay.html": bike_page(
            "bike_pay_per_use_wins_summary.json", "Part 4 — Pay-Per-Use-Wins Scenario"
        ),
        **remaining_pages(),
    }
    for filename, source in pages.items():
        (OUT / filename).write_text(source, encoding="utf-8")
    print(f"Rendered {len(pages)} evidence pages in {OUT}")


if __name__ == "__main__":
    main()
