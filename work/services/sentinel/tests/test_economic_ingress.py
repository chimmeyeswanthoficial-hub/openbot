"""Actual ASGI boundary, fake signed events, disposable SQLite, no network/provider."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json

import app as service
import pytest
from economic import MAX_BODY_BYTES, EconomicError
from economic_fixtures import charge, encoded, event, scope
from economic_ingress import SyntheticIngress
from economic_repository import EconomicBook
from fastapi import HTTPException
from fastapi.testclient import TestClient
from repository import Store
from webhook import verify_stripe_signature

SECRET = 'explicitly-fake-unit-fixture-signing-secret'
FIXTURE_NOW = 1_700_000_000  # deterministic unit clock, NOT a measured execution timestamp


def signature(payload, *, timestamp=None, secret=SECRET):
    timestamp = FIXTURE_NOW if timestamp is None else timestamp
    digest = hmac.new(secret.encode(), str(timestamp).encode() + b'.' + payload, hashlib.sha256).hexdigest()
    return f't={timestamp},v1={digest}'


@pytest.fixture()
def ingress(tmp_path, monkeypatch):
    store = Store(str(tmp_path / 'ingress.sqlite3'))
    book = EconomicBook(store, experimental=True)
    profile = SyntheticIngress(book, scope(), SECRET, experimental=True, current_time=lambda: FIXTURE_NOW)
    monkeypatch.setattr(service, 'synthetic_economic_ingress', profile)
    monkeypatch.setattr(service, 'store', store)
    yield TestClient(service.app), book
    # A test may deliberately simulate a failed/closed connection.
    store._conn.close()


def post(client, payload=None, header=None):
    payload = encoded() if payload is None else payload
    return client.post('/v2/economic/stripe', content=payload,
                       headers={'stripe-signature': signature(payload) if header is None else header})


def test_disabled_ingress_refuses_before_body_or_book_access(monkeypatch):
    monkeypatch.setattr(service, 'synthetic_economic_ingress', None)
    class Request:
        async def stream(self):
            pytest.fail('disabled route must not read request body')
            yield b''
    with pytest.raises(HTTPException) as result:
        asyncio.run(service.synthetic_economic_webhook(Request()))
    assert result.value.status_code == 503


def test_profile_cannot_be_created_without_explicit_synthetic_host_configuration(tmp_path):
    store = Store(':memory:')
    book = EconomicBook(store, experimental=True)
    with pytest.raises(EconomicError):
        SyntheticIngress(book, scope(), SECRET)
    assert SECRET not in repr(SyntheticIngress(book, scope(), SECRET, experimental=True))
    store._conn.close()


def test_signed_raw_body_records_canonical_capture_but_not_legacy_revenue(ingress):
    client, book = ingress
    response = post(client)
    assert response.status_code == 201
    assert response.json()['status'] == 'recorded' and response.json()['created_postings'] == 1
    assert response.json()['bank_settlement_verified'] is False
    assert book.summary(scope())['capture_minor'] == 10000
    assert book.store.ledger_rows() == []
    assert client.get('/v1/pnl').json()['portfolio']['net_revenue'] == 0
    assert client.get('/v2/economic/pnl').status_code == 404  # no unreviewed public book-read route


def test_exact_replay_and_linked_notification_are_not_new_money(ingress):
    client, book = ingress
    assert post(client).status_code == 201
    assert post(client).status_code == 200
    response = post(client, encoded('charge.succeeded', charge()))
    assert response.status_code == 200 and response.json()['created_postings'] == 0
    assert book.summary(scope())['capture_minor'] == 10000


@pytest.mark.parametrize('header', ['', 'garbage', 't=0,v1=' + 'a' * 64, 't=abc,v1=' + 'a' * 64,
                                    't=1,t=2,v1=' + 'a' * 64, 't=1,v1=' + 'g' * 64])
def test_invalid_missing_expired_or_ambiguous_signature_cannot_mutate_book(ingress, header):
    client, book = ingress
    reply = post(client, header=header)
    assert reply.status_code == 400
    assert book.messages(scope()) == [] and book.postings(scope()) == []
    assert SECRET not in reply.text


def test_tampered_and_wrong_secret_body_cannot_mutate_book(ingress):
    client, book = ingress
    payload = encoded()
    assert post(client, payload + b' ', signature(payload)).status_code == 400
    assert post(client, payload, signature(payload, secret='another-fake-key')).status_code == 400
    assert book.messages(scope()) == []


@pytest.mark.parametrize('bad_payload', [b'[]', b'{bad', b'\xff', b'{"id":"evt_one","id":"evt_two"}',
                                        b'[' * 1100 + b']' * 1100])
def test_valid_signature_does_not_authorize_malformed_or_ambiguous_json(ingress, bad_payload):
    client, book = ingress
    assert post(client, bad_payload).status_code == 400
    assert book.messages(scope()) == []


def test_stream_byte_limit_enforced_without_content_length_trust(ingress):
    client, book = ingress
    response = client.post('/v2/economic/stripe', content=iter([b'x' * 65536] * 3),
                           headers={'stripe-signature': 'irrelevant', 'content-length': '1'})
    assert response.status_code == 413
    assert book.messages(scope()) == []
    assert MAX_BODY_BYTES < 3 * 65536


@pytest.mark.parametrize('field,value', [('currency', 'inr'), ('amount', True), ('amount', 1.25)])
def test_valid_signature_does_not_make_invalid_money_valid(ingress, field, value):
    client, book = ingress
    obj = charge()
    obj[field] = value
    assert post(client, encoded('charge.succeeded', obj)).status_code == 422
    assert book.messages(scope()) == [] and book.postings(scope()) == []


@pytest.mark.parametrize('field,value', [('livemode', True), ('account', 'acct_other')])
def test_signed_wrong_scope_is_refused(ingress, field, value):
    client, book = ingress
    obj = event('charge.succeeded', charge())
    obj[field] = value
    assert post(client, json.dumps(obj).encode()).status_code == 403
    assert book.messages(scope()) == []


def test_unsupported_event_is_explicitly_unresolved_not_recorded_as_paid(ingress):
    client, book = ingress
    response = post(client, encoded('charge.dispute.created', charge()))
    assert response.status_code == 202 and response.json()['status'] == 'unresolved'
    assert response.json()['created_postings'] == 0
    assert book.summary(scope())['unresolved_messages'] == 1


def test_same_id_changed_payload_is_conflict_not_successful_replay(ingress):
    client, book = ingress
    assert post(client).status_code == 201
    obj = event()
    obj['data']['object']['description'] = 'changed-fixture'
    reply = post(client, json.dumps(obj).encode())
    assert reply.status_code == 409 and book.summary(scope())['posting_count'] == 1


def test_closed_store_is_503_without_leaking_path_or_claiming_success(ingress):
    client, book = ingress
    book.store._conn.close()
    reply = post(client)
    assert reply.status_code == 503 and reply.json()['outcome_uncertain'] is False
    assert 'sqlite3' not in reply.text and 'ingress.sqlite3' not in reply.text


def test_postcommit_loss_requires_same_id_reconciliation_not_new_money(ingress):
    client, book = ingress
    def lost_reply(stage):
        if stage == 'after_commit':
            raise OSError('fixture response loss')
    book.fault_hook = lost_reply
    reply = post(client)
    assert reply.status_code == 503 and reply.json()['outcome_uncertain'] is True
    book.fault_hook = None
    assert post(client).status_code == 200
    assert book.summary(scope())['posting_count'] == 1


@pytest.mark.parametrize('valid_first', [True, False])
def test_signature_rotation_accepts_any_valid_v1_not_only_last(valid_first):
    payload = encoded()
    valid = signature(payload)
    timestamp, valid_sig = valid.split(',')
    invalid_sig = 'v1=' + '0' * 64
    header = timestamp + ',' + ','.join([valid_sig, invalid_sig] if valid_first else [invalid_sig, valid_sig])
    assert verify_stripe_signature(payload, header, SECRET, current_time=FIXTURE_NOW)


@pytest.mark.parametrize('tolerance', [0, -1, True, 901])
def test_timestamp_validation_cannot_be_switched_off_by_bad_tolerance(tolerance):
    payload = encoded()
    assert not verify_stripe_signature(payload, signature(payload), SECRET, tolerance=tolerance)


def test_non_ascii_signature_text_is_a_denial_not_a_constant_time_compare_exception():
    payload = encoded()
    assert not verify_stripe_signature(payload, 't=1,v1=' + '\u96ea' * 64, SECRET)


def test_absent_signature_header_is_refused_without_mutation(ingress):
    client, book = ingress
    assert client.post('/v2/economic/stripe', content=encoded()).status_code == 400
    assert book.messages(scope()) == [] and book.postings(scope()) == []
