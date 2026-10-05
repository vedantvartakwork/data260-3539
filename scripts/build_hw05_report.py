#!/usr/bin/env python3
"""Build the screenshot-backed DATA 260 Homework 5 submission report."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "reports/hw05/evidence"
REPORT = ROOT / "reports/hw05/report.pdf"
CANVAS_COPY = ROOT / "output/pdf/Vartak_HW5.pdf"

GREEN = colors.HexColor("#0B5130")
MID_GREEN = colors.HexColor("#247A4B")
PALE_GREEN = colors.HexColor("#E8F4EC")
INK = colors.HexColor("#17211B")
MUTED = colors.HexColor("#58665E")
RULE = colors.HexColor("#B7C8BE")
RED = colors.HexColor("#A83A32")


def git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def tagged_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-list", "-n", "1", "hw5"], cwd=ROOT, text=True
    ).strip()


def img(path: Path, max_width: float = 7.25 * inch, max_height: float = 6.5 * inch) -> Image:
    with PILImage.open(path) as source:
        width, height = source.size
    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


def page_chrome(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(0.55 * inch, 10.45 * inch, 7.95 * inch, 10.45 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.58 * inch, 10.57 * inch, "DATA 260 | Homework 5 | Vedant Vartak")
    canvas.drawRightString(7.92 * inch, 0.34 * inch, f"Page {doc.page}")
    canvas.restoreState()


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="TitleGreen",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=GREEN,
        alignment=TA_LEFT,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="Section",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        textColor=GREEN,
        spaceBefore=4,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="Subsection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        textColor=MID_GREEN,
        spaceBefore=4,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="Body11",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=INK,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        name="Small",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=MUTED,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="Caption",
        parent=styles["BodyText"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=11,
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceBefore=4,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        name="CodeBlock",
        fontName="Courier",
        fontSize=7.2,
        leading=8.6,
        textColor=INK,
        backColor=colors.HexColor("#F2F5F3"),
        borderColor=RULE,
        borderWidth=0.5,
        borderPadding=6,
        leftIndent=0,
        spaceBefore=4,
        spaceAfter=5,
    )
)


def p(text: str, style: str = "Body11") -> Paragraph:
    return Paragraph(text, styles[style])


def section(story: list, title: str, intro: str | None = None) -> None:
    story.append(p(title, "Section"))
    if intro:
        story.append(p(intro))


def evidence_page(
    story: list,
    title: str,
    intro: str,
    filename: str,
    caption: str,
    max_height: float = 6.8 * inch,
) -> None:
    section(story, title, intro)
    story.append(img(EVIDENCE / filename, max_height=max_height))
    story.append(p(caption, "Caption"))
    story.append(PageBreak())


def paired_evidence_page(
    story: list,
    title: str,
    intro: str,
    first: tuple[str, str],
    second: tuple[str, str],
) -> None:
    section(story, title, intro)
    story.append(img(EVIDENCE / first[0], max_height=3.25 * inch))
    story.append(p(first[1], "Caption"))
    story.append(img(EVIDENCE / second[0], max_height=3.25 * inch))
    story.append(p(second[1], "Caption"))
    story.append(PageBreak())


def ui_code_page(
    story: list,
    title: str,
    intro: str,
    screenshot: str,
    caption: str,
    code: str,
) -> None:
    section(story, title, intro)
    story.append(img(EVIDENCE / screenshot, max_height=4.25 * inch))
    story.append(p(caption, "Caption"))
    story.append(p("Relevant Redux/React code in the same report frame", "Subsection"))
    story.append(Preformatted(code.strip(), styles["CodeBlock"]))
    story.append(PageBreak())


def make_report() -> None:
    commit = git_commit()
    tag_commit = tagged_commit()
    summary = json.loads((ROOT / "reports/hw05/raw/fault_injection_summary.json").read_text())
    story: list = []

    # Cover and configuration.
    story.append(Spacer(1, 0.28 * inch))
    story.append(p("Vedant Vartak", "Subsection"))
    story.append(p("DATA 260 - Agentic AI and Distributed Systems", "Small"))
    story.append(p("Homework 5: Tools, Reliability, and a Safe Local Agent", "TitleGreen"))
    story.append(
        p(
            '<b>GitHub:</b> <link href="https://github.com/vedantvartakwork/data260-3539">'
            "https://github.com/vedantvartakwork/data260-3539</link>"
        )
    )
    story.append(p(f"<b>Verified implementation commit:</b> <font name='Courier'>{commit}</font>"))
    story.append(p(f"<b>Resolved submission tag:</b> <font name='Courier'>hw5 -&gt; {tag_commit}</font>"))
    config = [
        ["Item", "Value", "Item", "Value"],
        ["SID4", "3539", "PORT_BASE", "8839"],
        ["PREFIX", "s3539", "SEED", "3539"],
        ["VERIFY_SEED", "263539", "DOMAIN_ID", "3"],
        ["Domain", "Grocery supply and recall notices", "Local model", "qwen3:8b"],
        ["Hardware", "Apple M4 MacBook Air", "Memory / CPU", "16 GB / 10 cores"],
        ["Platform", "macOS 15.3", "Ports", "API 8839 / UI 5173"],
    ]
    table = Table(config, colWidths=[1.08 * inch, 2.52 * inch, 1.15 * inch, 2.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, RULE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_GREEN]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.16 * inch))
    story.append(
        p(
            "This cumulative submission extends the authenticated FastAPI/MySQL application with a "
            "manufacturer relationship, Redux Toolkit and Axios, two MCP servers, strict tool schemas, "
            "bounded retries, and a local Ollama tool-calling loop with deterministic safety enforcement."
        )
    )
    story.append(p("Submission contents", "Subsection"))
    story.append(
        p(
            "The repository includes RUN_LOG.txt, METRICS.md, REFLECTION.md, TOOL_CONTRACTS.md, "
            "AI_USE.md, verification.json, 150 raw fault-injection rows, MCP/agent/API raw outputs, "
            "Postman collection and environment files, and this screenshot-backed report."
        )
    )
    story.append(PageBreak())

    # Requirements matrix.
    section(story, "1. Completion and verification", "The final cumulative checks passed without exceptions or skipped requirements.")
    checks = [
        ["Area", "Evidence", "Result"],
        ["Database/API", "12 manufacturers; 500 recalls; 200 events; 14/14 authenticated checks", "PASS"],
        ["React/Redux", "Home, create, update, delete; 10-page access to all 500 records", "PASS"],
        ["MealDB MCP", "Exactly four live tools demonstrated", "PASS"],
        ["Domain MCP", "Exactly search/detail/aggregate; valid and invalid calls", "PASS"],
        ["Reliability", "150 deterministic calls; 3-attempt bounded retry", "PASS"],
        ["Offline tests", "9/9 tool and safety tests", "PASS"],
        ["Cumulative suite", "34/34 Python tests; React production build", "PASS"],
        ["Local agent", "Four qwen3:8b scenarios; one enforced safety block", "PASS"],
        ["Verifier", "12/12 checks", "PASS"],
    ]
    check_table = Table(checks, colWidths=[1.3 * inch, 5.15 * inch, 0.72 * inch], repeatRows=1)
    check_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTNAME", (-1, 1), (-1, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (-1, 1), (-1, -1), MID_GREEN),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, RULE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_GREEN]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(check_table)
    story.append(Spacer(1, 0.15 * inch))
    story.append(
        p(
            "The verifier independently inventories both MCP servers, calls one tool from each, checks "
            "the live API health endpoint, counts all 150 experiment rows, runs the offline runner and "
            "34-test suite, and rebuilds the React client."
        )
    )
    story.append(PageBreak())

    # Part 1: actual Postman screenshots plus readable request/response companions.
    evidence_page(story, "2. Actual Postman Runner evidence - first operations",
        "This is the original Postman application capture, not a reconstructed panel. It shows the selected HW5 environment and successful manufacturer operations.",
        "22_postman_part1.png", "Postman Runner UI: HW5 collection, local environment, response statuses, timings, and test summary.", 7.1 * inch)
    evidence_page(story, "3. Actual Postman Runner evidence - final operations",
        "This second original Postman capture shows the update, delete, login, and cleanup operations in the same collection run.",
        "23_postman_part2.png", "Postman Runner UI: update recall, delete recall, login, and manufacturer cleanup returned 200/204 responses.", 7.1 * inch)
    evidence_page(story, "4. Manufacturer CRUD request/response companion",
        "Every operation is labeled with the exact HTTP request, returned status, and response excerpt.",
        "28_api_manufacturers.png", "Manufacturer create, list, read, and update all returned their expected statuses.", 7.15 * inch)
    evidence_page(story, "5. Recall create, list, read, and relationship companion",
        "The previously unclear recall operations are now all shown explicitly, including filtered listing and relationship lookup.",
        "29_api_recalls_read.png", "Recall create/list/read and GET by manufacturer all returned the created record.", 7.15 * inch)
    evidence_page(story, "6. Recall update, delete, FK block, and cleanup",
        "The write half proves update/delete behavior, the 404 after deletion, and RESTRICT enforcement.",
        "30_api_recalls_write.png", "All status codes match the recorded 14/14 live integration checks.", 7.15 * inch)
    evidence_page(story, "7. Enlarged live MySQL evidence",
        "The database capture is given a full page so the row counts, schema, and foreign key are readable.",
        "24_database.png", "12 manufacturers, 500 recalls, 200 events, required columns, and RESTRICT foreign key.", 7.25 * inch)
    evidence_page(story, "8. Database and API implementation evidence",
        "The relevant validation and transaction code is immediately followed by measured output.",
        "38_database_api_code.png", "Validation, 409 handling, relationship integrity, and live row counts.", 7.15 * inch)
    evidence_page(story, "9. Authentication, format validation, and numeric default",
        "The requested security and schema details are explicit rather than inferred from PASS claims.",
        "49_security_validation.png", "Salted PBKDF2 hashing, unique-field formats, and the units_affected default are documented from source.", 7.15 * inch)

    evidence_page(story, "10. Redux store and slice setup",
        "The store registration, async thunk, and slice state are shown as implementation evidence.",
        "46_redux_store_slice.png", "configureStore registers the recalls reducer; the thunk and fulfilled reducer preserve pagination metadata.", 7.15 * inch)
    evidence_page(story, "11. Redux Home - code and UI in one screenshot",
        "The composite contains the actual thunk/slice fields and visible UI output, including page 1 and page 2.",
        "42_redux_home_composite.png", "Showing 1-50 of 500; page 1/10 and page 2/10 prove access beyond the first 50 records.", 7.2 * inch)
    evidence_page(story, "12. Redux Create - form, code, and saved output",
        "The create form, thunk, and persisted success result appear in one report frame.",
        "43_redux_create_composite.png", "The completed form is visible before createRecall returns the saved record and success notice.", 7.2 * inch)
    evidence_page(story, "13. Redux Update - form, code, and revised output",
        "The update form, thunk/reducer, and revised record output appear together.",
        "44_redux_update_composite.png", "The edited form is visible before Redux replaces the item with the API response.", 7.2 * inch)
    evidence_page(story, "14. Redux Delete - code, confirmation, and output",
        "The dedicated confirmation route and post-delete state appear with the reducer code in one composite screenshot.",
        "45_redux_delete_composite.png", "Explicit confirmation precedes deletion; the success notice follows API completion.", 7.2 * inch)

    # Part 2: implementation plus actual Inspector screenshots and readable companions.
    evidence_page(story, "15. MealDB MCP implementation",
        "This source evidence shows the exact four-tool surface, stdio transport, stderr logging, HTTP timeout, and handled failures.",
        "47_mealdb_server_code.png", "MealDB server implementation excerpts and failure boundary.", 7.15 * inch)
    evidence_page(
        story,
        "16. MealDB MCP server connection",
        "The Inspector connected over stdio using the project virtual environment and exposed exactly four required tools.",
        "01_mealdb_connected.png",
        "Connected MealDB MCP server in Inspector; tools, prompts, and resources inventories completed successfully.",
        6.6 * inch,
    )
    for number, actual, filename, title in (
        (17, "50_mealdb_search_with_input.png", "31_mealdb_search_meals_by_name.png", "search_meals_by_name"),
        (18, "51_mealdb_ingredient_with_input.png", "32_mealdb_meals_by_ingredient.png", "meals_by_ingredient"),
        (19, "52_mealdb_detail_with_input.png", "33_mealdb_meal_details.png", "meal_details"),
        (20, "53_mealdb_random_with_input.png", "34_mealdb_random_meal.png", "random_meal"),
    ):
        paired_evidence_page(story, f"{number}. MealDB Inspector - {title}",
            "The Inspector screenshot visibly includes the submitted arguments and returned output, paired with a readable exact-input/output companion.",
            (actual, f"Actual MCP Inspector call for {title}, with the Protocol pane expanded to show its exact arguments and response."),
            (filename, f"Exact input JSON and readable output for {title}; complete raw output is retained."))

    # Part 3: domain MCP server.
    evidence_page(story, "21. Domain MCP implementation",
        "The server exposes exactly three stdio tools and routes all calls through the validated shared boundary.",
        "48_domain_server_code.png", "stderr logging, stdio transport, exact tool signatures, and stable error envelope.", 7.15 * inch)
    for number, name, valid_shot, invalid_shot in (
        (22, "search", "54_domain_search_valid_with_input.png", "55_domain_search_invalid_with_input.png"),
        (24, "detail", "56_domain_detail_valid_with_input.png", "57_domain_detail_invalid_with_input.png"),
        (26, "aggregate", "58_domain_aggregate_valid_with_input.png", "59_domain_aggregate_invalid_with_input.png"),
    ):
        paired_evidence_page(story, f"{number}. Actual Domain Inspector calls - {name}",
            "The expanded Protocol panes show exact inputs and responses for one valid and one rejected call.",
            (valid_shot, f"Actual valid {name} call in MCP Inspector, including submitted arguments and response."),
            (invalid_shot, f"Actual invalid {name} call, rejected arguments, and complete failure envelope in MCP Inspector."))
        evidence_page(story, f"{number + 1}. Domain MCP contract - {name}",
            "Expected JSON schema, valid input/output, rejected JSON, complete error, and rejection reason are shown together.",
            f"{35 + ((number - 22) // 2)}_domain_contract_{name}.png",
            f"The {name} contract returns the stable {{ok, data, error}} envelope for both valid and invalid calls.", 7.25 * inch)

    # Part 4: reliability.
    evidence_page(story, "28. Real operation timeout, retry code, and behavior",
        "The operation is executed through Future.result(timeout=remaining), so a hanging call is interrupted from the caller's perspective rather than merely checked after failure.",
        "39_retry_code.png", "Runtime test: a 200 ms operation returns a clean timeout within the 30 ms caller deadline; retries remain bounded.", 7.15 * inch)
    section(
        story,
        "29. Fault-injection metrics and representative rows",
        "The experiment used VERIFY_SEED 263539 and exactly 150 calls: 50 each at 0%, 20%, and 50% injected failure.",
    )
    retry_rows = [["Injected failure", "Calls", "Success", "Mean latency", "p99 latency"]]
    for row in summary["summaries"]:
        retry_rows.append(
            [
                f"{int(row['injected_failure_rate'] * 100)}%",
                str(row["calls"]),
                f"{row['success_rate'] * 100:.0f}%",
                f"{row['mean_latency_ms']:.3f} ms",
                f"{row['p99_latency_ms']:.3f} ms",
            ]
        )
    retry_table = Table(retry_rows, colWidths=[1.45 * inch, 0.75 * inch, 1.0 * inch, 1.35 * inch, 1.35 * inch])
    retry_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, RULE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_GREEN]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(retry_table)
    story.append(Spacer(1, 0.12 * inch))
    story.append(
        p(
            "Policy: at most three attempts, 100 ms total timeout, and bounded exponential delays of "
            "1 ms then 2 ms (4 ms cap). Normal calls have negligible delay. At 50% injected failure, "
            "92% still completed, while the remaining failures returned a clean error after exhausting "
            "the fixed attempt budget. A batch workload could tolerate more attempts and jitter; the "
            "interactive assistant favors a short, predictable response ceiling."
        )
    )
    story.append(
        p(
            "The numbers in this table are from the final 150-call run in raw/fault_injection_calls.csv and its matching raw/fault_injection_summary.json. Representative rows in the CSV include immediate success, failure-then-success, and three exhausted attempts.",
            "Caption",
        )
    )
    story.append(PageBreak())
    paired_evidence_page(story, "30. execute_tool and offline assertions",
        "Implementation and representative assertions are immediately followed by the full named PASS output.",
        ("40_execute_tests_code.png", "Safe execution entry point, assertion examples, and 9/9 summary."),
        ("13_offline_tests.png", "Terminal output names every valid/invalid, safety, and max-step test as PASS."))

    # Part 5: agent.
    paired_evidence_page(story, "31. Bounded agent loop and Ollama scenarios",
        "The agent loop code and corresponding four-scenario terminal output are shown together.",
        ("41_agent_loop_code.png", "MAX_STEPS loop, execute_tool call, normal completion, and deterministic safety stop."),
        ("14_agent_scenarios.png", "Three grounded completions plus one safety-rule block using qwen3:8b."))
    section(story, "32. Agent reflection", "Selected run: Scenario 4 - deterministic safety-rule block.")
    reflection = [
        "I selected the fourth Ollama run because it demonstrates that the harness, not the language model, owns the safety boundary. The user prompt explicitly asked the agent to retrieve recall records with a limit of 25 and told it not to reduce that limit. In step 1, local qwen3:8b produced a structured action for the search tool with query set to an empty string and limit set to 25. The harness did not send that action directly to the database. Instead, run_agent routed it through the single execute_tool(name, inputs) entry point used by every agent tool call.",
        "Inside execute_tool, the domain-specific safety rule checked the requested search limit before normal schema validation or repository access. Because the limit exceeded the allowed agent maximum of 10, the function returned the shared JSON envelope with ok=false, data=null, and the error 'Safety rule blocked search: limit cannot exceed 10 records.' It raised no exception and issued no SQL query.",
        "The loop parsed this clean result, logged the tool name, input, complete result, step number, and run identifier to agent_runs.jsonl, and recognized the safety-error prefix. It then stopped immediately with stop_reason equal to safety_rule_block. The run therefore used one step and one tool-call attempt, never approached the six-step ceiling, and never gave the model a chance to bypass the policy. This run shows why centralized enforcement is stronger than asking the model to follow a prompt: even when the model follows the user's unsafe request exactly, deterministic application code blocks it consistently.",
    ]
    for paragraph in reflection:
        story.append(p(paragraph))
    story.append(p("Word count: 264", "Small"))
    story.append(PageBreak())

    # Tool contracts and AI use.
    section(story, "33. Tool contracts and AI-use disclosure")
    contract_text = [
        ["Tool", "Expected JSON", "Rejected JSON", "Complete error location"],
        ["search", '{"query": str, "limit": int}', '{"query":"s","limit":5}', "Section 23: Domain MCP contract - search"],
        ["detail", '{"recall_id": positive int}', '{"recall_id":0}', "Section 25: Domain MCP contract - detail"],
        ["aggregate", '{"group_by": enum, "min_units": int}', '{"group_by":"submitter", "min_units":0}', "Section 27: Domain MCP contract - aggregate"],
    ]
    contract_rows = [
        [Paragraph(str(cell), styles["Small"]) for cell in row]
        for row in contract_text
    ]
    contract_table = Table(contract_rows, colWidths=[0.75 * inch, 1.75 * inch, 1.7 * inch, 2.95 * inch], repeatRows=1)
    contract_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, RULE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_GREEN]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(contract_table)
    story.append(Spacer(1, 0.12 * inch))
    story.append(p("Sections 23, 25, and 27 contain each full expected schema, valid input/output, rejected object, untruncated returned error, and explanation. All three return {ok, data, error}. Pydantic validation is caught at the boundary, and execute_tool applies the narrower agent-only limit of 10."))
    story.append(p("AI-use disclosure", "Section"))
    disclosures = [
        "1. I used an AI assistant to translate the assignment checklist into a cumulative implementation plan, draft FastAPI/Redux/MCP code, and create repeatable validation scripts. I independently reviewed the requirements, ran the tests, inspected the artifacts, and captured the final evidence.",
        "2. I independently found that my first Home-page implementation deleted a recall directly from the record card, bypassing the required delete-confirmation UI even though the API operation worked.",
        "3. I detected it by tracing the Home button to its Redux dispatch and reproducing the rendered flow: clicking Delete immediately issued the request instead of first showing the selected record and confirmation action.",
        "4. I changed Home to navigate to /delete/:id, added a confirmation page that loads the selected record, and dispatches deleteRecall only after explicit confirmation. I verified the confirmation screen, success notice, and MySQL removal.",
    ]
    for disclosure in disclosures:
        story.append(p(disclosure))
    story.append(PageBreak())

    section(story, "34. Submission file alignment")
    files = [
        ["Required item", "Repository location"],
        ["Final report", "reports/hw05/report.pdf"],
        ["Run log", "reports/hw05/RUN_LOG.txt"],
        ["Metrics", "reports/hw05/METRICS.md"],
        ["AI disclosure", "reports/hw05/AI_USE.md"],
        ["Verification", "reports/hw05/verification.json"],
        ["Raw evidence", "reports/hw05/raw/"],
        ["Screenshots", "reports/hw05/evidence/"],
        ["Postman files", "reports/hw05/postman/"],
        ["Canvas upload copy", "output/pdf/Vartak_HW5.pdf"],
    ]
    file_table = Table(files, colWidths=[2.0 * inch, 5.15 * inch], repeatRows=1)
    file_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (1, 1), (1, -1), "Courier"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, RULE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_GREEN]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(file_table)
    story.append(Spacer(1, 0.16 * inch))
    story.append(
        p(
            "The repository deliberately excludes temporary demonstration rows: UI record 6006 and "
            "Postman recall 6007/manufacturer 28 were deleted after proof was captured. The final live "
            "database therefore matches the deterministic cumulative seed."
        )
    )
    story.append(p("End of report", "Subsection"))

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    CANVAS_COPY.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(REPORT),
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.55 * inch,
        title="Vartak - DATA 260 Homework 5",
        author="Vedant Vartak",
        subject="Agentic AI and Distributed Systems Homework 5",
    )
    document.build(story, onFirstPage=page_chrome, onLaterPages=page_chrome)
    CANVAS_COPY.write_bytes(REPORT.read_bytes())
    print(REPORT)
    print(CANVAS_COPY)


if __name__ == "__main__":
    make_report()
