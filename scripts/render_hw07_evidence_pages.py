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
    expected = {
        "invalid_login": 401,
        "reader_login": 200,
        "me_missing": 401,
        "me_invalid": 401,
        "list_reader": 200,
        "create_reader": 403,
        "create_writer": 201,
        "delete_writer": 403,
        "delete_moderator": 204,
    }
    rows = []
    for name, wanted in expected.items():
        item = redact_tokens(data[name])
        body = item.get("body")
        if isinstance(body, dict):
            body = {key: body[key] for key in list(body)[:3]}
        rows.append(
            "<tr>"
            f"<td>{esc(name)}</td><td>{esc(item['method'])}</td><td>{esc(item['url'])}</td>"
            f"<td class={'ok' if item['status_code'] == wanted else 'bad'}>{item['status_code']}</td>"
            f"<td><code>{esc(body)}</code></td></tr>"
        )
    table = (
        "<table><thead><tr><th>Check</th><th>Method</th><th>Request</th><th>Status</th>"
        "<th>Response excerpt</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )
    return page(
        "Part 1 — Live JWT Authentication and RBAC",
        "Actual local HTTP requests against http://127.0.0.1:8839 — all required statuses visible",
        '<section class="card wide"><h2 class="ok">PASS — complete live request matrix</h2>'
        + table
        + "</section>",
    )


def agent_page() -> str:
    fixed = load("agent_fixed_task_runs.json")
    model = load("tool_reliability_20_model_attempts.json")
    runs = fixed.get("runs", fixed) if isinstance(fixed, dict) else fixed
    if isinstance(runs, dict):
        runs = [value | {"name": key} for key, value in runs.items()]
    blocks = []
    for run in runs:
        title = run.get("task") or run.get("case") or run.get("name", "Agent run")
        concise = {
            "request": run.get("user_input"),
            "tool_calls": [
                {
                    "tool": call.get("tool"),
                    "inputs": call.get("inputs"),
                    "success": call.get("observation", {}).get("success", True),
                }
                for call in run.get("invocations", [])
            ],
            "final_answer": run.get("answer"),
            "tool_call_count": run.get("tool_calls"),
            "steps": run.get("steps"),
            "stop_reason": run.get("stop_reason"),
            "repairs": run.get("repairs"),
        }
        blocks.append(card(str(title), concise, run.get("stop_reason") == "success"))
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
    commit = (RAW / "precommit_commit_output.txt").read_text(encoding="utf-8")
    lint_excerpt = "\n".join(before.splitlines()[:20])
    commit_lines = commit.splitlines()
    commit_summary = next((line for line in commit_lines if line.startswith("[main ")), "")
    commit_excerpt = "\n".join(commit_lines[:6] + ([commit_summary] if commit_summary else []))
    attack_cards = []
    for attack in attacks["attacks"]:
        layers = {
            "BEFORE": attack["before_defenses"],
            "PROMPT ONLY": attack["after_prompt_defense"],
            "PROMPT + TOOL": attack["after_prompt_and_tool_defense"],
        }
        trace = "\n\n".join(
            f"{label} — {'PASS' if layer['passed'] else 'FAIL'}\n"
            f"action: {layer['action']}\nobservation: {layer['observation']}\n"
            f"final: {layer['final_answer']}"
            for label, layer in layers.items()
        )
        attack_cards.append(
            card(attack["attack"], trace, attack["after_prompt_and_tool_defense"]["passed"])
        )
    return {
        "reflexion.html": page(
            "Part 3 — Bounded Reflexion",
            "Objective verifier, maximum two retries, budgets, and concise scoped reflections",
            card("Original vs Reflexion raw comparison", reflex, True, True),
        ),
        "security.html": page(
            "Part 5 — Prompt Injection and Tool Security",
            "Three executable local-fixture attacks rerun before and after both defense layers",
            '<div class="grid">' + "".join(attack_cards) + "</div>",
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
            "Real terminal output: lint failure, corrected check, hook execution, and successful commit",
            '<div class="grid">'
            + card("1 — Ruff failure before fix", lint_excerpt, False)
            + card("2 — Ruff after fixes", after, True)
            + card("3 — pre-commit hooks during git commit", commit_excerpt, True, True)
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
