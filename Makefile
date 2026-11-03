PYTHON ?= python3
PYTHONPATH := .:01-apis:02-tools:03-rag:04-mcp:05-plugins:06-skills:07-integration
export PYTHONPATH
PYTEST ?= $(PYTHON) -m pytest
PIP ?= $(PYTHON) -m pip
AGENT_DEBUGGER_URL ?= http://127.0.0.1:18000

.PHONY: help install smoke \
	apis tools rag mcp plugins skills integration chat chat-debugger \
	test-apis test-tools test-rag test-mcp test-plugins test-skills test-integration \
	test-all debugger-up debugger-down integration-debugger clone-debugger

help:
	@echo "Targets:"
	@echo "  install               pip install root requirements"
	@echo "  smoke / test-all      run all model-free smoke tests"
	@echo "  apis|tools|rag|mcp|plugins|skills|integration  run module demos"
	@echo "  chat                  observability web chat on :8080"
	@echo "  chat-debugger         chat with AGENT_DEBUGGER_URL set"
	@echo "  test-<module>         smoke test one module"
	@echo "  clone-debugger        clone Agent Debugger into third_party/"
	@echo "  debugger-up           compose profile debugger (ui :3000, api :18000)"
	@echo "  debugger-down         stop debugger profile"
	@echo "  integration-debugger  one-shot pipeline with AGENT_DEBUGGER_URL"

install:
	$(PIP) install -r requirements.txt

apis:
	PYTHONPATH=01-apis:$(PYTHONPATH) $(PYTHON) -m uvicorn issue_api.server:app --host 127.0.0.1 --port 8000

tools:
	SKIP_MODEL=1 $(PYTHON) 02-tools/tools_demo/agent.py

rag:
	SKIP_MODEL=1 $(PYTHON) 03-rag/rag_demo/ask.py

mcp:
	$(PYTHON) 04-mcp/client/demo.py

plugins:
	$(PYTHON) 05-plugins/loader/install.py

skills:
	PYTHONPATH=06-skills:$(PYTHONPATH) $(PYTHON) 06-skills/agent/run.py

integration:
	SKIP_MODEL=1 $(PYTHON) 07-integration/integration/pipeline.py --question "Which open issues mention login?"

chat:
	SKIP_MODEL=1 $(PYTHON) 07-integration/integration/chat_app.py

chat-debugger:
	SKIP_MODEL=1 AGENT_DEBUGGER_URL=$(AGENT_DEBUGGER_URL) $(PYTHON) 07-integration/integration/chat_app.py

test-apis:
	$(PYTEST) 01-apis/tests -q

test-tools:
	$(PYTEST) 02-tools/tests -q

test-rag:
	$(PYTEST) 03-rag/tests -q

test-mcp:
	$(PYTEST) 04-mcp/tests -q

test-plugins:
	$(PYTEST) 05-plugins/tests -q

test-skills:
	PYTHONPATH=06-skills:$(PYTHONPATH) $(PYTEST) 06-skills/tests -q

test-integration:
	$(PYTEST) 07-integration/tests -q

test-all smoke: test-apis test-tools test-rag test-mcp test-plugins test-skills test-integration
	@echo "All model-free smoke tests passed."

clone-debugger:
	@mkdir -p third_party
	@if [ ! -d third_party/agent-debugger/.git ]; then \
	  git clone --depth 1 https://github.com/likarajo/agent-debugger.git third_party/agent-debugger; \
	else \
	  echo "third_party/agent-debugger already present"; \
	fi

debugger-up: clone-debugger
	docker compose --profile debugger up --build -d debugger-redis debugger-api debugger-ui issue-api

debugger-down:
	docker compose --profile debugger down

integration-debugger:
	SKIP_MODEL=1 AGENT_DEBUGGER_URL=$(AGENT_DEBUGGER_URL) $(PYTHON) 07-integration/integration/pipeline.py --question "Triage the open login issues."
