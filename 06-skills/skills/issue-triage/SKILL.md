---
name: issue-triage
description: Triage open issues using Northwind labels, severity rules, and a standard report template.
---

# Issue triage skill

Tools give the agent hands. This skill gives it the playbook.

## When to activate
- User asks to triage, prioritize, or summarize open issues
- Especially auth / login related queues

## Steps
1. Search open issues for the symptom text (default: `login` if unspecified).
2. For each match, read title, labels, assignee, and body.
3. Assign severity using the login-timeout runbook guidance when auth-related:
   - **p1**: production login blocked for many users
   - **p2**: intermittent or slow-network only
   - **p3**: staging / QA inconvenience
4. Prefer keeping existing severity labels when already present.
5. Produce a triage report using the template below — do not invent issue ids.

## Report template
```
# Triage report
- Scope: <what you searched>
- Matches:
  - #<id> <title> [labels] → severity <p?>
- Severity call: <overall p1|p2|p3 and why>
- Next step: <one concrete action>
```

## Rules
- Only use tool/API results for issue facts
- Cite issue ids
- If emailing a summary, that is a gated action (`email.send`) — propose, don't silently send
