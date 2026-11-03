"""Connect to the Issue Tracker MCP server over stdio, list tools, call one."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "04-mcp" / "server" / "issue_tracker.py"


async def run_demo(text: str = "login", state: str = "open") -> dict:
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)],
        env=env,
        cwd=str(ROOT),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            result = await session.call_tool(
                "search_issues_tool",
                {"state": state, "text": text},
            )
            # Normalize content blocks to plain text/json
            chunks = []
            for block in result.content or []:
                text_val = getattr(block, "text", None)
                if text_val is not None:
                    chunks.append(text_val)
                else:
                    chunks.append(str(block))
            return {
                "tools": tool_names,
                "call": "search_issues_tool",
                "raw": "\n".join(chunks),
            }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="login")
    parser.add_argument("--state", default="open")
    args = parser.parse_args()
    out = asyncio.run(run_demo(text=args.text, state=args.state))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
