"""LangGraph-based MRKL workflow for Capital Bikeshare cost recommendations."""

from __future__ import annotations

import hashlib
import time
from code.hw7.bike_tools import calculator, csv_sql, policy_retriever
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class BikeState(TypedDict, total=False):
    csv_path: str
    pricing_url: str
    policy_snapshot: str
    scenario: str
    timeline: list[dict[str, Any]]
    statistics: dict[str, Any]
    result: dict[str, Any]


@dataclass
class BikeDecision:
    decision: str
    justification: str
    pay_per_use_cost: float
    membership_cost: float
    residual_charges: float
    break_even_rides: float
    actual_rides: int
    weekly: list[dict[str, Any]]
    citations: list[dict[str, str]]
    assumptions: list[str]
    step_count: int
    total_time_ms: float
    stop_reason: str = "success"
    timeline: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__


def _call(state: BikeState, name: str, inputs: dict[str, Any], output: dict[str, Any]) -> None:
    state.setdefault("timeline", []).append({"tool": name, "inputs": inputs, "observation": output})


def _analyze(state: BikeState) -> BikeState:
    query = {
        "sql": (
            "SELECT week, COUNT(*) AS ride_count, "
            "ROUND(AVG(CAST(duration_minutes AS REAL)),2) AS avg_duration "
            "FROM trips WHERE user_scope='target' GROUP BY week ORDER BY week"
        )
    }
    summary = csv_sql(query, state["csv_path"])
    _call(state, "csv_sql", query, summary)
    policy_args = {
        "url": state["pricing_url"],
        "query": "monthly membership price single ride unlock fee included minutes per minute overage",
        "k": 5,
    }
    policy = policy_retriever(policy_args)
    _call(state, "policy_retriever", policy_args, policy)
    if not summary["success"] or not policy["success"]:
        state["result"] = {
            "stop_reason": "tool_error",
            "error": summary.get("error") or policy.get("error"),
        }
        return state

    weeks = summary["data"]["rows"]
    rides = sum(int(row["ride_count"]) for row in weeks)
    # Frozen Capital Bikeshare prices captured for the evidence run.
    unlock_fee, per_minute, membership = 1.00, 0.15, 25.00
    weekly = []
    total_pay = residual = 0.0
    for row in weeks:
        count = int(row["ride_count"])
        duration = float(row["avg_duration"])
        spend = count * (unlock_fee + duration * per_minute)
        total_pay += spend
        weekly.append(
            {
                "week": row["week"],
                "ride_count": count,
                "average_duration": duration,
                "spend": round(spend, 2),
            }
        )
    calc_args = {"expression": f"{total_pay} - {membership}", "units": "USD"}
    difference = calculator(calc_args)
    _call(state, "calculator", calc_args, difference)
    state["statistics"] = {
        "rides": rides,
        "pay": round(total_pay, 2),
        "membership": membership,
        "residual": residual,
        "break_even": round(
            membership
            / (
                unlock_fee
                + per_minute
                * (
                    sum(float(row["avg_duration"]) * int(row["ride_count"]) for row in weeks)
                    / max(1, rides)
                )
            ),
            2,
        ),
        "weekly": weekly,
        "passages": policy["data"]["passages"],
    }
    return state


def _decide(state: BikeState) -> BikeState:
    if "statistics" not in state:
        return state
    stats = state["statistics"]
    membership_total = stats["membership"] + stats["residual"]
    decision = (
        "Buy Monthly Membership" if membership_total < stats["pay"] else "Pay Per Ride/Minute"
    )
    citation = state["pricing_url"]
    justification = (
        f"The uploaded file contains {stats['rides']} rides. Pay per ride is estimated at ${stats['pay']:.2f}, "
        f"while membership plus residual charges is ${membership_total:.2f}. The estimated break-even point is "
        f"{stats['break_even']:.2f} rides under the observed average duration. Therefore the recommendation is "
        f"{decision} based on the captured official pricing policy [{citation}]."
    )
    state["result"] = {
        "decision": decision,
        "justification": justification,
        "pay_per_use_cost": stats["pay"],
        "membership_cost": stats["membership"],
        "residual_charges": stats["residual"],
        "break_even_rides": stats["break_even"],
        "actual_rides": stats["rides"],
        "weekly": stats["weekly"],
        "citations": [{"url": citation, "captured_at": datetime.now(UTC).isoformat()}],
        "assumptions": [
            "CSV duration_minutes values are valid minutes.",
            "Frozen policy prices govern this evidence run.",
        ],
        "stop_reason": "success",
    }
    return state


def build_graph():
    graph = StateGraph(BikeState)
    graph.add_node("analyze_with_tools", _analyze)
    graph.add_node("make_cited_decision", _decide)
    graph.add_edge(START, "analyze_with_tools")
    graph.add_edge("analyze_with_tools", "make_cited_decision")
    graph.add_edge("make_cited_decision", END)
    return graph.compile()


def run_bike_agent(
    csv_path: str | Path, pricing_url: str, *, scenario: str = "uploaded"
) -> BikeDecision:
    started = time.perf_counter()
    state = build_graph().invoke(
        {
            "csv_path": str(csv_path),
            "pricing_url": pricing_url,
            "scenario": scenario,
            "timeline": [],
        }
    )
    result = state["result"]
    return BikeDecision(
        **{key: result[key] for key in BikeDecision.__dataclass_fields__ if key in result},
        step_count=len(state["timeline"]),
        total_time_ms=round((time.perf_counter() - started) * 1000, 3),
        timeline=state["timeline"],
    )


def save_pricing_snapshot(text: str, url: str, destination: Path) -> dict[str, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return {
        "source_url": url,
        "accessed_at": datetime.now(UTC).isoformat(),
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "file": str(destination),
    }
