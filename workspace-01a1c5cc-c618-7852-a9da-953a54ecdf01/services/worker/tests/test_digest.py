"""Tests for daily approvals digest (T9)."""

from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from digest import format_digest


def test_empty_approvals_digest():
    text = format_digest([])
    assert "No pending approvals" in text


def test_digest_with_recent_approvals():
    now = 1700000000.0
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 7200))  # 2 hours ago
    approvals = [{
        "id": "ap_12345",
        "venture": "media-api",
        "rule": "mcp.payment",
        "reason": "charge Stripe",
        "cost_usd": 25.0,
        "created": created,
    }]
    text = format_digest(approvals, now_epoch=now)
    assert "Daily Approvals Digest" in text
    assert "1 action(s) awaiting decision" in text
    assert "ap_12345" in text
    assert "$25.00" in text
    assert "2.0h" in text
    assert "GATE STARVATION ALERT" not in text


def test_digest_escalates_on_gate_starvation():
    now = 1700000000.0
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 30 * 3600))  # 30 hours ago
    approvals = [{
        "id": "ap_stale99",
        "venture": "media-api",
        "rule": "danger.shell",
        "reason": "execute script",
        "cost_usd": 0.0,
        "created": created,
    }]
    text = format_digest(approvals, now_epoch=now)
    assert "GATE STARVATION ALERT" in text
    assert "30.0h old" in text
    assert "ap_stale99" in text
