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


def test_stripe_webhook_flow_and_idempotency(monkeypatch, tmp_path):
    import hashlib
    import hmac
    import json

    import app as mod
    from economic_fixtures import encoded, invoice, scope
    from economic_ingress import SyntheticIngress
    from economic_repository import EconomicBook
    from repository import Store

    disposable = Store(str(tmp_path / "versioned-synthetic-webhook.sqlite3"))
    monkeypatch.setattr(mod, "store", disposable)
    client = TestClient(mod.app)
    secret, ts = "whsec_test_secret", 1_700_000_000  # synthetic deterministic UNIT clock
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)

    def signed(payload):
        digest = hmac.new(secret.encode(), str(ts).encode() + b"." + payload, hashlib.sha256).hexdigest()
        return {"Stripe-Signature": f"t={ts},v1={digest}"}

    try:
        # Preserve the original insufficient input as explicit denial coverage.
        # Neither an env secret nor a paid-label-only invoice activates old writes.
        old_payload = json.dumps({
            "id": "evt_hook_test_001", "type": "invoice.paid",
            "data": {"object": {"id": "in_test_001", "amount_paid": 5000,
                                "metadata": {"venture": "media-api"}}},
        }).encode()
        assert client.post("/webhooks/stripe", content=old_payload,
                           headers=signed(old_payload)).status_code == 503
        assert disposable.ledger_rows() == []

        # Qualified happy path is explicitly versioned, host-bound and synthetic.
        book = EconomicBook(disposable, experimental=True)
        profile = SyntheticIngress(book, scope(), secret, experimental=True, current_time=lambda: ts)
        monkeypatch.setattr(mod, "synthetic_economic_ingress", profile)
        payload = encoded("invoice.paid", invoice("test001", 5000), "evt_hook_test_001")
        first = client.post("/v2/economic/stripe", content=payload, headers=signed(payload))
        assert first.status_code == 201 and first.json()["created_postings"] == 1
        assert first.json()["message_created"] and not first.json()["bank_settlement_verified"]
        replay = client.post("/v2/economic/stripe", content=payload, headers=signed(payload))
        assert replay.status_code == 200 and replay.json()["created_postings"] == 0
        assert not replay.json()["message_created"]
        assert client.post("/v2/economic/stripe", content=payload,
                           headers={"Stripe-Signature": "t=123,v1=bad"}).status_code == 400
        assert book.summary(scope())["capture_minor"] == 5000
        assert disposable.ledger_rows() == []  # no unverified legacy revenue side effect
    finally:
        disposable._conn.close()
