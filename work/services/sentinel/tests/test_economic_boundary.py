"""Behavioral red regressions: retire the unsafe writer and reject invalid money.

All keys/events below are synthetic, all databases disposable. No provider calls.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time

import app as service
import pytest
from fastapi.testclient import TestClient
from pnl import LedgerError, validate_row
from repository import Store
from webhook import WebhookError, map_stripe_event_to_ledger_row


@pytest.mark.parametrize('event_type,obj', [
    ('invoice.paid', {'id': 'in_fixture', 'amount_paid': 10000}),
    ('charge.refunded', {'id': 'ch_fixture', 'amount_refunded': 5000}),
    ('invoice.paid', {'id': 'in_fixture_inr', 'currency': 'inr', 'amount_paid': 10000}),
])
def test_legacy_event_id_mapper_is_not_an_authoritative_money_writer(event_type, obj):
    with pytest.raises(WebhookError, match='legacy'):
        map_stripe_event_to_ledger_row({'id': 'evt_fixture', 'type': event_type,
                                        'data': {'object': obj}})


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf'), True])
def test_legacy_validation_refuses_nonfinite_and_boolean_money(value):
    with pytest.raises(LedgerError):
        validate_row({'venture': 'media-api', 'kind': 'adjustment', 'amount_usd': value,
                      'idempotency_key': 'fixture', 'source': 'manual'})


def test_legacy_secret_alone_cannot_enable_an_unverified_ledger_writer(monkeypatch):
    store = Store(':memory:')
    monkeypatch.setattr(service, 'store', store)
    secret = 'explicitly-fake-unit-signing-secret'
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', secret)
    payload = json.dumps({'id': 'evt_fixture', 'type': 'invoice.paid',
                          'data': {'object': {'id': 'in_fixture', 'amount_paid': 10000}}}).encode()
    timestamp = int(time.time())
    signature = hmac.new(secret.encode(), str(timestamp).encode() + b'.' + payload, hashlib.sha256).hexdigest()
    response = TestClient(service.app).post('/webhooks/stripe', content=payload,
                headers={'stripe-signature': f't={timestamp},v1={signature}'})
    assert response.status_code == 503
    assert store.ledger_rows() == []
    store._conn.close()


def test_legacy_manual_http_does_not_coerce_boolean_to_money(monkeypatch):
    store = Store(':memory:')
    monkeypatch.setattr(service, 'store', store)
    response = TestClient(service.app).post('/v1/ledger', json={
        'venture': 'media-api', 'kind': 'revenue', 'amount_usd': True,
        'source': 'manual', 'idempotency_key': 'bool-fixture',
    })
    assert response.status_code == 422
    assert store.ledger_rows() == []
    store._conn.close()


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf'), True])
def test_direct_legacy_store_also_refuses_invalid_new_money(value):
    store = Store(':memory:')
    try:
        with pytest.raises(ValueError):
            store.post_ledger({'venture': 'media-api', 'kind': 'adjustment', 'amount_usd': value,
                               'source': 'manual', 'idempotency_key': 'invalid-direct-fixture'})
        assert store.ledger_rows() == []
    finally:
        store._conn.close()


def test_legacy_unrelated_integrity_failure_is_not_a_successful_duplicate():
    import sqlite3

    store = Store(':memory:')
    store._conn.execute("CREATE TRIGGER fixture_fail_ledger BEFORE INSERT ON ledger "
                        "BEGIN SELECT RAISE(ABORT,'synthetic disk/constraint problem'); END")
    try:
        with pytest.raises(sqlite3.IntegrityError):
            store.post_ledger({'venture': 'media-api', 'kind': 'revenue', 'amount_usd': 1,
                               'source': 'manual', 'idempotency_key': 'constraint-unit'})
        assert store.ledger_rows() == []
    finally:
        store._conn.close()


@pytest.mark.parametrize('literal', ['NaN', 'Infinity', '-Infinity'])
def test_legacy_manual_http_nonfinite_is_a_clean_refusal_not_500(monkeypatch, literal):
    store = Store(':memory:')
    monkeypatch.setattr(service, 'store', store)
    payload = ('{"venture":"media-api","kind":"adjustment","source":"manual",'
               '"idempotency_key":"bad-http-money","amount_usd":' + literal + '}')
    try:
        reply = TestClient(service.app, raise_server_exceptions=False).post(
            '/v1/ledger', content=payload, headers={'content-type': 'application/json'})
        assert reply.status_code == 422
        assert store.ledger_rows() == []
        assert 'input' not in reply.json()['detail'][0]  # no nonfinite/raw-body echo
    finally:
        store._conn.close()
