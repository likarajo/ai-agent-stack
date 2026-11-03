"""Function-calling loop: model asks, our code acts, model answers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).resolve().parents[1]
for path in (ROOT, MODULE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from shared.config import SETTINGS  # noqa: E402
from shared.llm import ModelUnavailable, chat, model_available  # noqa: E402

from tools_demo.tools import TOOL_DEFINITIONS, execute_tool  # noqa: E402


SYSTEM = (
    "You are a helpful assistant for the Northwind issue tracker. "
    "Use tools to look up issues. Prefer search_issues for questions like "
    "'Which open issues mention login?'."
)


def scripted_tool_loop(question: str) -> str:
    """Deterministic demo path used when no model is available."""
    # Mimic what a capable model would request for the article's example question.
    call = {"name": "search_issues", "arguments": {"state": "open", "text": "login"}}
    result = execute_tool(call["name"], call["arguments"])
    titles = [f"#{i['id']} {i['title']}" for i in result.get("issues", [])]
    return (
        f"[scripted tools mode — no LLM]\n"
        f"Tool call: {call['name']}({json.dumps(call['arguments'])})\n"
        f"Found {result.get('count', 0)} open issue(s) mentioning login:\n"
        + "\n".join(f"- {t}" for t in titles)
    )


def llm_tool_loop(question: str, max_rounds: int = 4) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    for _ in range(max_rounds):
        reply = chat(messages, tools=TOOL_DEFINITIONS, settings=SETTINGS)
        tool_calls = reply.get("tool_calls") or []
        if not tool_calls:
            return reply.get("content") or "(empty model response)"
        messages.append(reply)
        for tc in tool_calls:
            fn = tc.get("function") or {}
            name = fn.get("name")
            args = fn.get("arguments") or {}
            result = execute_tool(name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_name": name,
                    "content": json.dumps(result),
                }
            )
    return "Stopped after max tool rounds without a final answer."


def answer(question: str) -> str:
    if model_available(SETTINGS) and not SETTINGS.skip_model:
        try:
            return llm_tool_loop(question)
        except ModelUnavailable:
            pass
    return scripted_tool_loop(question)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--question",
        default="Which open issues mention login?",
    )
    args = parser.parse_args()
    print(answer(args.question))


if __name__ == "__main__":
    main()
