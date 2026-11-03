"""Minimal web chat for the observability integration demo.

Films well: suggested questions as chips, answer pane, and a live local
trace sidebar. When AGENT_DEBUGGER_URL is set, the same events stream to
Agent Debugger (open the returned run_id there).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).resolve().parents[1]
for path in (ROOT, MODULE, ROOT / "05-plugins", ROOT / "06-skills", ROOT / "03-rag", ROOT / "04-mcp", ROOT / "02-tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from shared.debugger import debugger_enabled, debugger_url  # noqa: E402

from integration.pipeline import DEMO_QUESTIONS, answer_question  # noqa: E402

app = FastAPI(title="ai-agent-stack chat", version="1.0.0")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    send_email: bool = False


class ChatResponse(BaseModel):
    answer: str
    run_id: str | None
    duration_ms: float
    debugger: bool
    debugger_url: str | None
    concepts: list[str]
    events: list[dict[str, Any]]


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "debugger": debugger_enabled(),
        "debugger_url": debugger_url(),
    }


@app.get("/api/demo-questions")
def demo_questions() -> dict[str, Any]:
    return {"questions": DEMO_QUESTIONS}


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    result = answer_question(body.message, send_email=body.send_email)
    return ChatResponse(
        answer=result["answer"],
        run_id=result.get("run_id"),
        duration_ms=result["duration_ms"],
        debugger=result["debugger"],
        debugger_url=debugger_url(),
        concepts=result["concepts"],
        events=result.get("events") or [],
    )


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return CHAT_HTML


CHAT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ai-agent-stack chat</title>
  <style>
    :root {
      --bg: #0f1419;
      --panel: #1a222c;
      --ink: #e7eef7;
      --muted: #8b9bb0;
      --accent: #3d9cf0;
      --accent2: #5ecf9a;
      --line: #2a3544;
      --warn: #f0b35a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      background: radial-gradient(1200px 600px at 10% -10%, #1b2a3d, transparent),
                  radial-gradient(900px 500px at 100% 0%, #1a2e28, transparent),
                  var(--bg);
      color: var(--ink); min-height: 100vh;
    }
    header {
      padding: 1.25rem 1.5rem 0.5rem; max-width: 1100px; margin: 0 auto;
    }
    header h1 { margin: 0; font-size: 1.35rem; letter-spacing: 0.02em; }
    header p { margin: 0.35rem 0 0; color: var(--muted); font-size: 0.95rem; }
    .layout {
      display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 1rem;
      max-width: 1100px; margin: 0 auto; padding: 1rem 1.5rem 2rem;
    }
    @media (max-width: 900px) { .layout { grid-template-columns: 1fr; } }
    .panel {
      background: color-mix(in srgb, var(--panel) 92%, black);
      border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
      display: flex; flex-direction: column; min-height: 70vh;
    }
    .panel h2 {
      margin: 0; padding: 0.85rem 1rem; font-size: 0.85rem; text-transform: uppercase;
      letter-spacing: 0.08em; color: var(--muted); border-bottom: 1px solid var(--line);
    }
    .chips { display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 0.75rem 1rem; border-bottom: 1px solid var(--line); }
    .chip {
      border: 1px solid var(--line); background: #121820; color: var(--ink);
      border-radius: 999px; padding: 0.4rem 0.75rem; font-size: 0.85rem; cursor: pointer;
    }
    .chip:hover { border-color: var(--accent); color: white; }
    .messages { flex: 1; overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem; }
    .bubble { max-width: 92%; padding: 0.75rem 0.9rem; border-radius: 12px; white-space: pre-wrap; line-height: 1.45; font-size: 0.95rem; }
    .user { align-self: flex-end; background: #243447; }
    .bot { align-self: flex-start; background: #18231c; border: 1px solid #2a4036; }
    .meta { font-size: 0.75rem; color: var(--muted); margin-top: 0.35rem; }
    form {
      display: flex; gap: 0.5rem; padding: 0.85rem; border-top: 1px solid var(--line);
    }
    input[type=text] {
      flex: 1; border-radius: 10px; border: 1px solid var(--line); background: #0e1319;
      color: var(--ink); padding: 0.7rem 0.85rem; font-size: 1rem;
    }
    button.send {
      border: 0; border-radius: 10px; background: var(--accent); color: #041018;
      font-weight: 600; padding: 0 1rem; cursor: pointer;
    }
    button.send:disabled { opacity: 0.5; cursor: wait; }
    .trace { flex: 1; overflow-y: auto; padding: 0.75rem; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.78rem; }
    .evt { border: 1px solid var(--line); border-radius: 8px; padding: 0.55rem 0.65rem; margin-bottom: 0.5rem; background: #10161d; }
    .evt .t { color: var(--accent2); }
    .evt .m { color: var(--ink); margin-top: 0.2rem; }
    .evt pre { margin: 0.4rem 0 0; color: var(--muted); white-space: pre-wrap; word-break: break-word; max-height: 140px; overflow: auto; }
    .banner {
      margin: 0.75rem 1.5rem 0; max-width: 1100px; margin-left: auto; margin-right: auto;
      padding: 0.65rem 0.85rem; border-radius: 10px; border: 1px solid var(--line);
      background: #151c24; color: var(--muted); font-size: 0.9rem;
    }
    .banner strong { color: var(--warn); }
    a { color: var(--accent); }
  </style>
</head>
<body>
  <header>
    <h1>ai-agent-stack · observability chat</h1>
    <p>Ask about Northwind issues. Every step (plugin → skill → RAG → MCP → tools → API → LLM) is traced.</p>
  </header>
  <div class="banner" id="status">Loading…</div>
  <div class="layout">
    <section class="panel">
      <h2>Chat</h2>
      <div class="chips" id="chips"></div>
      <div class="messages" id="messages"></div>
      <form id="form">
        <input id="input" type="text" placeholder="Ask a question…" autocomplete="off" />
        <button class="send" id="send" type="submit">Send</button>
      </form>
    </section>
    <section class="panel">
      <h2>Local trace (same events → Agent Debugger)</h2>
      <div class="trace" id="trace"><div class="evt"><div class="m">Send a question to see the ordered timeline.</div></div></div>
    </section>
  </div>
  <script>
    const messages = document.getElementById('messages');
    const trace = document.getElementById('trace');
    const chips = document.getElementById('chips');
    const form = document.getElementById('form');
    const input = document.getElementById('input');
    const send = document.getElementById('send');
    const status = document.getElementById('status');

    function addBubble(text, who, meta) {
      const div = document.createElement('div');
      div.className = 'bubble ' + who;
      div.textContent = text;
      if (meta) {
        const m = document.createElement('div');
        m.className = 'meta';
        m.textContent = meta;
        div.appendChild(m);
      }
      messages.appendChild(div);
      messages.scrollTop = messages.scrollHeight;
    }

    function renderTrace(events) {
      trace.innerHTML = '';
      if (!events || !events.length) {
        trace.innerHTML = '<div class="evt"><div class="m">No events.</div></div>';
        return;
      }
      for (const e of events) {
        const el = document.createElement('div');
        el.className = 'evt';
        const tool = e.tool ? ' · ' + e.tool : '';
        el.innerHTML = `<div class="t">${e.type || ''}${tool}</div><div class="m">${e.message || ''}</div>`;
        if (e.payload != null) {
          const pre = document.createElement('pre');
          pre.textContent = JSON.stringify(e.payload, null, 2);
          el.appendChild(pre);
        }
        trace.appendChild(el);
      }
      trace.scrollTop = trace.scrollHeight;
    }

    async function boot() {
      const h = await fetch('/health').then(r => r.json());
      const qs = await fetch('/api/demo-questions').then(r => r.json());
      if (h.debugger) {
        status.innerHTML = `<strong>Debugger ON</strong> → ${h.debugger_url}. After each answer, open Agent Debugger and watch run_id (UI patch: Watch run by id — see docs/AGENT_DEBUGGER_UPSTREAM.md).`;
      } else {
        status.innerHTML = `Standalone mode (local trace only). Set <code>AGENT_DEBUGGER_URL</code> to stream into Agent Debugger.`;
      }
      for (const q of qs.questions || []) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'chip';
        b.textContent = q.text;
        b.title = q.focus || '';
        b.onclick = () => { input.value = q.text; form.requestSubmit(); };
        chips.appendChild(b);
      }
    }

    form.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      addBubble(text, 'user');
      send.disabled = true;
      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text }),
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        const meta = `run_id=${data.run_id || '—'} · ${data.duration_ms}ms · concepts: ${(data.concepts||[]).join(', ')}`;
        addBubble(data.answer, 'bot', meta);
        renderTrace(data.events);
        if (data.debugger && data.run_id) {
          status.innerHTML = `<strong>Debugger run</strong> <code>${data.run_id}</code> at ${data.debugger_url} — timeline + audit should show every step.`;
        }
      } catch (e) {
        addBubble('Error: ' + e, 'bot');
      } finally {
        send.disabled = false;
        input.focus();
      }
    });

    boot();
  </script>
</body>
</html>
"""


def main() -> None:
    import uvicorn

    host = os.getenv("CHAT_HOST", "127.0.0.1")
    port = int(os.getenv("CHAT_PORT", "8080"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
