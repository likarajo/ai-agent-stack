"""Issue Tracker MCP server — official Python SDK (MCPServer).

Exposes tools, a resource, and a prompt so any MCP-compatible host can reuse
this integration without embedding tool schemas in the host app.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.mcpserver import MCPServer  # noqa: E402

from shared.issue_store import get_issue, search_issues  # noqa: E402

mcp = MCPServer(
    name="northwind-issue-tracker",
    instructions=(
        "Tools for the Northwind portal issue tracker. "
        "Use search_issues for questions like 'Which open issues mention login?'."
    ),
)


@mcp.tool(description="Search issues by state and free-text query.")
def search_issues_tool(state: str = "open", text: str = "") -> dict:
    issues = search_issues(state=state, text=text)
    return {"count": len(issues), "issues": issues}


@mcp.tool(description="Fetch a single issue by id.")
def get_issue_tool(issue_id: int) -> dict:
    issue = get_issue(int(issue_id))
    if issue is None:
        return {"error": f"Issue {issue_id} not found"}
    return issue


@mcp.resource("issues://open")
def open_issues_resource() -> str:
    """Resource: current open issues as JSON."""
    return json.dumps(search_issues(state="open", text=None), indent=2)


@mcp.prompt()
def login_issue_prompt() -> str:
    """Reusable prompt template for the article's example question."""
    return "Which open issues mention login? Use search_issues_tool."


def main() -> None:
    # stdio transport — typical for local MCP hosts
    mcp.run()


if __name__ == "__main__":
    main()
