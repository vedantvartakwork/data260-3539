#!/usr/bin/env python3
"""Capture every required call through the real MCP STDIO transport."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from code.hw5_tools import SQLAlchemyRecallRepository


OUTPUT = ROOT / "reports/hw05/raw/mcp_tool_outputs.json"


def server_parameters(relative_path: str) -> StdioServerParameters:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    return StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / relative_path)],
        cwd=str(ROOT),
        env=environment,
    )


async def capture_server(relative_path: str, calls: list[dict]) -> dict:
    async with stdio_client(server_parameters(relative_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            records = []
            for call in calls:
                result = await session.call_tool(call["tool"], call["inputs"])
                records.append({**call, "output": result.model_dump(mode="json")})
            return {
                "server": relative_path,
                "transport": "stdio",
                "tools": [tool.name for tool in tools.tools],
                "calls": records,
            }


async def capture() -> dict:
    sample_id = SQLAlchemyRecallRepository().search("shrimp", 1)[0]["id"]
    domain_calls = [
        {"tool": "search", "expected": "success", "inputs": {"query": "shrimp", "limit": 1}},
        {"tool": "search", "expected": "rejected", "inputs": {"query": "s", "limit": 5}},
        {"tool": "detail", "expected": "success", "inputs": {"recall_id": sample_id}},
        {"tool": "detail", "expected": "rejected", "inputs": {"recall_id": 0}},
        {"tool": "aggregate", "expected": "success", "inputs": {"group_by": "category", "min_units": 0}},
        {"tool": "aggregate", "expected": "rejected", "inputs": {"group_by": "submitter", "min_units": 0}},
    ]
    meal_calls = [
        {"tool": "search_meals_by_name", "inputs": {"query": "Arrabiata", "limit": 5}},
        {"tool": "meals_by_ingredient", "inputs": {"ingredient": "chicken", "limit": 5}},
        {"tool": "meal_details", "inputs": {"id": "52771"}},
        {"tool": "random_meal", "inputs": {}},
    ]
    domain, meals = await asyncio.gather(
        capture_server("mcp_servers/domain_server.py", domain_calls),
        capture_server("mcp_servers/meals_server.py", meal_calls),
    )
    return {"domain_server": domain, "meals_server": meals}


def main() -> None:
    payload = asyncio.run(capture())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"Captured {len(payload['domain_server']['calls'])} domain calls and "
        f"{len(payload['meals_server']['calls'])} MealDB calls through MCP STDIO"
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
