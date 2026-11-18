"""A gate/deny from the real HTTP schema must never become a queued routine."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from repository import Store
from runner import Worker
from spec import parse

ROOT = Path(__file__).parents[3]
SCOUT = (ROOT / ".openbot/routines/scout-daily.md").read_text()
SPEC = parse(SCOUT.replace("tags: [scout, market, daily]", "tags: [scout]\nventure: media-api"))


@pytest.mark.parametrize("reply, decision", [
    ({"effect": "deny", "rule": "test.deny"}, "deny"),
    ({"effect": "gate", "rule": "test.gate", "approval_id": "ap_test"}, "gate"),
    ({"decision": "gate", "rule": "test.gate", "approval_id": "ap_test"}, "gate"),
    ({"effect": "bogus"}, "deny"),
    ({}, "deny"),
    (None, "deny"),
    ({"effect": "allow", "decision": "deny"}, "deny"),
])
def test_non_allow_decision_never_queues(reply, decision):
    store = Store()
    worker = Worker(store=store, sentinel=lambda _: reply)
    worker.specs = [SPEC]
    out = worker.dispatch(SPEC.id, when=datetime(2026, 11, 10, 6))
    assert out["ok"] is False
    assert all(r["status"] != "queued" for r in store.runs(10))
    assert store.audit_tail(1)[0]["decision"] == decision
    if decision == "gate":
        assert out["approval_id"] == "ap_test"


def test_boundary_exception_records_refusal_instead_of_queue():
    def broken(_):
        raise ConnectionError("not reachable")
    store = Store()
    worker = Worker(store=store, sentinel=broken)
    worker.specs = [SPEC]
    out = worker.dispatch(SPEC.id)
    assert out["ok"] is False
    assert store.audit_tail(1)[0]["decision"] == "deny"
