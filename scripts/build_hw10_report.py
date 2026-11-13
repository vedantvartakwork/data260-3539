#!/usr/bin/env python3
"""Build the HW10 report from source code and frozen raw artifacts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

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
REPORT = ROOT / "reports" / "hw10"
RAW = REPORT / "raw"
EVIDENCE = REPORT / "evidence"
OUTPUT = ROOT / "output" / "pdf" / "Vartak_HW10.pdf"
REPO_URL = "https://github.com/vedantvartakwork/data260-3539"


def git_value(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def source(path: str, start: int, end: int) -> str:
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    return "\n".join(
        f"{number:>3}  {lines[number - 1]}" for number in range(start, min(end, len(lines)) + 1)
    )


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="Cover",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=25,
        leading=30,
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
        spaceBefore=6,
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
        spaceBefore=5,
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
        fontSize=9.2,
        leading=11.5,
        textColor=colors.black,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="Codex",
        fontName="Courier",
        fontSize=8.4,
        leading=10.2,
        textColor=colors.black,
        backColor=colors.HexColor("#f3f3f3"),
        borderColor=colors.HexColor("#777777"),
        borderWidth=0.5,
        borderPadding=6,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="Captionx",
        parent=styles["BodyText"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=6,
    )
)


def p(text: str, style: str = "Bodyx") -> Paragraph:
    return Paragraph(text, styles[style])


def code(text: str) -> Preformatted:
    return Preformatted(escape(text), styles["Codex"])


def table(rows: list[list[object]], widths: list[float] | None = None) -> Table:
    data = [[p(escape(str(cell)), "Smallx") for cell in row] for row in rows]
    result = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6e6e6")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#777777")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return result


def screenshot(name: str, caption: str, max_height: float = 5.65 * inch) -> list:
    image = Image(str(EVIDENCE / name))
    max_width = 7.25 * inch
    scale = min(max_width / image.imageWidth, max_height / image.imageHeight)
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    return [image, p(caption, "Captionx")]


def new_page(story: list, title: str) -> None:
    if story:
        story.append(PageBreak())
    story.append(p(title, "H1x"))


def footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.black)
    canvas.drawString(0.62 * inch, 0.32 * inch, "Vedant Vartak | DATA 260 Homework 10")
    canvas.drawRightString(7.88 * inch, 0.32 * inch, f"Page {document.page}")
    canvas.restoreState()


def build() -> None:
    summary = json.loads((RAW / "evaluation_summary.json").read_text(encoding="utf-8"))
    validation = json.loads((RAW / "judge_validation.json").read_text(encoding="utf-8"))
    metrics = json.loads((RAW / "stage_metrics.json").read_text(encoding="utf-8"))
    e2e = json.loads((RAW / "end_to_end_case.json").read_text(encoding="utf-8"))
    verification = json.loads((REPORT / "verification.json").read_text(encoding="utf-8"))
    tag_hash = git_value("rev-parse", "hw10^{}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        rightMargin=0.62 * inch,
        leftMargin=0.62 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="Vartak HW10 - Evaluation and Observability",
        author="Vedant Vartak",
        subject="DATA 260 Homework 10",
    )
    story: list = []

    story.extend(
        [
            Spacer(1, 0.25 * inch),
            p("DATA 260 — HOMEWORK 10", "H2x"),
            p("Evaluation and Observability", "Cover"),
            p("Vedant Vartak", "H1x"),
            p(
                "This report extends the Kafka-style Planner Writer Reviewer pipeline and Redis semantic-cache behavior from Homeworks 8 and 9. It adds a Streamlit operations dashboard a bounded DeepEval GEval evaluator a frozen judge-validation experiment and correlation-preserving stage traces.",
                "Bodyx",
            ),
            table(
                [
                    ["Required item", "Submitted value"],
                    ["SID4 / PREFIX / PORT_BASE", "3539 / s3539 / 8839"],
                    ["SEED / VERIFY_SEED / DOMAIN_ID", "3539 / 263539 / 3"],
                    ["Hardware", "Apple M4 MacBook Air — 10 cores — 16 GB RAM"],
                    ["Local model", "qwen3:8b through Ollama; temperature 0; seed 263539"],
                    ["Repository", REPO_URL],
                    ["Resolved hw10 tagged commit", tag_hash],
                    ["Frozen human-label commit", summary["dataset_commit"]],
                    ["Verification", f"{verification['status']} — 8 tests and 11 semantic checks"],
                ],
                [2.25 * inch, 4.95 * inch],
            ),
            Spacer(1, 0.12 * inch),
            p(
                "Reproduction: <font name='Courier'>make experiment-hw10</font> then <font name='Courier'>make verify-hw10</font> and <font name='Courier'>make run-hw10-dashboard</font>.",
                "Bodyx",
            ),
        ]
    )

    new_page(story, "1. Requirement map and architecture")
    story.extend(
        [
            p(
                "The implementation uses the same correlation identifier as the trace identifier. No second request ID is introduced.",
                "Bodyx",
            ),
            table(
                [
                    ["Assignment part", "Implementation and saved evidence"],
                    [
                        "Part 1 — Streamlit dashboard",
                        "Summary Evaluation and Trace Lookup pages in code/hw10/dashboard.py; five real UI captures.",
                    ],
                    [
                        "Part 2 — automated evaluation",
                        "DeepEval GEval with a bounded local Ollama adapter; Planner Writer and Reviewer final scored on one correlated case.",
                    ],
                    [
                        "Part 3 — judge validation",
                        "20 frozen Writer drafts plus hand labels committed first; three identical-setting runs; Spearman MAD and repeatability.",
                    ],
                    [
                        "Part 4 — tracing",
                        "JSON spans for cache lookup inbox planner queue wait writer reviewer and evaluator; hit miss failure and 50-miss load evidence.",
                    ],
                ],
                [2.05 * inch, 5.15 * inch],
            ),
            Spacer(1, 0.08 * inch),
            p("Request flow", "H2x"),
            code(
                "question + correlation_id (= trace_id)\n"
                "  -> semantic cache lookup\n"
                "     HIT  -> cached answer + one cache_lookup span\n"
                "     MISS -> s3539.inbox -> Planner -> s3539.tasks\n"
                "          -> Writer -> s3539.drafts -> Reviewer -> s3539.final\n"
                "          -> GEval evaluator -> s3539.evaluations -> cache write"
            ),
            p(
                "The dashboard reads only saved JSON and JSONL telemetry. Its Summary page states the complete experiment-run window and the exact files used for request cache error and latency metrics.",
                "Bodyx",
            ),
        ]
    )

    new_page(story, "2. Streamlit summary page")
    story.extend(
        screenshot(
            "dashboard_summary.png",
            "Figure 1. Real Streamlit Summary page showing request count cache hit/miss rate error rate E2E latency window and data sources.",
        )
    )
    story.append(
        p(
            "The 53 requests are one live evaluated miss one exact cache hit one intentional failure and 50 confirmed performance misses.",
            "Bodyx",
        )
    )

    new_page(story, "3. Dashboard implementation")
    story.extend(
        [
            p("Cached data loaders and explicitly sourced metrics", "H2x"),
            code(source("code/hw10/dashboard.py", 13, 50)),
            p(
                "<font name='Courier'>@st.cache_data(ttl=5)</font> is appropriate because JSON files are small serializable data values that may change between experiment runs. No global connection object is created so <font name='Courier'>st.cache_resource</font> is not needed.",
                "Bodyx",
            ),
            p("Evaluation and trace routing", "H2x"),
            code(source("code/hw10/dashboard.py", 53, 80)),
            code(source("code/hw10/dashboard.py", 83, 115)),
        ]
    )

    new_page(story, "4. Cache-hit trace")
    story.extend(
        screenshot(
            "trace_cache_hit.png",
            "Figure 2. Exact semantic-cache hit trace. The cache-hit path is visibly distinct and ends after cache_lookup.",
        )
    )
    story.extend(
        [
            table(
                [
                    ["Trace type", "trace_id", "Observed journey"],
                    ["Cache hit", "trace-cache-hit-3539", "cache_lookup"],
                ],
                [1.2 * inch, 2.25 * inch, 3.75 * inch],
            ),
            p(
                "The answer matched the preceding live miss answer exactly; verification records cache_hit_trace_answer_matches=true.",
                "Bodyx",
            ),
        ]
    )

    new_page(story, "5. Successful cache-miss trace")
    story.extend(
        screenshot(
            "trace_cache_miss.png",
            "Figure 3. Successful cache miss showing ordered stages start/end times duration status and the long bounded local evaluator call.",
        )
    )
    story.append(
        table(
            [["Trace type", "trace_id"], ["Successful miss", "trace-live-eval-3539"]],
            [1.65 * inch, 5.55 * inch],
        )
    )

    new_page(story, "6. Failed trace")
    story.extend(
        screenshot(
            "trace_failure.png",
            "Figure 4. Intentional Writer failure with failed stage and complete error visible above the span table.",
        )
    )
    story.append(
        table(
            [
                ["Trace type", "trace_id", "Failure"],
                [
                    "Failed miss",
                    "trace-writer-failure-3539",
                    "writer — RuntimeError: intentional writer failure for trace evidence",
                ],
            ],
            [1.15 * inch, 2.2 * inch, 3.85 * inch],
        )
    )

    new_page(story, "7. Structured span implementation")
    story.extend(
        [
            p("Every stage emits the required fields even when an exception is raised.", "Bodyx"),
            code(source("code/hw10/tracing.py", 29, 70)),
            p("Single-ID propagation and distinct cache paths", "H2x"),
            code(source("code/hw10/pipeline.py", 34, 80)),
            p(
                "The same value is written to correlation_id and trace_id and used as the Kafka-style key. The failed trace proves that the context manager records the error before re-raising it.",
                "Bodyx",
            ),
        ]
    )

    new_page(story, "8. Full pipeline and evaluator stage")
    story.extend(
        [
            code(source("code/hw10/pipeline.py", 82, 120)),
            p(
                "Planner Writer and Reviewer reuse the Homework 8 process_stage logic and topic journey. The evaluator receives the complete correlated message and publishes the score payload to s3539.evaluations. A cache entry is written only after the miss path succeeds.",
                "Bodyx",
            ),
            p("Request-level telemetry", "H2x"),
            code(source("code/hw10/pipeline.py", 121, 136)),
        ]
    )

    new_page(story, "9. Bounded DeepEval GEval judge")
    story.extend(
        [
            p(
                "Local model adapter with timeout structured JSON deterministic settings and bounded output",
                "H2x",
            ),
            code(source("code/hw10/judge.py", 18, 71)),
            p("Five-level rubric and GEval invocation", "H2x"),
            code(source("code/hw10/judge.py", 74, 121)),
            p(
                "The judge is local qwen3:8b with temperature 0 VERIFY_SEED 263539 a 60-second HTTP timeout 2048-token context and 192-token output cap. DeepEval GEval owns the criteria rubric test-case construction and measurement.",
                "Bodyx",
            ),
        ]
    )

    new_page(story, "10. One end-to-end evaluated case")
    story.extend(
        [
            table(
                [
                    ["Field", "Saved value"],
                    ["trace_id / correlation_id", e2e["trace_id"]],
                    ["Question", e2e["question"]],
                    ["Metadata", json.dumps(e2e["metadata"], sort_keys=True)],
                    ["Plan", e2e["plan"]],
                    ["Writer draft", e2e["draft"]],
                    ["Reviewer final", e2e["answer"]],
                ],
                [1.45 * inch, 5.75 * inch],
            ),
            Spacer(1, 0.08 * inch),
            table(
                [
                    ["Stage", "Score", "Brief reason"],
                    [
                        "Plan Quality",
                        e2e["evaluation"]["plan"]["score"],
                        e2e["evaluation"]["plan"]["reason"],
                    ],
                    [
                        "Writer Helpfulness",
                        e2e["evaluation"]["writer"]["score"],
                        e2e["evaluation"]["writer"]["reason"],
                    ],
                    [
                        "Final Helpfulness",
                        e2e["evaluation"]["final"]["score"],
                        e2e["evaluation"]["final"]["reason"],
                    ],
                ],
                [1.45 * inch, 0.65 * inch, 5.1 * inch],
            ),
            p(
                f"Final minus draft = {e2e['evaluation']['improvement']:+d}. {e2e['evaluation']['interpretation']} The honest result is no measured improvement; the Reviewer preserved the Writer score rather than improving it.",
                "Bodyx",
            ),
        ]
    )

    new_page(story, "11. Evaluation dashboard evidence")
    story.extend(
        screenshot(
            "dashboard_evaluation.png",
            "Figure 5. Real Streamlit Evaluation page with stage scores Spearman MAD repeatability and deployment-gate interpretation.",
        )
    )

    new_page(story, "12. Frozen validation set and chronology")
    rows = [["Case", "Topic", "Human", "Judge 1", "Judge 2", "Judge 3"]]
    for item in validation["cases"][:10]:
        rows.append(
            [
                item["case_id"],
                item["topic"],
                item["human_label"],
                item["judge_run_1"],
                item["judge_run_2"],
                item["judge_run_3"],
            ]
        )
    story.extend(
        [
            p(
                f"The 20 Writer drafts and hand-assigned labels were committed at <font name='Courier'>{validation['dataset_commit']}</font> before judge implementation/results commit <font name='Courier'>{tag_hash}</font>. The labels were not generated by an LLM and were not changed after scoring.",
                "Bodyx",
            ),
            table(
                rows, [1.0 * inch, 1.55 * inch, 0.75 * inch, 0.75 * inch, 0.75 * inch, 0.75 * inch]
            ),
            p(
                "Cases 1–10 of the frozen set. Each row retains its original domain topic and the three raw judge scores.",
                "Captionx",
            ),
            p(
                "The raw JSON keeps the original question draft metadata and run-1 reason for every case. The CSV contains exactly one manually assigned integer label per case.",
                "Bodyx",
            ),
        ]
    )

    new_page(story, "13. Raw judge results — cases 11–20")
    rows = [["Case", "Topic", "Human", "Judge 1", "Judge 2", "Judge 3"]]
    for item in validation["cases"][10:]:
        rows.append(
            [
                item["case_id"],
                item["topic"],
                item["human_label"],
                item["judge_run_1"],
                item["judge_run_2"],
                item["judge_run_3"],
            ]
        )
    story.extend(
        [
            table(
                rows, [1.0 * inch, 1.55 * inch, 0.75 * inch, 0.75 * inch, 0.75 * inch, 0.75 * inch]
            ),
            Spacer(1, 0.12 * inch),
            table(
                [
                    ["Validation statistic", "Result"],
                    ["Spearman rank correlation", f"{summary['spearman']:.3f}"],
                    ["Mean absolute difference", f"{summary['mean_absolute_difference']:.3f}"],
                    ["Repeat runs", "3 with identical settings"],
                    [
                        "Changed cases / frequency",
                        f"{validation['repeatability']['changed_cases']} / {summary['changed_score_frequency']:.1%}",
                    ],
                    [
                        "Mean / max absolute change",
                        f"{summary['mean_absolute_change']:.3f} / {summary['max_absolute_change']:.3f}",
                    ],
                ],
                [3.4 * inch, 3.8 * inch],
            ),
            p(summary["deployment_gate"], "Bodyx"),
        ]
    )

    new_page(story, "14. Fifty confirmed cache misses and stage latency")
    stage_rows = [["Stage", "p50 ms", "p95 ms", "Mean ms", "% miss E2E"]]
    for item in metrics["stages"]:
        stage_rows.append(
            [
                item["stage"],
                f"{item['p50_ms']:.3f}",
                f"{item['p95_ms']:.3f}",
                f"{item['mean_ms']:.3f}",
                f"{item['percent_of_e2e']:.2f}%",
            ]
        )
    story.extend(
        [
            table(
                [
                    ["Required check", "Observed"],
                    ["New intentionally uncached questions", metrics["confirmed_cache_misses"]],
                    ["Requests served from cache", metrics["cache_served_count"]],
                    [
                        "Cache-miss E2E p50 / p95",
                        f"{metrics['e2e_p50_ms']:.3f} / {metrics['e2e_p95_ms']:.3f} ms",
                    ],
                    ["Cache-hit trace", "Reported separately: trace-cache-hit-3539"],
                ],
                [3.1 * inch, 4.1 * inch],
            ),
            Spacer(1, 0.1 * inch),
            table(stage_rows, [1.55 * inch, 1.15 * inch, 1.15 * inch, 1.15 * inch, 1.35 * inch]),
            Spacer(1, 0.1 * inch),
            p(metrics["optimization"], "Bodyx"),
            p(
                "The 50-request load experiment uses the frozen bounded evaluator replay for comparable stage timing. The real local GEval latency is retained separately in trace-live-eval-3539 and is visibly 29.7 seconds for three sequential model judgments.",
                "Bodyx",
            ),
        ]
    )

    new_page(story, "15. Experiment output")
    story.extend(
        screenshot(
            "experiment_summary.png",
            "Figure 6. Frozen experiment summary generated directly from evaluation_summary.json and stage_metrics.json.",
        )
    )

    new_page(story, "16. Automated tests and verification")
    story.extend(
        screenshot(
            "verification_terminal.png",
            "Figure 7. Final verification: ruff passed 8 tests passed dashboard AppTest passed and all semantic checks passed.",
        )
    )
    story.extend(
        [
            p("Offline tests include:", "H2x"),
            p(
                "configuration; 20-case dataset shape; required span fields; cache miss then hit; single trace ID and stage order; failed Writer trace; final-vs-draft scoring; and generated 50-miss artifacts.",
                "Bodyx",
            ),
            p(
                "verification.json stores SHA-256 digests for every raw artifact. The dashboard AppTest reported title Recall Pipeline Operations and zero exceptions.",
                "Bodyx",
            ),
        ]
    )

    new_page(story, "17. Reproduction and artifact manifest")
    artifact_rows = [["Artifact", "SHA-256"]]
    for name, digest in verification["artifact_sha256"].items():
        artifact_rows.append([name, digest])
    story.extend(
        [
            code(
                ".venv/bin/pip install -r requirements-hw10.txt\n"
                ".venv/bin/python scripts/run_hw10_experiments.py\n"
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests/test_hw10.py\n"
                ".venv/bin/python scripts/verify_hw10.py\n"
                "PYTHONPATH=. .venv/bin/streamlit run code/hw10/dashboard.py --server.port 8510"
            ),
            table(artifact_rows, [2.2 * inch, 5.0 * inch]),
            p(
                "The report is generated from these immutable raw files plus repository source. The human-label commit and final hw10 tag make the chronology independently verifiable.",
                "Bodyx",
            ),
        ]
    )

    new_page(story, "18. Interpretation limitations and AI use")
    story.extend(
        [
            p("Interpretation", "H2x"),
            p(
                "The Planner score of 1 reveals a coordination weakness: its outline is useful to the Writer but is not itself a user-facing answer. Writer and Reviewer both scored 3 so the Reviewer did not measurably improve this case. The judge aligns well with human ordering but MAD 0.55 shows that exact-score disagreement remains. Zero score changes under identical deterministic settings establish repeatability for this frozen set but do not prove robustness to prompt or model drift.",
                "Bodyx",
            ),
            p("Limitations and next evidence", "H2x"),
            p(
                "The in-memory Kafka analogue is used for deterministic offline replay while preserving the inherited s3539 topic journey. Before using the judge as a production gate I would collect multiple expert labels measure inter-rater agreement add adversarial and edge cases and rerun validation after every model or rubric change. Queue wait dominates the lightweight 50-miss replay and should be optimized first; real model evaluation latency is much larger and should remain asynchronous in production.",
                "Bodyx",
            ),
            p("AI-use disclosure", "H2x"),
            p(
                "I used an AI assistant to help debug code structure tests and report presentation. I checked the generated implementation and reran the saved experiments and verification commands. The 20 human labels were assigned before judge scoring and were not generated or changed by an LLM. The report identifies the local model raw artifacts and limitations so the evidence can be audited.",
                "Bodyx",
            ),
            p("Final checklist", "H2x"),
            table(
                [
                    ["Item", "Status"],
                    ["Four graded parts documented", "Complete"],
                    ["20 cases × 3 judge runs", "Complete"],
                    ["Hit miss failed traces", "Complete"],
                    ["50 confirmed misses", "Complete"],
                    ["Report length", "Below the 35-page limit"],
                    ["Submission filename", "Vartak_HW10.pdf"],
                ],
                [4.1 * inch, 3.1 * inch],
            ),
        ]
    )

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"saved={OUTPUT}")


if __name__ == "__main__":
    build()
