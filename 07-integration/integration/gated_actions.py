"""Simulated gated actions (email.send, etc.). Never performs real side effects."""

from __future__ import annotations

from typing import Any


def simulate_email_send(payload: dict[str, Any]) -> dict[str, Any]:
    """Demo-only email send — logs intent, sends nothing."""
    return {
        "ok": True,
        "simulated": True,
        "to": payload.get("to"),
        "subject": payload.get("subject"),
        "note": "No email was actually sent.",
    }
