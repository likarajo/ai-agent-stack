# ai-agent-stack

Clone-and-learn examples for the six building blocks in  
[AI Agent Stack: MCP vs RAG vs APIs vs Tools vs Plugins vs Skills](https://likarajo.github.io/writing/ai-agent-stack-mcp-rag-apis-tools-plugins-skills/)  
by Rajarshi Chattopadhyay.

They **stack, they don’t compete**. Each module is self-contained (README + runnable demo + smoke test). The final module wires them into one agentic pipeline. Everything runs **locally and free** by default (optional Ollama; optional hosted model env vars; optional [Agent Debugger](https://github.com/likarajo/agent-debugger)).

## Overview

```text
                         ┌─────────────────────────┐
                         │     Host / Agent app     │
                         │  (07-integration demo)   │
                         └───────────┬─────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         ▼                         ▼
    ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
    │   Plugin    │ bundles  │   Skills    │ playbook │     RAG     │
    │  (05)       │ ───────► │   (06)      │          │    (03)     │
    └──────┬──────┘          └──────┬──────┘          └─────────────┘
           │ MCP config             │ uses
           ▼                        ▼
    ┌─────────────┐          ┌─────────────┐
    │     MCP     │ exposes  │    Tools    │
    │    (04)     │ ───────► │    (02)     │
    └──────┬──────┘          └──────┬──────┘
           │                        │
           └───────────┬────────────┘
                       ▼
                ┌─────────────┐
                │     API     │  Northwind Issue Tracker
                │    (01)     │  shared/data/issues.json
                └─────────────┘
```

Running domain (matches the article): an assistant for a software project’s **issue tracker** — e.g. “Which open issues mention login?” / “Triage the open login issues.”

## Recommended learning order

| Order | Module | Concept |
| ---: | --- | --- |
| 1 | [`01-apis`](01-apis/) | Documented HTTP/JSON contract — no AI |
| 2 | [`02-tools`](02-tools/) | Function calling — model proposes, your code runs |
| 3 | [`03-rag`](03-rag/) | Retrieve docs, then answer with sources |
| 4 | [`04-mcp`](04-mcp/) | Standard host/client/server tool protocol |
| 5 | [`05-plugins`](05-plugins/) | Packaging MCP + skills + commands |
| 6 | [`06-skills`](06-skills/) | Progressive-loaded playbooks (`SKILL.md`) |
| 7 | [`07-integration`](07-integration/) | Full stack + optional Agent Debugger |

## Quickstart

```bash
git clone https://github.com/likarajo/ai-agent-stack.git
cd ai-agent-stack
python3 -m venv .venv && source .venv/bin/activate
make install
make smoke          # model-free CI-equivalent tests
make integration    # end-to-end standalone demo
```

Per-module one-liners:

```bash
make tools      # scripted function-calling demo
make rag        # extractive RAG over shared docs
make mcp        # official MCP Python SDK stdio round-trip
make plugins    # install plugin manifest
make skills     # progressive skill load + triage report
```

Optional live LLM (free, local):

```bash
# install Ollama, then:
ollama pull qwen2.5:0.5b
unset SKIP_MODEL
python 02-tools/tools_demo/agent.py
```

Optional Agent Debugger timeline (final video):

```bash
make debugger-up            # needs Docker; clones debugger into third_party/
make integration-debugger   # pauses on email.send until Approve/Deny in UI :3000
```

Details: [`docs/AGENT_DEBUGGER.md`](docs/AGENT_DEBUGGER.md).

## Makefile

See `make help` for per-module run and test targets.

## License

MIT — see [`LICENSE`](LICENSE).

## Notes

- No paid APIs or secrets required for the default path.
- Model-dependent paths are skippable (`SKIP_MODEL=1`); CI only runs model-free smoke tests.
- Optional hosted OpenAI-compatible settings: see `.env.example`.
