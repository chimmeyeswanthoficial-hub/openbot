"""Daily approvals digest generator for OpenBot OS (T9).

Summarises pending human-in-the-loop approvals, flags gate starvation (> 24h age),
and produces actionable digests for human operators.
"""

from __future__ import annotations

import calendar
import time
from typing import Any


def format_digest(approvals: list[dict[str, Any]], *, now_epoch: float | None = None) -> str:
    """Format a list of pending approvals into a concise markdown digest."""
    now = now_epoch if now_epoch is not None else time.time()
    if not approvals:
        return "No pending approvals. The company is unblocked."

    oldest_age_hours = 0.0
    for a in approvals:
        created_str = a.get("created")
        if created_str:
            try:
                t = calendar.timegm(time.strptime(created_str, "%Y-%m-%dT%H:%M:%SZ"))
                age = max(0.0, (now - t) / 3600.0)
                if age > oldest_age_hours:
                    oldest_age_hours = age
            except Exception:
                pass

    oldest_age_hours = round(oldest_age_hours, 1)
    escalate = oldest_age_hours >= 24.0

    lines = []
    if escalate:
        lines.append(f"⚠️ **GATE STARVATION ALERT**: {len(approvals)} approval(s) pending, oldest is {oldest_age_hours}h old!")
        lines.append("Actions are blocked awaiting owner decision:")
    else:
        lines.append(f"**Daily Approvals Digest**: {len(approvals)} action(s) awaiting decision (oldest: {oldest_age_hours}h):")

    for a in approvals:
        aid = a.get("id", "unknown")
        venture = a.get("venture", "unassigned")
        rule = a.get("rule", "policy.gate")
        cost = a.get("cost_usd", 0.0)
        action_desc = a.get("reason") or a.get("rule")
        lines.append(f"- `{aid}` [{venture}] {rule} (${cost:.2f}): {action_desc}")

    return "\n".join(lines)
