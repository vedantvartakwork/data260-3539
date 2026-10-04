"""STDIO MCP server exposing exactly three grocery-recall domain tools."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Direct STDIO launches put ``mcp_servers`` (not the repository root) on
# ``sys.path``. Add the project root before importing the local ``code``
# package so Inspector and command-line launches behave like the test suite.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from code.hw5_tools import call_domain_tool


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
mcp = FastMCP("s3539_rel-recall-tools")


@mcp.tool(name="search")
def search(query: str, limit: int = 5) -> dict[str, Any]:
    """Search recall codes, products, and brands."""
    return call_domain_tool("search", {"query": query, "limit": limit})


@mcp.tool(name="detail")
def detail(recall_id: int) -> dict[str, Any]:
    """Return one recall and its manufacturer detail."""
    return call_domain_tool("detail", {"recall_id": recall_id})


@mcp.tool(name="aggregate")
def aggregate(group_by: str, min_units: int = 0) -> dict[str, Any]:
    """Aggregate recall count and affected units by category or manufacturer."""
    return call_domain_tool(
        "aggregate", {"group_by": group_by, "min_units": min_units}
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
