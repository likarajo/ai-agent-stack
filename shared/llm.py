"""Thin LLM client: Ollama by default, optional OpenAI-compatible hosted API."""

from __future__ import annotations

import json
from typing import Any

import httpx

from shared.config import SETTINGS, Settings


class ModelUnavailable(RuntimeError):
    """Raised when no local/hosted model can be reached."""


def model_available(settings: Settings | None = None) -> bool:
    cfg = settings or SETTINGS
    if cfg.skip_model:
        return False
    if cfg.use_hosted:
        return True
    try:
        with httpx.Client(base_url=cfg.ollama_base_url, timeout=2.0) as client:
            resp = client.get("/api/tags")
            return resp.status_code == 200
    except (httpx.HTTPError, OSError):
        return False


def chat(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Return a normalized message dict: {role, content, tool_calls?}."""
    cfg = settings or SETTINGS
    if cfg.skip_model:
        raise ModelUnavailable("SKIP_MODEL is set")
    if cfg.use_hosted:
        return _chat_openai_compatible(messages, tools=tools, settings=cfg)
    return _chat_ollama(messages, tools=tools, settings=cfg)


def _chat_ollama(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None,
    settings: Settings,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
    try:
        with httpx.Client(base_url=settings.ollama_base_url, timeout=120.0) as client:
            resp = client.post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, OSError) as exc:
        raise ModelUnavailable(f"Ollama chat failed: {exc}") from exc
    message = data.get("message") or {}
    usage = None
    if any(k in data for k in ("prompt_eval_count", "eval_count")):
        usage = {
            "prompt_tokens": data.get("prompt_eval_count"),
            "completion_tokens": data.get("eval_count"),
            "total_tokens": (data.get("prompt_eval_count") or 0)
            + (data.get("eval_count") or 0),
        }
    return {
        "role": message.get("role", "assistant"),
        "content": message.get("content") or "",
        "tool_calls": message.get("tool_calls") or [],
        "usage": usage,
    }


def _chat_openai_compatible(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None,
    settings: Settings,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if settings.openai_api_key:
        headers["Authorization"] = f"Bearer {settings.openai_api_key}"
    payload: dict[str, Any] = {
        "model": settings.openai_model,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, OSError) as exc:
        raise ModelUnavailable(f"Hosted chat failed: {exc}") from exc
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    tool_calls = []
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function") or {}
        args = fn.get("arguments") or "{}"
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {"raw": args}
        tool_calls.append(
            {
                "function": {
                    "name": fn.get("name"),
                    "arguments": args,
                }
            }
        )
    return {
        "role": message.get("role", "assistant"),
        "content": message.get("content") or "",
        "tool_calls": tool_calls,
        "usage": data.get("usage"),
    }
