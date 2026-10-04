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
    story.append(p(f"<b>Implementation commit:</b> <font name='Courier'>{commit}</font>"))
    story.append(p("<b>Submission tag:</b> <font name='Courier'>hw5</font> (applied to the final report commit)"))
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
        ["Database/API", "12 manufacturers; 500 recalls; 200 events; authenticated CRUD", "PASS"],
        ["React/Redux", "Home, create, update, delete; Redux Toolkit thunks; Axios", "PASS"],
        ["MealDB MCP", "Exactly four live tools demonstrated", "PASS"],
        ["Domain MCP", "Exactly search/detail/aggregate; valid and invalid calls", "PASS"],
        ["Reliability", "150 deterministic calls; 3-attempt bounded retry", "PASS"],
        ["Offline tests", "9/9 tool and safety tests", "PASS"],
        ["Cumulative suite", "33/33 Python tests; React production build", "PASS"],
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
            "33-test suite, and rebuilds the React client."
        )
    )
    story.append(PageBreak())

    # Part 1: API/Postman and database.
    evidence_page(
        story,
        "2. FastAPI and Postman CRUD - first half",
        "A single collection run used the SID-specific environment and completed with zero errors.",
        "22_postman_part1.png",
        "Postman run summary and successful manufacturer create/list/read/update plus recall create/list/read operations.",
        6.55 * inch,
    )
    evidence_page(
        story,
        "3. FastAPI and Postman CRUD - second half",
        "The same run verifies the relationship endpoint, update path, authenticated login, and cleanup deletes.",
        "23_postman_part2.png",
        "Successful recall update (200), recall delete (204), login (200), and manufacturer delete (204).",
        6.55 * inch,
    )
    evidence_page(
        story,
        "4. Live MySQL schema and row counts",
        "The cumulative seed is stable after the UI and Postman demonstrations; temporary evidence records were removed.",
        "24_database.png",
        "Live schema evidence: 12 manufacturers, 500 recall notices, 200 related events, required columns, and RESTRICT foreign key.",
        7.1 * inch,
    )

    # Part 1 Redux pages with code and output together.
    ui_code_page(
        story,
        "5. Redux Home page",
        "Home reads normalized application state through useSelector and dispatches the search thunk.",
        "15_react_home.png",
        "Authenticated Home page showing 50 database-backed recall cards and search controls.",
        """
const dispatch = useDispatch();
const { items: records, loading, error, notice } =
  useSelector((state) => state.recalls);

function handleSearch(event) {
  event.preventDefault();
  dispatch(fetchRecalls(query));
}

<Link className="danger button-link"
      to={`/delete/${record.id}`}>Delete</Link>
""",
    )
    ui_code_page(
        story,
        "6. Redux Create page",
        "Create dispatches the asynchronous createRecall thunk and returns to Home only after unwrap confirms success.",
        "17_react_create_success.png",
        "Created REC-3539-90001; the Redux notice and persisted database record are visible.",
        """
async function handleCreate(payload) {
  await dispatch(createRecall(payload)).unwrap();
  navigate("/");
}

export const createRecall = createAsyncThunk(
  "recalls/create",
  async (payload, thunkApi) => {
    const response = await apiClient.post("/recalls", payload);
    return response.data;
  }
);
""",
    )
    ui_code_page(
        story,
        "7. Redux Update page",
        "Update loads one database record, dispatches updateRecall with its numeric ID, and replaces that item in Redux state.",
        "19_react_update_success.png",
        "The saved product, brand, units, and details are visibly updated after the API returns 200.",
        """
async function handleUpdate(payload) {
  await dispatch(updateRecall({ id: Number(id), payload })).unwrap();
  navigate("/");
}

.addCase(updateRecall.fulfilled, (state, action) => {
  const index = state.items.findIndex(
    (item) => item.id === action.payload.id
  );
  if (index >= 0) state.items[index] = action.payload;
});
""",
    )
    ui_code_page(
        story,
        "8. Redux Delete page",
        "Delete uses a dedicated confirmation route and removes the record from Redux only after the API succeeds.",
        "21_react_delete_success.png",
        "The success notice confirms temporary recall ID 6006 was deleted and the seeded 500-record state was restored.",
        """
async function handleDelete() {
  await dispatch(deleteRecall(Number(id))).unwrap();
  navigate("/");
}

.addCase(deleteRecall.fulfilled, (state, action) => {
  state.items = state.items.filter(
    (item) => item.id !== action.payload
  );
  state.notice = `Deleted recall ID ${action.payload} successfully.`;
});
""",
    )
    paired_evidence_page(
        story,
        "9. Form and confirmation states",
        "The input and confirmation screens provide additional evidence of complete user-facing CRUD behavior.",
        ("16_react_create_form.png", "Create form populated with valid SID-specific evidence data and exact terms label."),
        ("20_react_delete_confirm.png", "Dedicated confirmation screen prevents an accidental one-click delete."),
    )
    paired_evidence_page(
        story,
        "10. Create and update form states",
        "Both form paths reuse the validated RecordForm component while preserving distinct page routes.",
        ("16_react_create_form.png", "Create form before submission, including the exact terms-and-conditions control."),
        ("18_react_update_form.png", "Update page loaded persisted values and accepted the revised data."),
    )
    evidence_page(
        story,
        "11. Explicit delete confirmation",
        "The destructive action is isolated behind a named confirmation page with a Cancel path.",
        "20_react_delete_confirm.png",
        "Delete confirmation for temporary evidence record 6006 before the successful cleanup shown earlier.",
        6.6 * inch,
    )

    # Part 2: public MCP server.
    evidence_page(
        story,
        "12. MealDB MCP server connection",
        "The Inspector connected over stdio using the project virtual environment and exposed exactly four required tools.",
        "01_mealdb_connected.png",
        "Connected MealDB MCP server in Inspector; tools, prompts, and resources inventories completed successfully.",
        6.6 * inch,
    )
    paired_evidence_page(
        story,
        "13. MealDB tools - name and ingredient",
        "Both discovery tools returned structured JSON from the public MealDB API.",
        ("02_mealdb_search.png", "search_meals_by_name returned Spicy Arrabiata Penne for the name query."),
        ("03_mealdb_ingredient.png", "meals_by_ingredient returned five chicken meals with IDs, names, and thumbnails."),
    )
    paired_evidence_page(
        story,
        "14. MealDB tools - details and random",
        "The remaining tools return complete meal objects, including normalized ingredient arrays.",
        ("04_mealdb_detail.png", "meal_details returned instructions, links, and measured ingredients for meal 52771."),
        ("05_mealdb_random.png", "random_meal returned Spaghetti alla Carbonara with complete structured details."),
    )

    # Part 3: domain MCP server.
    paired_evidence_page(
        story,
        "15. Domain tool contract - search",
        "The domain MCP server exposes exactly search, detail, and aggregate, all using one stable JSON envelope.",
        ("06_domain_search_valid.png", "Valid search for shrimp returned ok=true and SID-specific recall matches."),
        ("07_domain_search_invalid.png", "One-character input returned ok=false, data=null, and a clean validation error."),
    )
    paired_evidence_page(
        story,
        "16. Domain tool contract - detail",
        "Detail resolves a positive integer recall ID and includes the related manufacturer object.",
        ("08_domain_detail_valid.png", "Valid detail for recall 5505 returned recall and manufacturer fields."),
        ("09_domain_detail_invalid.png", "ID zero was rejected through the same error envelope without an exception."),
    )
    paired_evidence_page(
        story,
        "17. Domain tool contract - aggregate",
        "Aggregate restricts grouping to approved, non-sensitive dimensions.",
        ("10_domain_aggregate_valid.png", "Category aggregation returned recall_count and total_units for all four categories."),
        ("11_domain_aggregate_invalid.png", "The unsupported submitter dimension was rejected with ok=false."),
    )

    # Part 4: reliability.
    section(
        story,
        "18. Retry policy and fault-injection results",
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
    story.append(img(EVIDENCE / "12_retry_examples.png", max_height=4.15 * inch))
    story.append(
        p(
            "Representative rows show immediate success, failure-then-success, and three exhausted attempts; the summary above is derived from all 150 CSV rows.",
            "Caption",
        )
    )
    story.append(PageBreak())
    evidence_page(
        story,
        "19. Offline tool and safety tests",
        "The offline runner is deterministic and requires no external network or language model.",
        "13_offline_tests.png",
        "Nine of nine tests passed: valid/invalid calls for all tools, allowed/blocked safety cases, and max-step termination.",
        6.7 * inch,
    )

    # Part 5: agent.
    evidence_page(
        story,
        "20. Local Ollama agent scenarios",
        "All scenarios used qwen3:8b, temperature 0, model seed 3539, and MAX_STEPS=6.",
        "14_agent_scenarios.png",
        "Three scenarios completed normally after one grounded tool call; the fourth stopped immediately at the safety boundary.",
        6.7 * inch,
    )
    section(story, "21. Agent reflection", "Selected run: Scenario 4 - deterministic safety-rule block.")
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
    section(story, "22. Tool contracts under stress")
    contract_rows = [
        ["Tool", "Accepted input", "Rejected input", "Clean behavior"],
        ["search", "query 2-80 chars; limit 1-25", "query='s'", "Minimum-length error"],
        ["detail", "positive recall_id", "recall_id=0", "Positive-ID error"],
        ["aggregate", "category|manufacturer", "group_by='submitter'", "Approved-dimension error"],
    ]
    contract_table = Table(contract_rows, colWidths=[0.9 * inch, 2.15 * inch, 1.65 * inch, 2.45 * inch], repeatRows=1)
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
    story.append(
        p(
            "All three return {ok, data, error}. Pydantic validation is caught at the tool boundary so "
            "bad arguments never become uncaught exceptions. The Part 5 agent rule is intentionally "
            "narrower than the MCP schema: execute_tool blocks search limits above 10 to prevent bulk "
            "extraction, while direct interactive MCP use still permits up to 25."
        )
    )
    story.append(p("AI-use disclosure", "Section"))
    disclosures = [
        "1. I used an AI assistant to translate the assignment checklist into a cumulative implementation plan, draft FastAPI/Redux/MCP code, and create repeatable validation scripts. I independently reviewed the requirements, ran the tests, inspected the artifacts, and captured the final evidence.",
        "2. I independently verified that the supplied demo's relationship route order was unsuitable to copy directly: a dynamic /{course_id} route appeared before /by-instructor/{instructor_id}, which can cause the static path to be parsed as an integer ID.",
        "3. I detected the issue by reading the complete demo source after extracting the assignment requirements, then comparing FastAPI declaration-order matching with the required relationship endpoint. I also used production builds and offline tests instead of assuming generated code was correct.",
        "4. I declared the static /by-manufacturer/{manufacturer_id} relationship route before the dynamic /{recall_id} route. The cumulative suite and live API flow verify that relationship lookup coexists with individual recall lookup.",
    ]
    for disclosure in disclosures:
        story.append(p(disclosure))
    story.append(PageBreak())

    section(story, "23. Submission file alignment")
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
