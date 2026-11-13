"""Tests for OpenBot Gateway Adapter (T2)."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from adapter import GatewayAdapter


def test_adapter_allow_action():
    def mock_decide(action):
        return {"effect": "allow", "run_id": "r_123", "rule": "policy.allow"}

    adapter = GatewayAdapter(decide_fn=mock_decide)
    res = adapter.intercept("open_browser", {"url": "https://api.stripe.com/prices"})
    assert res["status"] == "allowed"
    assert res["run_id"] == "r_123"


def test_adapter_deny_action():
    def mock_decide(action):
        return {"effect": "deny", "run_id": "r_456", "rule": "isolation.write_root", "reason": "out of bounds"}

    adapter = GatewayAdapter(decide_fn=mock_decide)
    res = adapter.intercept("save_file", {"path": "/etc/passwd", "content": "bad"})
    assert res["status"] == "denied"
    assert res["rule"] == "isolation.write_root"
    assert "out of bounds" in res["reason"]


def test_adapter_gate_creates_agui_card():
    def mock_decide(action):
        return {
            "effect": "gate",
            "run_id": "r_789",
            "approval_id": "ap_xyz999",
            "rule": "mcp.send_message",
            "reason": "sending external message requires review",
        }

    adapter = GatewayAdapter(decide_fn=mock_decide)
    res = adapter.intercept("gmail.send_message", {"body": "hello"}, bot_id="scout-bot")
    assert res["status"] == "gated"
    assert res["approval_id"] == "ap_xyz999"

    card = res["card"]
    assert card["type"] == "card"
    assert card["card"] == "approval"
    assert card["approval_id"] == "ap_xyz999"
    assert card["tool"] == "gmail.send_message"
    assert card["status"] == "pending"


def test_adapter_fails_closed_on_sentinel_exception():
    def broken_decide(action):
        raise ConnectionError("sentinel down")

    adapter = GatewayAdapter(decide_fn=broken_decide)
    res = adapter.intercept("bash", {"command": "rm -rf /"})
    assert res["status"] == "denied"
    assert res["rule"] == "gateway.error_fail_closed"


def test_adapter_resolve_approval():
    calls = []

    def mock_resolve(aid, decision, by, note):
        calls.append((aid, decision, by, note))
        return True

    adapter = GatewayAdapter(decide_fn=lambda a: {}, resolve_fn=mock_resolve)
    ok = adapter.resolve("ap_test_1", "approved", by="human:owner", note="verified")
    assert ok is True
    assert calls == [("ap_test_1", "approved", "human:owner", "verified")]

