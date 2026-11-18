"""A missing provider credential must not expose an unauthenticated ledger writer."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_webhook_without_signing_secret_is_disabled_and_cannot_write(monkeypatch):
    import app as service
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    client = TestClient(service.app)
    before = len(service.store.ledger_rows())
    reply = client.post("/webhooks/stripe", json={
        "id": "evt_unsigned_attempt", "type": "invoice.paid",
        "data": {"object": {"id": "in_unsigned", "amount_paid": 999999}},
    })
    assert reply.status_code == 503
    assert len(service.store.ledger_rows()) == before
