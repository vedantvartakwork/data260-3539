#!/usr/bin/env python3
"""Build the screenshot-backed DATA 260 Homework 5 submission report."""

from __future__ import annotations

import csv
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
    # Retain the genuine test output and name, excluding unrelated earlier-run scrollback.
    with PILImage.open(EVIDENCE / "13_offline_tests.png") as original:
        original.crop((0, 598, original.width, original.height)).save(EVIDENCE / "80_offline_tests_crop.png")
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
    story.append(p(f"<b>Evidence-build commit:</b> <font name='Courier'>{commit}</font>"))
    story.append(p(f"<b>Resolved submission tag:</b> <font name='Courier'>hw5 -&gt; {tag_commit}</font>"))
    story.append(p("Repository link verified. supriyaselvanganesan has write access; Sbnikitha's write invitation is pending acceptance. Generated verification/report evidence follows the tagged application snapshot; application source is checked for exact tag alignment.", "Small"))
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
    section(story, "1. Completion and verification", "Automated local checks are summarized below; repository access is verified separately.")
    checks = [
        ["Area", "Evidence", "Result"],
        ["Database/API", "12 manufacturers; 500 recalls; 200 events; 14/14 authenticated checks", "PASS"],
        ["React/Redux", "Home, create, update, delete; 10-page access to all 500 records", "PASS"],
        ["MealDB MCP", "Exactly four live tools demonstrated", "PASS"],
        ["Domain MCP", "Exactly search/detail/aggregate; valid and invalid calls", "PASS"],
        ["Reliability", "150 deterministic calls; 3-attempt bounded retry", "PASS"],
        ["Offline tests", "9/9 tool and safety tests", "PASS"],
        ["Cumulative suite", "37/37 Python tests; React production build", "PASS"],
        ["Local agent", "Four qwen3:8b scenarios; one enforced safety block", "PASS"],
        ["Verifier", "14/14 checks including real STDIO and tag alignment", "PASS"],
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
            "37-test suite, and rebuilds the React client. Both MCP calls use newly launched STDIO processes; application source is compared to the hw5 tag."
        )
    )
    story.append(PageBreak())

    # Part 1: actual Postman screenshots plus readable request/response companions.
    evidence_page(story, "Part 1 - Database/API: actual Postman operations",
        "This is the original Postman application capture, not a reconstructed panel. It shows the selected HW5 environment and successful manufacturer operations. It is an earlier temporary demonstration run; the linked recall workflow in Sections 3-6 uses manufacturer 29 and recall 6008 consistently.",
        "22_postman_part1.png", "Postman Runner UI: HW5 collection, local environment, response statuses, timings, and test summary.", 7.1 * inch)
    evidence_page(story, "3. Actual Postman Runner evidence - recall operations",
        "This new Postman run visibly shows recall creation, listing, reading, the manufacturer relationship endpoint, update, and delete. Login was sent before the run. It is a separate run from the manufacturer capture and companion panels: recall ID 6008 and manufacturer ID 29 identify this capture.",
        "60_postman_recall_crud_relationship.png", "Actual Runner results: create 201; list, read, relationship, and update 200; delete 204. Two assertions passed, with zero failed assertions and zero request errors.", 7.1 * inch)
    paired_evidence_page(
        story,
        "4. Actual Postman request and response - recall creation",
        "These are unedited Postman application captures from the same run shown above. The first records the submitted JSON request and the second shows the stored 201 response for recall 6008.",
        ("62_postman_create_request.png", "Request tab: POST /api/v1/recalls with the recall payload and 201 Created status."),
        ("61_postman_create_response.png", "Response tab: the returned recall object, including ID 6008 and its manufacturer relation."),
    )
    paired_evidence_page(
        story,
        "5. Actual Postman responses - list and direct record read",
        "The list request demonstrates the fixed eager-load implementation and page metadata. The next capture is a completed direct-read response for the manufacturer used by the recall workflow; Section 3 independently records the matching direct recall read.",
        ("63_postman_list_response.png", "GET /api/v1/recalls?page_size=10 returned 200 with implementation metadata, total, page size, and records."),
        ("69_postman_manufacturer_read.png", "GET /api/v1/manufacturers/29 returned 200 and the complete saved manufacturer."),
    )
    paired_evidence_page(
        story,
        "6. Actual Postman responses - relationship, update, and delete",
        "The relationship query and update are captured directly in Postman. The Runner capture in Section 3 records the subsequent 204 delete response for this same recall, since a successful DELETE has no response body to display.",
        ("65_postman_relationship_response.png", "GET /api/v1/recalls/by-manufacturer/29 returned 200 and includes recall 6008 with manufacturer data."),
        ("71_postman_update_response.png", "PUT /api/v1/recalls/6008 returned 200 with the updated recall; the same run then returned DELETE 204."),
    )
    evidence_page(story, "6A. Actual Postman response - manufacturer deletion",
        "This final cleanup action is shown in the real Postman Runner after its dependent recall was deleted. HTTP 204 deliberately has no response body; the completed request and status are both visible.",
        "74_postman_manufacturer_delete.png", "DELETE /api/v1/manufacturers/29 returned 204 No Content in Postman, completing the temporary demonstration data cleanup.", 7.1 * inch)
    evidence_page(story, "7. Enlarged live MySQL evidence",
        "The database capture is given a full page so the row counts, schema, and foreign key are readable.",
        "24_database.png", "12 manufacturers, 500 recalls, 200 events, required columns, and RESTRICT foreign key.", 7.25 * inch)
    evidence_page(story, "7A. Database evidence — readable detail",
        "This close crop retains the row counts and schema columns while removing unused terminal space. The preceding page remains the complete, unmodified capture.",
        "24_database_detail.png", "Close view of the recorded MySQL row counts and required schema columns.", 7.25 * inch)
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
    evidence_page(story, "Part 2A - MealDB MCP implementation",
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
        (17, "76_mealdb_search_final.jpg", "31_mealdb_search_meals_by_name.png", "search_meals_by_name"),
        (18, "77_mealdb_ingredient_final.jpg", "32_mealdb_meals_by_ingredient.png", "meals_by_ingredient"),
        (19, "78_mealdb_detail_final.jpg", "33_mealdb_meal_details.png", "meal_details"),
        (20, "79_mealdb_random_final.jpg", "34_mealdb_random_meal.png", "random_meal"),
    ):
        evidence_page(
            story,
            f"{number}. MealDB Inspector — {title}",
            "The actual Inspector view visibly includes the submitted arguments and returned output.",
            actual,
            f"Actual MCP Inspector call for {title}, with the Protocol pane expanded to show its exact arguments and response.",
            7.0 * inch,
        )
        evidence_page(
            story,
            f"{number}A. MealDB result — {title}",
            "The exact companion panel is placed on its own page so the result is readable at normal viewing size.",
            filename,
            f"Exact input JSON and readable output for {title}; complete raw output is retained.",
            7.0 * inch,
        )

    # Part 3: domain MCP server.
    evidence_page(story, "Part 2B - Domain MCP implementation",
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
    evidence_page(story, "Part 3 - Operation timeout, retries, and stress",
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
            "1 ms then 2 ms (4 ms cap). p99 uses nearest rank (the maximum of 50 samples). Normal calls have negligible delay. At 50% injected failure, "
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
    story.append(p("Three measured retry outcomes from the same run", "Subsection"))
    with (ROOT / "reports/hw05/raw/fault_injection_calls.csv").open(newline="") as stream:
        calls = list(csv.DictReader(stream))
    for label, predicate in [
        ("First-attempt success", lambda row: row["attempt_outcomes"] == "success"),
        ("Failure followed by retry success", lambda row: row["attempt_outcomes"] == "failure|success"),
        ("All allowed attempts exhausted", lambda row: row["success"] == "False"),
    ]:
        row = next(row for row in calls if predicate(row))
        story.append(p(label, "Subsection"))
        excerpt = (
            f"seed={row['verify_seed']}; failure_rate={row['injected_failure_rate']}; call={row['call_index']}\n"
            f"success={row['success']}; attempts={row['attempts']}; latency_ms={row['latency_ms']}\n"
            f"outcomes={row['attempt_outcomes']}\n"
            f"error={row['error'] or 'null'}"
        )
        story.append(Preformatted(excerpt, styles["CodeBlock"]))
    story.append(PageBreak())
    paired_evidence_page(story, "Part 4 - execute_tool and offline assertions",
        "Implementation and representative assertions are immediately followed by the full named PASS output.",
        ("40_execute_tests_code.png", "Safe execution entry point, assertion examples, and 9/9 summary."),
        ("80_offline_tests_crop.png", "Unaltered offline-test region cropped from the original terminal capture; name, all nine PASS results and summary remain visible. The latest 9/9 rerun is recorded in RUN_LOG.txt."))

    # Part 5: agent.
    paired_evidence_page(story, "Part 5 - Bounded agent loop and Ollama scenarios",
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
        [str(cell) if row_index == 0 else Paragraph(str(cell), styles["Small"]) for cell in row]
        for row_index, row in enumerate(contract_text)
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
    disclosures = [line for line in (ROOT / "reports/hw05/AI_USE.md").read_text().splitlines() if line[:2] in ("1.", "2.", "3.", "4.")]
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
            "Temporary UI/Postman demonstration records were deleted after proof was captured; "
            "the final authenticated API run also cleaned up its temporary fixtures. The final live "
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
