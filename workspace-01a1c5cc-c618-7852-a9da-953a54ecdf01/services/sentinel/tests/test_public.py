"""Public-deployment behaviour: a token gates the writes, and nothing leaks without it."""

from __future__ import annotations

import importlib
import pathlib
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

TOKEN = "test-token-not-a-secret"


@pytest.fixture()
def gated(monkeypatch):
    monkeypatch.setenv("SENTINEL_UI_TOKEN", TOKEN)
    import app as mod
    importlib.reload(mod)
    yield TestClient(mod.app)
    monkeypatch.delenv("SENTINEL_UI_TOKEN", raising=False)
    importlib.reload(mod)


def _gate(client) -> str:
    r = client.post("/v1/decide", json={
        "kind": "mcp.call", "venture": "media-api", "name": "gmail.send_message",
        "url": "https://api.stripe.com/x"})
    assert r.json()["effect"] == "gate"
    return r.json()["approval_id"]


def test_approving_without_the_token_is_refused(gated):
    ap = _gate(gated)
    r = gated.post(f"/v1/approvals/{ap}", json={"decision": "approved"})
    assert r.status_code == 401
    assert gated.get("/v1/approvals").json()[0]["status"] == "pending"


def test_approving_with_the_token_works(gated):
    ap = _gate(gated)
    r = gated.post(f"/v1/approvals/{ap}", json={"decision": "approved"},
                   headers={"X-OpenBot-Token": TOKEN})
    assert r.status_code == 200 and r.json()["status"] == "approved"


def test_ledger_write_needs_the_token(gated):
    body = {"venture": "media-api", "kind": "revenue", "amount_usd": 19,
            "idempotency_key": "stripe:evt_public_1"}
    assert gated.post("/v1/ledger", json=body).status_code == 401
    assert gated.post("/v1/ledger", json=body,
                      headers={"X-OpenBot-Token": TOKEN}).status_code == 201
    # and the same provider event cannot be posted twice even with the token
    assert gated.post("/v1/ledger", json=body,
                      headers={"X-OpenBot-Token": TOKEN}).status_code == 200


def test_reads_stay_open_so_the_console_can_render(gated):
    assert gated.get("/v1/overview").status_code == 200
    assert gated.get("/").status_code == 200
    assert gated.get("/healthz").json()["ui_token_required"] is True


def test_when_the_store_fails_every_action_is_refused(monkeypatch):
    """No audit row, no action. A failing store must not let a decision escape unrecorded."""
    import sqlite3

    import app as mod

    real = mod.store
    before = len(real.list_approvals("all"))

    class BrokenStore:
        def __getattr__(self, _name):
            def boom(*_a, **_k):
                raise sqlite3.OperationalError("attempt to write a readonly database")
            return boom

    monkeypatch.setattr(mod, "store", BrokenStore())
    client = TestClient(mod.app)
    r = client.post("/v1/decide", json={"kind": "mcp.call", "venture": "media-api",
                                        "name": "gmail.send_message",
                                        "url": "https://api.stripe.com/x"})
    assert r.status_code == 503
    assert "audit store unavailable" in r.json()["detail"]
    # and no approval was handed out for an action that could not be recorded
    monkeypatch.setattr(mod, "store", real)
    assert len(real.list_approvals("all")) == before


def test_health_reports_the_store_state(monkeypatch):
    import app as mod
    assert TestClient(mod.app).get("/healthz").json()["store"] == "ok"


def test_resolve_approval_lost_race_under_concurrency():
    import concurrent.futures
    import app as mod
    aid = _gate(TestClient(mod.app))
    results = []

    def try_resolve(caller_id: int):
        return mod.store.resolve_approval(aid, "approved", f"human:{caller_id}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(try_resolve, i) for i in range(10)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    assert results.count(True) == 1
    assert results.count(False) == 9


def test_stripe_webhook_flow_and_idempotency(monkeypatch):
    import hashlib
    import hmac
    import json
    import time
    import app as mod
    client = TestClient(mod.app)
    secret = "whsec_test_secret"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)

    ts = int(time.time())
    payload = json.dumps({
        "id": "evt_hook_test_001",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_test_001",
                "amount_paid": 5000,
                "metadata": {"venture": "media-api"},
            }
        }
    }).encode("utf-8")
    sig = f"t={ts},v1={hmac.new(secret.encode(), f'{ts}.'.encode() + payload, hashlib.sha256).hexdigest()}"

    # 1. Valid webhook creates ledger row (201)
    r1 = client.post("/webhooks/stripe", content=payload, headers={"Stripe-Signature": sig})
    assert r1.status_code == 201
    assert r1.json()["created"] is True

    # 2. Replay returns 200 created: False (idempotent)
    r2 = client.post("/webhooks/stripe", content=payload, headers={"Stripe-Signature": sig})
    assert r2.status_code == 200
    assert r2.json()["created"] is False

    # 3. Bad signature is rejected (400)
    r3 = client.post("/webhooks/stripe", content=payload, headers={"Stripe-Signature": "t=123,v1=bad"})
    assert r3.status_code == 400


