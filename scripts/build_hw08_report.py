"""Build the DATA 260 Homework 8 report from verified source and raw evidence."""

from __future__ import annotations

import json
from pathlib import Path

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
REPORT = ROOT / "reports" / "hw08"
RAW = REPORT / "raw"
EVIDENCE = REPORT / "evidence"
OUTPUT = ROOT / "output" / "pdf" / "Vartak_HW8.pdf"
IMPLEMENTATION_HASH = "66ef001731bf57b75530c0c1da2d55ca8153e0a1"
REPO_URL = "https://github.com/vedantvartakwork/data260-3539"


def source(path: str, start: int, end: int) -> str:
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    return "\n".join(f"{n:>3}  {lines[n - 1]}" for n in range(start, min(end, len(lines)) + 1))


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=26,
        leading=31,
        alignment=TA_LEFT,
        textColor=colors.black,
        spaceAfter=18,
    )
)
styles.add(
    ParagraphStyle(
        name="H1x",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.black,
        spaceBefore=8,
        spaceAfter=9,
    )
)
styles.add(
    ParagraphStyle(
        name="H2x",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.black,
        spaceBefore=7,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="Bodyx",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.black,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        name="Smallx",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.black,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="Codex",
        fontName="Courier",
        fontSize=7.6,
        leading=9.4,
        textColor=colors.black,
        backColor=colors.HexColor("#f3f4f6"),
        borderColor=colors.HexColor("#9ca3af"),
        borderWidth=0.5,
        borderPadding=7,
        spaceBefore=5,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="Captionx",
        parent=styles["BodyText"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#374151"),
        spaceBefore=4,
        spaceAfter=8,
    )
)


def p(text: str, style: str = "Bodyx") -> Paragraph:
    return Paragraph(text, styles[style])


def code(text: str) -> Preformatted:
    return Preformatted(text, styles["Codex"])


def table(rows: list[list[str]], widths: list[float] | None = None) -> Table:
    data = [[p(str(cell), "Smallx") for cell in row] for row in rows]
    result = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#6b7280")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return result


def screenshot(name: str, caption: str, max_height: float = 6.2 * inch) -> list:
    path = EVIDENCE / name
    image = Image(str(path))
    max_width = 7.25 * inch
    scale = min(max_width / image.imageWidth, max_height / image.imageHeight)
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    return [image, p(caption, "Captionx")]


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#4b5563"))
    canvas.drawString(0.65 * inch, 0.38 * inch, "Vedant Vartak | DATA 260 Homework 8")
    canvas.drawRightString(7.85 * inch, 0.38 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build() -> None:
    verification = json.loads((REPORT / "verification.json").read_text(encoding="utf-8"))
    live = json.loads((RAW / "live_failure_experiments.json").read_text(encoding="utf-8"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        rightMargin=0.62 * inch,
        leftMargin=0.62 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.58 * inch,
        title="Vartak HW8 - Kafka and Event-Driven Agents",
        author="Vedant Vartak",
        subject="DATA 260 Homework 8",
    )
    story: list = []

    story.extend(
        [
            Spacer(1, 0.35 * inch),
            p("DATA 260 — HOMEWORK 8", "H2x"),
            p("Kafka Request/Response and Event-Driven Agent Pipelines", "CoverTitle"),
            p("Vedant Vartak", "H1x"),
            p(
                "This report documents the implemented Kafka RPC service the three-process agent pipeline and four live failure experiments. Every screenshot below was generated from the saved raw run evidence in <b>reports/hw08/raw</b>.",
                "Bodyx",
            ),
            Spacer(1, 0.12 * inch),
            table(
                [
                    ["Required item", "Submitted value"],
                    ["SID4 / PREFIX / PORT_BASE", "3539 / s3539 / 8839"],
                    ["SEED / VERIFY_SEED / DOMAIN_ID", "3539 / 263539 / 3"],
                    ["Hardware", "Apple M4 MacBook Air — 10 cores — 16 GB RAM"],
                    ["Local model", "qwen3:8b"],
                    ["Repository", REPO_URL],
                    ["Verified implementation commit", IMPLEMENTATION_HASH],
                    ["Submission reference", "hw8 (authoritative Git tag)"],
                ],
                [2.2 * inch, 5.0 * inch],
            ),
            Spacer(1, 0.2 * inch),
            p("Verification summary", "H2x"),
            p(
                f"Automated verification passed {sum(1 for item in verification['checks'] if item['passed'])}/{len(verification['checks'])} checks. The suite includes 18 named unit tests plus direct inspection of the live Kafka failure-experiment JSON.",
                "Bodyx",
            ),
            p(
                "The verification hash identifies the exact implementation and live-evidence state that was tested. The final report packaging commit is the commit referenced by the published hw8 tag and can be resolved objectively with <b>git rev-parse hw8^{}</b>.",
                "Bodyx",
            ),
            p(
                "Collaborators: Sbnikitha and supriyaselvanganesan are the course collaborators associated with this repository.",
                "Bodyx",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("1. Requirement map and architecture", "H1x"),
            p(
                "The implementation uses Kafka in KRaft mode through Docker Compose. FastAPI acts as the client-facing process for the entity request/response flow. The recall worker owns an in-memory dictionary. Planner Writer and Reviewer are separate processes with independent consumer groups.",
                "Bodyx",
            ),
            table(
                [
                    ["Assignment requirement", "Implementation / evidence"],
                    [
                        "Entity request/response",
                        "code/hw8/rpc.py service.py worker.py plus live flow",
                    ],
                    [
                        "Three-process agent pipeline",
                        "agent_worker.py and planner/writer/reviewer.py plus live stage logs",
                    ],
                    ["Duplicate delivery", "correlation-ID response cache plus live replay"],
                    ["Consumer restart", "manual commit after publish plus live stop/start"],
                    [
                        "Poison message",
                        "three attempts then s3539_dead_letter plus live continuation",
                    ],
                    ["Ordering", "20 messages unkeyed vs keyed with two live Writers"],
                    [
                        "Raw and verification artifacts",
                        "reports/hw08/raw and verification.json",
                    ],
                ],
                [2.25 * inch, 4.95 * inch],
            ),
            p("Kafka topics", "H2x"),
            table(
                [
                    ["Topic", "Partitions", "Purpose"],
                    ["s3539_entity_requests", "1", "CREATE_RECALL and GET_RECALL requests"],
                    ["s3539_entity_responses", "1", "Correlated entity responses"],
                    ["s3539_inbox", "1", "User questions for Planner"],
                    ["s3539_tasks", "2", "Planner output and Writer scaling/ordering experiment"],
                    ["s3539_drafts", "1", "Writer drafts for Reviewer"],
                    ["s3539_final", "1", "Approved final response"],
                    ["s3539_dead_letter", "1", "Poison records after bounded retries"],
                ],
                [2.2 * inch, 0.8 * inch, 4.2 * inch],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("2. Reproducible Docker and Kafka setup", "H1x"),
            p(
                "The Compose file starts Kafka FastAPI one recall worker Planner two Writer instances and Reviewer. The initialization container creates the seven exact topics and gives s3539_tasks two partitions. The stack is reproducible with make hw8-up and removed with make hw8-down.",
                "Bodyx",
            ),
            code(
                source("docker-compose.hw8.yml", 1, 25)
                + "\n...\n"
                + source("docker-compose.hw8.yml", 76, 102)
            ),
            PageBreak(),
            p("2.1 Live container evidence", "H2x"),
            *screenshot(
                "01_docker_ps.png",
                "Figure 1. Live Docker Compose state. Kafka is healthy all six application processes are running and topic initialization exited successfully.",
            ),
            *screenshot(
                "10_startup_logs.png",
                "Figure 2. Required startup evidence: the Worker consumer is ready FastAPI completed startup port 8839 is listening and the health request returned HTTP 200.",
                max_height=2.4 * inch,
            ),
            p(
                "The host URL is http://127.0.0.1:8839. Docker maps it to the Uvicorn listener at container address 0.0.0.0:8839. The raw command output is saved as reports/hw08/raw/docker_ps.txt. Service logs and exact topic creation output are saved in kafka_service_logs.txt.",
                "Bodyx",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("3. Part 1 — Kafka request/response", "H1x"),
            p(
                "The client creates a UUID correlation_id includes reply_to operation and data and publishes JSON to s3539_entity_requests. A background response consumer resolves the matching Future only when the returned correlation_id matches. The worker validates every field performs CREATE_RECALL or GET_RECALL and publishes a clean success or error response.",
                "Bodyx",
            ),
            p("3.1 Domain validation and idempotent worker", "H2x"),
            code(
                source("code/hw8/service.py", 31, 54)
                + "\n...\n"
                + source("code/hw8/service.py", 56, 101)
            ),
            PageBreak(),
            p("3.2 Correlation-aware RPC client", "H2x"),
            code(source("code/hw8/rpc.py", 53, 101)),
            PageBreak(),
            p("3.3 Manual worker response and offset commit", "H2x"),
            code(source("code/hw8/worker.py", 23, 58)),
            p(
                "The record is committed only after the response is successfully sent. This is the at-least-once boundary used again in the failure experiment.",
                "Bodyx",
            ),
            PageBreak(),
            p("3.4 Complete live CREATE then GET run", "H2x"),
            *screenshot(
                "02_create_get.png",
                "Figure 3. One live call creates a UUID recall and a second call retrieves that same UUID. Each response preserves its own correlation ID.",
            ),
            p(
                "The input includes typed integer units accepted terms a valid email category product details and recall code. Unknown operations missing fields invalid units and invalid email values return explicit errors; the test suite covers each case.",
                "Bodyx",
            ),
            *screenshot(
                "07_rpc_message_flow.png",
                "Figure 4. The same correlation IDs appear in the FastAPI send the Worker receive and reply and the FastAPI receive for both CREATE_RECALL and GET_RECALL.",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("4. Part 2 — Three event-driven agent processes", "H1x"),
            p(
                "Planner reads s3539_inbox and sends a plan to s3539_tasks. Writer reads s3539_tasks and sends a draft to s3539_drafts. Reviewer reads s3539_drafts and sends the approved JSON to s3539_final. Each stage preserves correlation_id entity_key question and the accumulated journey array.",
                "Bodyx",
            ),
            p("4.1 Stage logic", "H2x"),
            code(source("code/hw8/pipeline.py", 9, 62)),
            p("4.2 Separate process entry points", "H2x"),
            code(
                source("code/hw8/planner.py", 1, 4)
                + "\n\n"
                + source("code/hw8/writer.py", 1, 4)
                + "\n\n"
                + source("code/hw8/reviewer.py", 1, 4)
            ),
            PageBreak(),
            p("4.3 Live end-to-end message journey", "H2x"),
            *screenshot(
                "03_agent_pipeline.png",
                "Figure 5. Live question sent to s3539_inbox and final approved JSON received from s3539_final with journey [planner writer reviewer].",
            ),
            *screenshot(
                "08_pipeline_stage_logs.png",
                "Figure 6. Matching correlation ID in Planner Writer and Reviewer receive/send lines proves the separate-process journey.",
            ),
            p(
                "The complete message includes the original question plan draft answer status correlation ID and entity key. This makes the full journey auditable without direct process-to-process calls.",
                "Bodyx",
            ),
            PageBreak(),
        ]
    )

    duplicate = live["duplicate_delivery"]
    story.extend(
        [
            p("5. Part 3A — Duplicate delivery and idempotency", "H1x"),
            p(
                "Failure: the same CREATE message may be delivered more than once. Without idempotency this creates duplicate entities. Fix: the recall service caches the completed response by correlation_id. A replay returns the original entity_id and adds duplicate=true without changing the entity dictionary.",
                "Bodyx",
            ),
            table(
                [
                    ["Observed item", "Live value"],
                    ["Correlation ID", duplicate["correlation_id"]],
                    ["First entity ID", duplicate["first"]["entity_id"]],
                    ["Replay entity ID", duplicate["replay"]["entity_id"]],
                    ["Replay marker", str(duplicate["replay"]["duplicate"])],
                    ["Result", "PASS — same entity returned"],
                ],
                [2.0 * inch, 5.2 * inch],
            ),
            *screenshot(
                "11_duplicate_log.png",
                "Figure 7. Direct duplicate-delivery log: the same correlation ID is received twice and both replies contain the same entity ID while the replay is marked duplicate=true.",
                max_height=3.2 * inch,
            ),
            PageBreak(),
            code(source("code/hw8/service.py", 47, 85)),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("6. Part 3B — Consumer killed mid-work", "H1x"),
            p(
                "Failure: an auto-committed task can disappear if the Writer dies after receiving it but before publishing the draft. Fix: enable_auto_commit is false and the worker commits only after the next-topic send succeeds. The live experiment sends an eight-second Writer task stops both Writer containers while it is in flight restarts them and observes an approved final response.",
                "Bodyx",
            ),
            code(source("code/hw8/agent_worker.py", 1, 95)),
            PageBreak(),
            *screenshot(
                "04_failures.png",
                "Figure 8. Machine-readable summaries of the three live failure experiments.",
                max_height=2.4 * inch,
            ),
            *screenshot(
                "12_restart_log.png",
                "Figure 9. Direct consumer-death log: both Writers stop during the delayed task the same partition and offset are received again after restart and commit occurs only after the downstream send.",
                max_height=4.4 * inch,
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("7. Part 3C — Poison message with bounded retries", "H1x"),
            p(
                "Failure: a blank question repeatedly fails Planner validation and can block the partition forever. Fix: each stage attempts processing at most three times then emits a dead-letter record with the original message failed_role correlation_id and error. It commits only after the DLQ publish. A later valid record then completes the full pipeline.",
                "Bodyx",
            ),
            table(
                [
                    ["Evidence", "Observed result"],
                    ["Poison correlation", live["poison_message"]["poison_correlation_id"]],
                    ["Attempts", "3"],
                    ["DLQ topic", "s3539_dead_letter"],
                    ["Error", live["poison_message"]["dead_letter"]["value"]["error"]],
                    ["Later message", "approved after poison record"],
                ],
                [2.0 * inch, 5.2 * inch],
            ),
            *screenshot(
                "13_poison_log.png",
                "Figure 10. Direct poison-message log: attempts 1/3 2/3 and 3/3 are followed by s3539_dead_letter and the later valid record proceeds through the pipeline.",
                max_height=3.5 * inch,
            ),
            PageBreak(),
            code(source("code/hw8/agent_worker.py", 52, 94)),
            p(
                "The service logs show PLANNER RETRY attempt=1/3 2/3 and 3/3 followed by PLANNER DEAD LETTER. They also show the next message being planned committed drafted reviewed and finalized.",
                "Bodyx",
            ),
            PageBreak(),
        ]
    )

    ordering = live["two_partitions_two_consumers"]
    story.extend(
        [
            p("8. Part 3D — Ordering across two partitions and two Writers", "H1x"),
            p(
                "Using VERIFY_SEED=263539 the script sends 20 numbered messages through s3539_tasks with two partitions and two Writer processes. Alternating deterministic delays make unkeyed work complete out of order. The corrected run uses one entity_key as the Kafka key. Kafka hashes every related message to partition 0 and preserves their input order.",
                "Bodyx",
            ),
            *screenshot(
                "05_ordering.png",
                "Figure 11. Required 20-message experiment: unkeyed completion is reordered; keyed completion is exactly 1 through 20 on one partition.",
            ),
            table(
                [
                    ["Case", "Processed order", "Result"],
                    [
                        "Unkeyed",
                        ", ".join(map(str, ordering["unkeyed_processed_order"])),
                        "Out of order",
                    ],
                    ["Keyed", ", ".join(map(str, ordering["keyed_processed_order"])), "In order"],
                ],
                [1.0 * inch, 5.2 * inch, 1.0 * inch],
            ),
            PageBreak(),
            p("8.1 Experiment implementation", "H2x"),
            code(
                source("scripts/run_hw08_live_failures.py", 142, 169)
                + "\n...\n"
                + source("scripts/run_hw08_live_failures.py", 174, 246)
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("9. Failure table and HW2 comparison", "H1x"),
            table(
                [
                    ["Scenario", "Before", "After"],
                    [
                        "Duplicate delivery",
                        "Replay creates another recall",
                        "Correlation cache returns original entity",
                    ],
                    [
                        "Consumer death",
                        "Work may be acknowledged too early",
                        "Commit occurs after downstream publish",
                    ],
                    [
                        "Poison message",
                        "Infinite retries block progress",
                        "Three tries then dead-letter; next record continues",
                    ],
                    [
                        "Ordering",
                        "Related records span partitions and reorder",
                        "Entity key pins records to one partition",
                    ],
                ],
                [1.35 * inch, 2.8 * inch, 3.05 * inch],
            ),
            p(
                "The HW2 graph executed nodes inside one process. That design was simple and deterministic but a process failure affected the whole graph and scaling a single stage was difficult. Kafka decouples the stages. Planner Writer and Reviewer can restart or scale independently and the durable log supports replay. The cost is explicit operational responsibility for idempotency manual commits poison-message policy consumer groups and partition keys.",
                "Bodyx",
            ),
            p(
                "This design is intentionally at-least-once. It avoids lost work by delaying commits and prevents duplicate side effects through idempotency rather than claiming exactly-once behavior.",
                "Bodyx",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("10. Tests verification and raw artifacts", "H1x"),
            *screenshot(
                "06_verification.png",
                "Figure 12. Final verification at implementation commit 66ef001731bf. All five checks pass including 18 unit tests and direct inspection of the live failure JSON.",
            ),
            p(
                "Test coverage includes exact topic names personal configuration successful CREATE/GET correlation preservation unknown entity unknown operation missing fields invalid units invalid email complete three-stage journey poison rejection idempotency manual-commit behavior dead-letter progress deterministic ordering and all four combined experiments.",
                "Bodyx",
            ),
            p(
                "The raw artifacts are not reconstructed from report prose. They are saved independently:",
                "Bodyx",
            ),
            table(
                [
                    ["Artifact", "Purpose"],
                    ["raw/homework_demo_live.txt", "Live CREATE/GET inputs and outputs"],
                    ["raw/agent_pipeline_live.txt", "Live inbox-to-final JSON"],
                    [
                        "raw/kafka_service_logs.txt",
                        "Topic creation worker retries commits and sends",
                    ],
                    [
                        "raw/live_failure_experiments.json",
                        "All live failure inputs outputs and PASS fields",
                    ],
                    ["raw/ordering_20_messages.csv", "Twenty-record unkeyed/keyed comparison"],
                    ["verification.json", "Configuration commit hash tests and pass/fail summary"],
                ],
                [2.4 * inch, 4.8 * inch],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("11. Supplemental JMeter plan", "H1x"),
            p(
                "The supplied JMeter instructions are supplemental to the Kafka requirements. I ran reports/hw08/jmeter/HW8_direct_100_users.jmx against POST /api/hw8/entities-direct with 100 threads a 10-second ramp JSON headers unique per-thread correlation IDs and an HTTP 201 assertion. This isolates direct FastAPI capacity from Kafka round-trip latency as requested by that handout.",
                "Bodyx",
            ),
            *screenshot(
                "09_jmeter.png",
                "Figure 13. Real JMeter non-GUI run: 100 samples 100 passed 0% errors average 4.04 ms and 10.13 requests per second during the configured ramp.",
            ),
            table(
                [
                    ["Samples", "Passed", "Error %", "Average", "Min", "Max", "p95", "Throughput"],
                    ["100", "100", "0.00", "4.04 ms", "1 ms", "15 ms", "8 ms", "10.13 req/s"],
                ],
                [
                    0.75 * inch,
                    0.7 * inch,
                    0.7 * inch,
                    0.9 * inch,
                    0.6 * inch,
                    0.6 * inch,
                    0.6 * inch,
                    1.0 * inch,
                ],
            ),
            p(
                "The editable plan is saved at reports/hw08/jmeter/HW8_direct_100_users.jmx. Raw per-request samples are saved in reports/hw08/raw/jmeter_100_users.jtl and the summarized values are in jmeter_summary.json.",
                "Bodyx",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("12. Reproduction commands", "H1x"),
            code(
                "make hw8-up\n"
                ".venv/bin/python -m code.hw8.homework_demo\n"
                ".venv/bin/python -m code.hw8.send_question\n"
                ".venv/bin/python scripts/run_hw08_live_failures.py\n"
                "make experiment-hw8\n"
                "make test-hw8\n"
                "make verify-hw08\n"
                "make hw8-down"
            ),
            p(
                "The live failure script is destructive only to the two Writer containers inside the dedicated data260-hw8 Compose project. It stops and restarts them as part of the required recovery demonstration. No database from another homework is modified.",
                "Bodyx",
            ),
            p("13. AI-use disclosure", "H1x"),
            p("1. I used an AI assistant to help debug code and organize the report.", "Bodyx"),
            p(
                "2. I independently checked the required topic names and correlation ID flow against the assignment.",
                "Bodyx",
            ),
            p(
                "3. I found mistakes by running the automated tests and comparing the saved JSON logs with the requirements.",
                "Bodyx",
            ),
            p(
                "4. I corrected the message validation and added bounded retry idempotency and ordering checks.",
                "Bodyx",
            ),
            p("14. Submission contents", "H1x"),
            p(
                "The hw8 tag contains the implementation Docker configuration scripts tests report raw evidence CSV JMeter plan METRICS.md RUN_LOG.txt AI_USE.md and verification.json. The report filename is Vartak_HW8.pdf.",
                "Bodyx",
            ),
        ]
    )

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    build()
