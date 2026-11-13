"""Streamlit operations dashboard for HW10."""

from __future__ import annotations

import json
from code.hw10.config import settings
from code.hw10.tracing import read_jsonl
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="HW10 Recall Operations", layout="wide")


@st.cache_data(ttl=5)
def load_jsonl(path: str) -> list[dict]:
    return read_jsonl(Path(path))


@st.cache_data(ttl=5)
def load_json(path: str) -> dict:
    target = Path(path)
    return json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}


def summary_page() -> None:
    st.title("Recall Pipeline Operations")
    requests = load_jsonl(str(settings.raw_dir / "requests.jsonl"))
    if not requests:
        st.warning("No request telemetry found. Run scripts/run_hw10_experiments.py.")
        return
    frame = pd.DataFrame(requests)
    hits = int((frame["cache_result"] == "hit").sum())
    misses = int((frame["cache_result"] == "miss").sum())
    errors = int((frame["status"] == "error").sum())
    columns = st.columns(4)
    columns[0].metric("Recent requests", len(frame))
    columns[1].metric("Cache hit rate", f"{hits / len(frame):.1%}", f"{hits} hit / {misses} miss")
    columns[2].metric("Error rate", f"{errors / len(frame):.1%}", f"{errors} errors")
    columns[3].metric("Mean E2E latency", f"{frame['e2e_latency_ms'].mean():.2f} ms")
    st.caption(
        "Window: complete saved HW10 experiment run. Sources: reports/hw10/raw/requests.jsonl "
        "and reports/hw10/raw/spans.jsonl. Cache hits and misses are counted separately."
    )
    st.subheader("Request telemetry")
    st.dataframe(
        frame[["timestamp", "trace_id", "cache_result", "status", "e2e_latency_ms"]],
        width="stretch",
    )


def evaluation_page() -> None:
    st.title("Evaluation and Judge Validation")
    summary = load_json(str(settings.raw_dir / "evaluation_summary.json"))
    raw = load_json(str(settings.raw_dir / "judge_validation.json"))
    if not summary:
        st.warning("Evaluation artifacts are not available yet.")
        return
    st.subheader("Planner / Writer / Reviewer end-to-end case")
    e2e = summary["end_to_end"]
    rows = [
        {"Stage": "Planner", "Score": e2e["plan"]["score"], "Reason": e2e["plan"]["reason"]},
        {"Stage": "Writer", "Score": e2e["writer"]["score"], "Reason": e2e["writer"]["reason"]},
        {
            "Stage": "Reviewer final",
            "Score": e2e["final"]["score"],
            "Reason": e2e["final"]["reason"],
        },
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.write(f"**Final minus draft:** {e2e['improvement']:+d}. {e2e['interpretation']}")
    st.subheader("20-case judge validation")
    a, b, c = st.columns(3)
    a.metric("Spearman correlation", f"{summary['spearman']:.3f}")
    b.metric("Mean absolute difference", f"{summary['mean_absolute_difference']:.3f}")
    c.metric("Changed-score frequency", f"{summary['changed_score_frequency']:.1%}")
    st.write(summary["deployment_gate"])
    if raw.get("cases"):
        st.dataframe(pd.DataFrame(raw["cases"]), width="stretch", hide_index=True)


def trace_page() -> None:
    st.title("Trace Lookup")
    traces = load_json(str(settings.raw_dir / "trace_examples.json"))
    spans = load_jsonl(str(settings.raw_dir / "spans.jsonl"))
    defaults = list(traces.values()) if traces else []
    default = defaults[0] if defaults else ""
    trace_id = st.text_input("trace_id", value=default)
    selected = [span for span in spans if span.get("trace_id") == trace_id]
    if not selected:
        st.info("Enter a saved trace ID. Example IDs are stored in trace_examples.json.")
        return
    path = " → ".join(span["stage"] for span in selected)
    st.write(f"**Journey:** {path}")
    if selected[0].get("cache_result"):
        st.write(f"**Cache path:** {selected[0]['cache_result']}")
    failures = [span for span in selected if span.get("error")]
    if failures:
        st.error(f"Failed stage: {failures[0]['stage']} — {failures[0]['error']}")
    st.dataframe(
        pd.DataFrame(selected)[["stage", "start", "end", "duration_ms", "status", "error"]],
        width="stretch",
        hide_index=True,
    )


page = st.sidebar.radio("Page", ["Summary", "Evaluation", "Trace Lookup"])
st.sidebar.caption(f"PREFIX={settings.prefix} · model={settings.model}")
if page == "Summary":
    summary_page()
elif page == "Evaluation":
    evaluation_page()
else:
    trace_page()
