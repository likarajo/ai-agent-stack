# Minimal Agent Debugger upstream patches

These changes belong in a **separate** PR on
[likarajo/agent-debugger](https://github.com/likarajo/agent-debugger) after Raj’s OK.
**Do not apply them from the ai-agent-stack agent.**

Goal: let an external driver (this repo’s chat) create a run, emit a rich
observability timeline, and let the Debugger UI attach to that run — without
racing the scripted outreach worker.

---

## 1. `api/app/main.py` — optional `enqueue` on create

Allow external agents to create a run without pushing onto `runs:queue`.

```diff
 class CreateRunBody(BaseModel):
     scenario: str = Field(default=runs.SCENARIO_OUTREACH)
+    enqueue: bool = Field(default=True, description="If false, do not push to the worker queue")


 @app.post("/runs")
 def create_run(body: CreateRunBody) -> dict[str, Any]:
-    return runs.create_run(scenario=body.scenario)
+    return runs.create_run(scenario=body.scenario, enqueue=body.enqueue)
```

## 2. `api/app/runs.py` — honor `enqueue=False`

```diff
 def create_run(scenario: str = SCENARIO_OUTREACH) -> dict[str, Any]:
+def create_run(scenario: str = SCENARIO_OUTREACH, enqueue: bool = True) -> dict[str, Any]:
     r = get_redis()
     run_id = str(uuid.uuid4())
     ...
     r.set(_run_key(run_id), json.dumps(run))
     r.delete(_events_key(run_id))
     r.delete(_decision_key(run_id))
-    r.lpush(RUNS_QUEUE, run_id)
+    if enqueue:
+        r.lpush(RUNS_QUEUE, run_id)
     _append_event(...)
     return run
```

## 3. `agent/worker.py` — idle external scenarios

Do not abort unknown / external scenarios; leave them for an outside driver.

```diff
                 scenario = run.get("scenario", "outreach_almost_sends_email")
                 if scenario == "outreach_almost_sends_email":
                     run_outreach(client, run_id)
+                elif scenario.startswith("external") or scenario.startswith("ai_agent_stack"):
+                    print(f"[agent] skipping externally-driven scenario {scenario}", flush=True)
+                    continue
                 else:
                     post_event(
                         client,
                         run_id,
                         {
                             "type": "run.aborted",
                             "message": f"Unknown scenario: {scenario}",
                         },
                     )
```

## 4. `api/app/runs.py` — broaden audit log for observability

Today `list_audit` only keeps `decision`, `tool.result`, `run.completed`,
`run.aborted`. For the stack demo, also keep user / answer / LLM markers:

```diff
 def list_audit(run_id: str) -> list[dict[str, Any]]:
-    return [e for e in list_events(run_id) if e.get("type") in {"decision", "tool.result", "run.completed", "run.aborted"}]
+    AUDIT_TYPES = {
+        "decision",
+        "tool.result",
+        "run.completed",
+        "run.aborted",
+        "user.message",
+        "agent.answer",
+        "llm.chat",  # if emitted as a type; tool.result for llm.chat still covered above
+    }
+    return [e for e in list_events(run_id) if e.get("type") in AUDIT_TYPES]
```

Note: ai-agent-stack emits LLM / plugin / skill / RAG / MCP / tools / API as
`tool.call` + `tool.result` pairs (with `duration_ms` in payloads), so they
already appear in the **current** audit via `tool.result`. Expanding audit is
still useful for `user.message` and `agent.answer`.

## 5. `ui/src/api.js` — watch an existing run

```diff
 export async function createRun() {
   const res = await fetch(`${API}/runs`, {
     method: "POST",
     headers: { "Content-Type": "application/json" },
-    body: JSON.stringify({ scenario: "outreach_almost_sends_email" }),
+    body: JSON.stringify({ scenario: "outreach_almost_sends_email", enqueue: true }),
   });
   ...
 }

+export async function watchRun(runId) {
+  const res = await fetch(`${API}/runs/${runId}`);
+  if (!res.ok) throw new Error(await res.text());
+  return res.json();
+}
```

## 6. `ui/src/App.jsx` — “Watch run” by id (for stack filming)

Add a small input + button next to the outreach demo button:

```diff
+ const [watchId, setWatchId] = useState("");
+
+ async function watchExisting() {
+   setError("");
+   setBusy(true);
+   try {
+     if (unsubRef.current) unsubRef.current();
+     setEvents([]);
+     setAudit([]);
+     const existing = await watchRun(watchId.trim());
+     setRun(existing);
+     // replay + live subscribe
+     const prior = await fetch(`${API}/runs/${existing.id}/events`).then((r) => r.json());
+     setEvents(prior.events || []);
+     await refreshAudit(existing.id);
+     unsubRef.current = subscribe(existing.id, async (event) => { /* same as startDemo */ });
+   } catch (e) {
+     setError(String(e.message || e));
+   } finally {
+     setBusy(false);
+   }
+ }
```

In the header JSX:

```jsx
<input
  value={watchId}
  onChange={(e) => setWatchId(e.target.value)}
  placeholder="Paste external run id"
/>
<button className="btn" onClick={watchExisting} disabled={busy || !watchId.trim()}>
  Watch run
</button>
```

Also import `watchRun` from `./api.js` (and `API` if replaying events client-side).

Optional copy tweak: subtitle can mention “or watch an external ai-agent-stack run”.

## 7. (Optional) `ui/src/App.jsx` — deep link `?run_id=`

```js
useEffect(() => {
  const id = new URLSearchParams(window.location.search).get("run_id");
  if (id) {
    setWatchId(id);
    // auto-call watchExisting once API helpers are ready
  }
}, []);
```

Then ai-agent-stack chat can link to `http://localhost:3000/?run_id=<uuid>`.

---

## Why this is enough

| Need | Covered by |
| --- | --- |
| External driver owns the run | patches 1–3 |
| Timeline shows every step | already works (EventCard renders any type + payload) |
| Audit shows answers / user turns | patch 4 |
| Film Debugger UI on stack chat | patches 5–7 |

Until these land, `ai-agent-stack` compose profile runs debugger **api + ui + redis** without the outreach worker, and the chat UI shows the same ordered local trace plus `run_id` for manual SSE/`GET /runs/{id}/events` inspection.
