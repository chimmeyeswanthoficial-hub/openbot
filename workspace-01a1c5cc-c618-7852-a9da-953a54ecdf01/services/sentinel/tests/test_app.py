"""Endpoint tests for the Sentinel service (the HITL queue is the point)."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import app as sentinel_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(sentinel_app.app)


def _decide(**kw):
    body = {"kind": "http.request", "venture": "media-api",
            "url": "https://api.stripe.com/v1/prices"}
    body.update(kw)
    return client.post("/v1/decide", json=body)


def test_health_lists_loaded_policies():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert "media-api" in r.json()["policies"]


def test_unknown_venture_fails_closed_and_is_audited():
    r = _decide(venture="ghost-venture")
    assert r.json()["effect"] == "deny"
    assert r.json()["rule"] == "policy.unknown_venture"


def test_read_in_allowlist_is_allowed():
    r = _decide()
    assert r.json()["effect"] == "allow" and r.json()["approval_id"] is None


def test_send_creates_a_pending_approval_that_a_human_resolves():
    r = _decide(kind="mcp.call", name="gmail.send_message",
                url="https://api.stripe.com/v1/x").json()
    assert r["effect"] == "gate" and r["approval_id"]

    pending = client.get("/v1/approvals").json()
    assert any(a["id"] == r["approval_id"] for a in pending)

    resolved = client.post(f"/v1/approvals/{r['approval_id']}",
                           json={"decision": "approved", "by": "human:owner"}).json()
    assert resolved["status"] == "approved"

    # A resolved approval cannot be re-resolved; the run was already unblocked once.
    again = client.post(f"/v1/approvals/{r['approval_id']}",
                        json={"decision": "denied", "by": "human:owner"})
    assert again.status_code == 409


def test_secret_payload_is_scrubbed_in_the_response():
    secret = "sk_live_" + "z" * 24
    r = _decide(method="POST", payload=f'{{"key":"{secret}"}}',
                url="https://api.stripe.com/v1/charges").json()
    assert r["effect"] == "gate"
    assert secret not in (r["scrubbed_payload"] or "")
    assert "[SCRUBBED]" in r["scrubbed_payload"]


def test_every_decision_persists_an_audit_row_with_its_initiator():
    before = client.get("/v1/audit?limit=1000").json()
    _decide(initiator="routine", initiator_id="scout-daily")
    after = client.get("/v1/audit?limit=1000").json()
    assert len(after) == len(before) + 1
    row = after[0]                      # newest first
    assert {"ts", "run_id", "decision", "rule", "initiator_kind", "initiator_id"} <= set(row)
    assert row["initiator_kind"] == "routine" and row["initiator_id"] == "scout-daily"


def test_overview_includes_approvals_pending_max_age_hours():
    r = client.get("/v1/overview")
    assert r.status_code == 200
    data = r.json()
    assert "approvals_pending_max_age_hours" in data
    assert isinstance(data["approvals_pending_max_age_hours"], (int, float))
    assert data["approvals_pending_max_age_hours"] >= 0.0

