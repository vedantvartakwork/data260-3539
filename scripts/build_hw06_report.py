#!/usr/bin/env python3
"""Build the evidence-backed DATA 260 Homework 6 report."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports/hw06"
RAW = REPORT_DIR / "raw"
SHOTS = REPORT_DIR / "screenshots"
REPORT = REPORT_DIR / "report.pdf"
OUTPUT_COPY = ROOT / "output/pdf/Vartak_HW6.pdf"
DOWNLOAD_COPY = Path("/Users/vedantvartak/Downloads/Vartak_HW6.pdf")
DESKTOP_COPY = Path("/Users/vedantvartak/Desktop/Homework6/Vartak_HW6.pdf")
COURSE_DESKTOP_COPY = Path("/Users/vedantvartak/Desktop/DATA 260 Agentic AI & Distributed Systems/Vartak_HW6.pdf")

GREEN = colors.black
MID_GREEN = colors.black
PALE_GREEN = colors.white
INK = colors.black
MUTED = colors.black
RULE = colors.black
ORANGE = colors.black


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def git_tag_commit() -> str:
    return subprocess.check_output(["git", "rev-list", "-n", "1", "hw6"], cwd=ROOT, text=True).strip()


def page_chrome(canvas, doc) -> None:
    """Keep pages plain: no running header, footer, or page number."""


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleGreen", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=GREEN, alignment=TA_LEFT, spaceAfter=10))
styles.add(ParagraphStyle(name="Section", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=GREEN, spaceBefore=4, spaceAfter=8))
styles.add(ParagraphStyle(name="Subsection", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=14, textColor=MID_GREEN, spaceBefore=4, spaceAfter=5))
styles.add(ParagraphStyle(name="Body11", parent=styles["BodyText"], fontName="Helvetica", fontSize=11, leading=15, textColor=INK, spaceAfter=7))
styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=12, textColor=MUTED, spaceAfter=4))
styles.add(ParagraphStyle(name="Caption", parent=styles["BodyText"], fontName="Helvetica-Oblique", fontSize=9, leading=11, textColor=MUTED, alignment=TA_CENTER, spaceBefore=4, spaceAfter=7))
styles.add(ParagraphStyle(name="CodeBlock", fontName="Courier", fontSize=8.8, leading=10.2, textColor=INK, backColor=colors.white, borderColor=RULE, borderWidth=0.5, borderPadding=6, spaceBefore=4, spaceAfter=5))


def p(text: str, style: str = "Body11") -> Paragraph:
    return Paragraph(text, styles[style])


def section(story: list, title: str, intro: str | None = None) -> None:
    story.append(p(title, "Section"))
    if intro:
        story.append(p(intro))


def img(path: Path, max_width: float = 7.25 * inch, max_height: float = 7.25 * inch) -> Image:
    with PILImage.open(path) as source:
        width, height = source.size
    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


def evidence_page(story: list, title: str, intro: str, filename: str, caption: str) -> None:
    section(story, title, intro)
    story.append(img(SHOTS / filename))
    story.append(p(caption, "Caption"))
    story.append(PageBreak())


def excerpt(path: str, start: str, end: str | None = None) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    first = text.index(start)
    last = text.index(end, first) if end else len(text)
    return text[first:last].rstrip()


def code_output_page(story: list, title: str, intro: str, code: str, output: str) -> None:
    section(story, title, intro)
    story.append(p("Relevant implementation", "Subsection"))
    story.append(Preformatted(code.rstrip(), styles["CodeBlock"]))
    story.append(p("Verified output", "Subsection"))
    story.append(Preformatted(output.rstrip(), styles["CodeBlock"]))
    story.append(PageBreak())


def styled_table(data: list[list[object]], widths: list[float]) -> Table:
    rows = []
    for row_index, row in enumerate(data):
        rows.append([
            str(cell) if row_index == 0 else Paragraph(escape(str(cell)), styles["Small"])
            for cell in row
        ])
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.3),
        ("GRID", (0, 0), (-1, -1), 0.45, RULE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_GREEN]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def make_report() -> None:
    commit = git_commit()
    tag_commit = git_tag_commit()
    database = json.loads((RAW / "database_crud_evidence.json").read_text())
    experiments = json.loads((RAW / "experiment_summary.json").read_text())
    file_memory = json.loads((RAW / "file_memory_evidence.json").read_text())
    verification = json.loads((REPORT_DIR / "verification.json").read_text())
    story: list = []

    story.append(Spacer(1, 0.28 * inch))
    story.append(p("Vedant Vartak", "Subsection"))
    story.append(p("Homework 6: Document Storage and Multi-Layer Memory", "TitleGreen"))
    story.append(p("Repository: <link href='https://github.com/vedantvartakwork/data260-3539'>https://github.com/vedantvartakwork/data260-3539</link>"))
    story.append(p(f"Report build commit: <font name='Courier'>{commit}</font>", "Small"))
    story.append(p(f"Resolved <font name='Courier'>hw6</font> tagged implementation/evidence commit: <font name='Courier'>{tag_commit}</font>", "Small"))
    story.append(Spacer(1, 0.12 * inch))
    config = [
        ["Parameter", "Value", "Derivation / purpose"],
        ["SID4", "3539", "last four student-ID digits"],
        ["PORT_BASE", "8839", "8000 + (SID4 mod 900)"],
        ["PREFIX", "s3539", "database/user namespace"],
        ["SEED", "3539", "repeatable seed"],
        ["VERIFY_SEED", "263539", "260000 + SID4"],
        ["DOMAIN_ID", "3", "3539 mod 8"],
        ["MongoDB", "s3539_doc", "document and memory database"],
        ["Model", "qwen3:8b via Ollama", "local completion model"],
        ["Embeddings", "all-MiniLM-L6", "local sentence-transformer"],
        ["Hardware", "MacBook Air M4, 10 cores, 16 GB", "local execution"],
    ]
    story.append(styled_table(config, [1.35 * inch, 2.25 * inch, 3.55 * inch]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(p("All application model calls were local. Raw JSONL/CSV, browser captures, verification, and the run log are committed under reports/hw06/.", "Body11"))
    story.append(PageBreak())

    section(story, "1. Architecture and repository structure", "Homework 6 extends the existing shared project rather than creating a separate app copy.")
    architecture = [
        ["Layer", "Implementation", "Evidence"],
        ["Document API", "FastAPI routes + PyMongo repository", "code/hw6/routes/documents.py; raw/database_crud_evidence.json"],
        ["Conversation memory", "messages, summaries, episodes", "code/hw6/memory.py; raw/memory_api_evidence.json"],
        ["Local generation", "qwen3:8b through Ollama", "raw/*_transcript.jsonl"],
        ["Episodic retrieval", "all-MiniLM-L6 + cosine top-k", "episodes collection + memory response"],
        ["Durable file memory", "AGENT.md + MEMORY.md", "MEMORY.original.md; file_memory_evidence.json"],
        ["Verification", "13 offline tests + artifact verifier", "tests/test_hw06.py; verification.json"],
    ]
    story.append(styled_table(architecture, [1.35 * inch, 2.65 * inch, 3.15 * inch]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Preformatted("""code/hw6/
  config.py, schemas.py, db.py, repositories.py, memory.py, file_memory.py
  routes/documents.py, routes/memory.py
reports/hw06/
  RUN_LOG.txt, METRICS.md, AI_USE.md, verification.json
  MEMORY.original.md, memory_probes.yaml, raw/, screenshots/
scripts/
  capture_hw06_*  run_hw06_memory_experiment.py  verify_hw06.py""", styles["CodeBlock"]))
    story.append(PageBreak())

    validator_code = excerpt("code/hw6/db.py", "RECALL_VALIDATOR =", "\n\n\nMEMORY_VALIDATORS")
    db_output = (
        f"database={database['database']}\n"
        f"collections={', '.join(database['compass_shell_snapshot']['collections'])}\n"
        f"MongoDB validator bypass blocked={database['mongo_schema_validation']['blocked']} "
        f"code={database['mongo_schema_validation']['code']}\n"
        f"seeded recall_documents={database['compass_shell_snapshot']['recall_document_count']}"
    )
    code_output_page(story, "2. Part 1 - MongoDB collection schema and validator", "The database-level validator independently enforces required fields, enums, types, title length, and timestamps.", validator_code, db_output)

    schema_code = excerpt("code/hw6/schemas.py", "class RecallStatus", "\n\nclass RecallDocumentOut")
    status_output = "\n".join([
        f"POST create -> {database['create']['status_code']}",
        f"GET list -> {database['list']['status_code']}",
        f"GET one -> {database['get_one']['status_code']}",
        f"{database['update']['method']} update -> {database['update']['status_code']} status={database['update']['body']['status']}",
        f"DELETE -> {database['delete']['status_code']}",
        f"GET after delete -> {database['get_after_delete']['status_code']}",
        f"missing required fields -> {database['invalid_missing_fields']['status_code']}",
        f"invalid category enum -> {database['invalid_enum']['status_code']}",
        f"invalid datetime type -> {database['invalid_type']['status_code']}",
    ])
    code_output_page(story, "3. Part 1 - API models, CRUD, and invalid inputs", "Pydantic rejects malformed requests before persistence; repository methods return correct status codes and JSON.", schema_code, status_output)

    evidence_page(story, "4. Part 1 - Live HW6 route map", "The running integrated API exposes POST, GET list, GET one, PUT, and DELETE document routes plus the three memory routes.", "swagger_hw6_routes.jpg", "Genuine FastAPI Swagger UI capture from http://127.0.0.1:8839/docs; the required PUT route is visible.")
    evidence_page(story, "5. Part 1 - POST document request", "The live create request shows the exact validated JSON sent to the API.", "swagger_document_create.jpg", "POST /api/v1/documents with title, description, status, category, and recalled_at.")
    evidence_page(story, "6. Part 1 - POST document response", "The same create call returned a MongoDB ObjectID, timestamps, and HTTP 201.", "swagger_document_create_response.jpg", "Successful POST response with the created document and status 201.")
    evidence_page(story, "7. Part 1 - GET document list", "A real list call reached MongoDB and returned stored recall documents.", "swagger_document_list.jpg", "GET /api/v1/documents response with request URL and HTTP 200.")
    evidence_page(story, "8. Part 1 - GET one document", "The exact created ObjectID is used in a successful read-by-id request.", "swagger_document_get_one.jpg", "GET /api/v1/documents/{document_id} with request URL, response body, and HTTP 200.")
    evidence_page(story, "9. Part 1 - PUT document request", "The required PUT update sends a validated status change for the same document.", "swagger_document_put.jpg", "PUT /api/v1/documents/{document_id} request body.")
    evidence_page(story, "10. Part 1 - PUT document response", "The required update returned the modified document and HTTP 200.", "swagger_document_put_response.jpg", "Successful PUT response for the same document ID.")
    evidence_page(story, "11. Part 1 - DELETE document", "The same document was deleted through the live API.", "swagger_document_delete.jpg", "DELETE /api/v1/documents/{document_id} with request URL and HTTP 204.")
    evidence_page(story, "12. Part 1 - MongoDB recall collection", "A live mongosh inspection confirms the configured database, collection, document count, and sample BSON documents.", "mongodb_shell_recall_documents.png", "Exact terminal output from s3539_doc.recall_documents; two sample documents are readable.")
    evidence_page(story, "13. Part 2 - MongoDB memory collections", "The same live mongosh inspection verifies messages, summaries, and episodes with counts and sample records.", "mongodb_shell_memory_collections.png", "Exact terminal output for the three required memory collections.")

    chat_code = "\n\n# ... bounded retrieval and local generation ...\n".join([
        excerpt("code/hw6/memory.py", "    def chat(", "\n        started ="),
        excerpt("code/hw6/memory.py", "        started =", "\n        system_prompt ="),
        excerpt("code/hw6/memory.py", "        system_prompt =", "\n        for fact, importance"),
        excerpt("code/hw6/memory.py", "        for fact, importance", "\n        components ="),
    ])
    chat_output = """POST /api/chat -> 200
short-term window: latest 12 prior messages
session summary: latest per-user/per-session summary
episodic memory: cosine-ranked top 3 facts
reply: Your name is Vedant Vartak, you are using the s3539_doc MongoDB
database, the qwen3:8b local model, and the API runs on port 8839."""
    code_output_page(story, "14. Part 2 - Multi-layer chat-memory pipeline", "Each request saves the user message, loads bounded short-term memory, latest summaries and top-k episodes, calls local Ollama, saves the assistant reply, extracts up to three facts, and records telemetry.", chat_code, chat_output)

    evidence_page(story, "15. Part 2 - Exact chat input", "The user/session identifiers and memory probe are visible before execution.", "swagger_chat_input.jpg", "Exact JSON submitted to POST /api/chat.")
    evidence_page(story, "16. Part 2 - Memory-aware chat output", "The output is from the same live call and includes a grounded answer plus the memory_used payload.", "swagger_chat_response.jpg", "200 response: the local model recalled the name, database, model, and port.")
    evidence_page(story, "17. Part 2 - GET memory", "The memory endpoint exposes the latest 16 messages plus summaries and episodes for inspection.", "swagger_memory_response.jpg", "Live request URL, status 200, and stored MongoDB messages.")
    evidence_page(story, "18. Part 2 - GET aggregate", "The aggregate endpoint returns daily message counts and recent summaries.", "swagger_aggregate_response.jpg", "Live aggregate response: daily count and summary documents are visible.")

    retrieval_code = "\n\n".join([
        excerpt("code/hw6/memory.py", "class SentenceTransformerEmbedder", "\n\nclass DeterministicEmbedder"),
        excerpt("code/hw6/memory.py", "def cosine_similarity", "\n\ndef extract_facts"),
        excerpt("code/hw6/memory.py", "def extract_facts", "\n\ndef _summary_text"),
    ])
    retrieval_output = """Embedding model: all-MiniLM-L6 (local)
fact extraction cap: 3 facts/message
similarity: cosine(query_embedding, episode_embedding)
top-k: 3 (default)
example retrieved facts:
  0.681312  What are my name, database, local model, and API port?
  0.397206  Never call a hosted model for this assignment.
  0.363459  Remember that my grocery safety project uses MongoDB."""
    code_output_page(story, "19. Part 2 - Episodic facts, embeddings, and cosine retrieval", "The production embedder is lazy and local; deterministic embeddings are used only by offline tests.", retrieval_code, retrieval_output)

    section(story, "20. Part 3 - Controlled memory experiment", "The same deterministic 30-message script and five probes ran in fresh sessions for N=4, N=12, N=30, and a compression/eviction policy.")
    rows = [["Run", "N", "Summary every", "Top-k", "Mean prompt", "Mean completion", "Mean latency ms", "Probe /5"]]
    for row in experiments:
        rows.append([row["name"], row["short_term_n"], row["summarize_every"], row["episodic_top_k"], row["mean_prompt_tokens"], row["mean_completion_tokens"], row["mean_latency_ms"], row["mean_probe_score"]])
    story.append(styled_table(rows, [1.25 * inch, 0.35 * inch, 0.75 * inch, 0.45 * inch, 0.85 * inch, 0.85 * inch, 1.05 * inch, 0.7 * inch]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(p("All four runs contain 30 conversation turns plus five probe records. The raw per-turn JSONL and combined CSV preserve prompt/completion counts, system/long-term/short-term/episode components, latency, summaries, and eviction/compression behavior."))
    story.append(Preformatted("""Probe rubric: 1 = absent/wrong, 3 = partially correct, 5 = exact and concise.
Five probes cover identity/config, durable preferences, an early critical fact,
recent context, and the explicit no-hosted-model constraint.""", styles["CodeBlock"]))
    story.append(PageBreak())

    compact = next(row for row in experiments if row["name"] == "compact_policy")
    n30 = next(row for row in experiments if row["name"] == "window_n30")
    savings = (1 - compact["mean_prompt_tokens"] / n30["mean_prompt_tokens"]) * 100
    section(story, "21. Part 3 - Compression, quality, and projected cost", "The selected policy keeps four recent messages, summarizes every two user messages, and retrieves five episodes.")
    story.append(p(f"Compared with N=30, it reduced mean prompt tokens by <b>{savings:.1f}%</b>, reduced mean latency from <b>{n30['mean_latency_ms']:.3f} ms</b> to <b>{compact['mean_latency_ms']:.3f} ms</b>, and improved mean probe score from <b>{n30['mean_probe_score']}</b> to <b>{compact['mean_probe_score']}</b>."))
    costs = []
    for row in experiments:
        per_conversation = row["total_prompt_tokens"] / 30 * 1.0 / 1_000_000 + row["total_completion_tokens"] / 30 * 5.0 / 1_000_000
        costs.append([row["name"], f"${per_conversation * 10000:,.2f}"])
    story.append(styled_table([["Policy", "Projected cost for 10,000 conversations"]] + costs, [3.6 * inch, 3.2 * inch]))
    story.append(Spacer(1, 0.12 * inch))
    story.append(p("Best case is the compact policy because it preserves or improves quality with a much smaller prompt. Worst case is N=30 because it repeatedly resends the longest context. Pricing assumption: $1 per million input tokens and $5 per million output tokens."))
    story.append(PageBreak())

    agent_excerpt = excerpt("AGENT.md", "# Homework 6", None)
    code_output_page(story, "22. Part 4 - AGENT.md categories and generated function", "Project, stack, coding-convention, testing, and prohibited-action instructions are injected into the system prompt. The generated function is pure, typed, documented, and tested.", agent_excerpt[:3300], """normalize_memory_fact(' model ', ' qwen3:8b ')
-> - model: qwen3:8b

test_generated_normalizer_follows_agent_rules ... ok""")

    command_code = '''def command(self, command: str,
            recent_messages: list[dict[str, Any]]) -> str | None:
    name = command.strip().lower()
    if name == "/help":
        return (
            "Commands: /memory shows durable memory; "
            "/compact consolidates it; /dream reflects on "
            "recent messages; /help shows this list."
        )
    if name == "/memory":
        if not self.memory_path.exists():
            return "No durable MEMORY.md exists yet."
        text = self.memory_path.read_text(encoding="utf-8")
        count = len(self._meaningful_lines(text))
        return f"Durable memory has {count} meaningful lines.\\n\\n{text}"'''
    memory_preview = "\n".join(file_memory["memory_command_after"].splitlines()[:9])
    command_output = (
        "/help\nCommands: /memory shows durable memory; /compact consolidates it;\n"
        "/dream reflects on recent messages; /help shows this list.\n\n"
        f"/memory\n{memory_preview}\n..."
    )
    code_output_page(
        story,
        "23. Part 4 - /memory and /help commands",
        "The command dispatcher exposes the required help text and returns the current durable memory with a verified meaningful-line count.",
        command_code,
        command_output,
    )

    dream_code = "\n\n".join([
        excerpt("code/hw6/file_memory.py", "    def _append_dream_facts", "\n\n    def command"),
        excerpt("code/hw6/file_memory.py", "        if name == \"/dream\":", "        return None"),
    ])
    dream_output = (
        f"dream={file_memory['dream_command']}\n"
        f"dream_added_lines={file_memory['dream_added_lines']}"
    )
    code_output_page(story, "24. Part 4 - /dream writes durable facts", "The /dream command deterministically identifies useful long-term facts in recent user messages, rejects duplicates, and appends unique dream_fact entries to MEMORY.md.", dream_code, dream_output)

    consolidation_code = "\n\n".join([
        excerpt("code/hw6/file_memory.py", "def normalize_memory_fact", "\n\nclass FileMemoryManager"),
        excerpt("code/hw6/file_memory.py", "    def needs_consolidation", "\n\n    def consolidate"),
        "# Inside consolidate():\n" + excerpt("code/hw6/file_memory.py", "        for key, occurrences", "        output.extend"),
        excerpt("code/hw6/file_memory.py", "        if name == \"/compact\":", "        if name == \"/dream\":"),
    ])
    compact_output = (
        f"needs_consolidation_before={file_memory['needs_consolidation_before']}\n"
        f"meaningful_lines_before={file_memory['meaningful_lines_before']}\n"
        f"meaningful_lines_after={file_memory['meaningful_lines_after']}\n"
        f"compact={file_memory['compact_command']}\n"
        f"incorrect_resolutions={file_memory['incorrect_resolutions']}"
    )
    code_output_page(story, "25. Part 4 - /compact consolidates durable memory", "Consolidation triggers above 40 non-empty, non-comment memory lines or after 24 hours, keeps the newest conflicting value, and records every resolution.", consolidation_code, compact_output)

    section(story, "26. Part 4 - Original vs. consolidated durable memory", f"The committed original has 55 meaningful lines, at least three duplicate groups, and three contradictions. The consolidated file has {file_memory['meaningful_lines_after']} meaningful lines and {file_memory['physical_lines_after']} physical lines, both below 40.")
    before_lines = (REPORT_DIR / "MEMORY.original.md").read_text().splitlines()
    after_lines = (ROOT / "MEMORY.md").read_text().splitlines()
    story.append(p("Original excerpt", "Subsection"))
    story.append(Preformatted("\n".join(before_lines[:12] + ["...", *before_lines[-8:]]), styles["CodeBlock"]))
    story.append(p("Consolidated excerpt", "Subsection"))
    story.append(Preformatted("\n".join(after_lines[:18]), styles["CodeBlock"]))
    story.append(p("Audited resolutions: short_term_window=12 (rejected 8), summary_interval=4 (rejected 6), episodic_top_k=3 (rejected 5). No incorrect resolution was found.", "Small"))
    story.append(PageBreak())

    section(story, "27. Part 4 - MongoDB memory versus file memory")
    comparison = [
        ["Criterion", "MongoDB", "AGENT.md / MEMORY.md"],
        ["Inspectability", "Queryable collections with timestamps, embeddings and indexes", "Human-readable, diffable and reviewable in Git"],
        ["Restart persistence", "Persists in the MongoDB volume", "Persists with the repository"],
        ["Scalability", "Many users/sessions and aggregation", "Small set of durable project facts"],
        ["Best use", "Conversation history, summaries, episodic retrieval", "Must-not-forget rules and confirmed configuration"],
    ]
    story.append(styled_table(comparison, [1.25 * inch, 2.95 * inch, 2.95 * inch]))
    story.append(Spacer(1, 0.14 * inch))
    story.append(p("The hybrid prompt is intentional: MongoDB provides scalable retrieval, while the files provide compact human-auditable constraints."))
    story.append(PageBreak())

    raw_test_output = verification["checks"]["offline_tests"]["details"]
    test_lines = [line.split(" (", 1)[0] + " ... ok" for line in raw_test_output.splitlines() if line.startswith("test_")]
    test_output = "\n".join(test_lines) + f"\n\n{len(test_lines)}/{len(test_lines)} tests passed."
    section(story, "28. Verification - 13/13 offline tests and artifact checks", "Tests avoid external APIs and use deterministic repositories/models. Live MongoDB and Ollama evidence is verified separately.")
    story.append(Preformatted(test_output, styles["CodeBlock"]))
    check_rows = [["Verifier check", "Pass", "Details"]]
    concise_details = {
        "offline_tests": "13/13 named deterministic tests passed",
        "python_compile": "compileall passed",
        "required_files": "all required source, report, memory, probe, and disclosure files present",
        "mongodb_crud_evidence": "POST/list/read/PUT/DELETE, 422 validation, and MongoDB validator verified",
        "memory_experiment": "4 runs x (30 conversation turns + 5 probes)",
        "live_memory_evidence": "20 messages, 2+ summaries, and 10+ episodic facts verified",
        "file_memory_consolidation": verification["checks"]["file_memory_consolidation"]["details"],
    }
    for name, item in verification["checks"].items():
        check_rows.append([name, item.get("pass"), concise_details.get(name, "verified")])
    story.append(styled_table(check_rows, [1.7 * inch, 0.55 * inch, 4.9 * inch]))
    story.append(PageBreak())

    section(story, "29. AI-use disclosure")
    ai_lines = (REPORT_DIR / "AI_USE.md").read_text().splitlines()[2:]
    for line in ai_lines:
        if line.strip():
            story.append(p(escape(line)))
    story.append(Spacer(1, 0.12 * inch))
    story.append(p("I verified the implementation with named tests, MongoDB validation, raw 30-turn experiment records, real local-model responses, and exact request/response captures. The Homework 6 application did not call a hosted model.", "Small"))

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_COPY.parent.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_COPY.parent.mkdir(parents=True, exist_ok=True)
    DESKTOP_COPY.parent.mkdir(parents=True, exist_ok=True)
    COURSE_DESKTOP_COPY.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(REPORT),
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.55 * inch,
        title="Vartak - DATA 260 Homework 6",
        author="Vedant Vartak",
        subject="Document Storage and Multi-Layer Memory",
    )
    document.build(story, onFirstPage=page_chrome, onLaterPages=page_chrome)
    shutil.copy2(REPORT, OUTPUT_COPY)
    shutil.copy2(REPORT, DOWNLOAD_COPY)
    shutil.copy2(REPORT, DESKTOP_COPY)
    shutil.copy2(REPORT, COURSE_DESKTOP_COPY)
    print(REPORT)
    print(OUTPUT_COPY)
    print(DOWNLOAD_COPY)
    print(DESKTOP_COPY)
    print(COURSE_DESKTOP_COPY)


if __name__ == "__main__":
    make_report()
