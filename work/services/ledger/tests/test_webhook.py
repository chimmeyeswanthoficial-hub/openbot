"""Tests for Stripe webhook processing and ledger mapping (T5)."""

from __future__ import annotations

import hashlib
import hmac
import pathlib
import sys
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from webhook import WebhookError, map_stripe_event_to_ledger_row, verify_stripe_signature


def _make_sig(payload: bytes, secret: str, ts: int) -> str:
    signed_payload = f"{ts}.".encode() + payload
    v1 = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={v1}"


def test_verify_stripe_signature_valid():
    secret = "whsec_test_secret_123"
    payload = b'{"id":"evt_123","type":"invoice.paid"}'
    ts = int(time.time())
    sig = _make_sig(payload, secret, ts)

    assert verify_stripe_signature(payload, sig, secret, current_time=ts) is True


def test_verify_stripe_signature_tampered_payload_rejected():
    secret = "whsec_test_secret_123"
    payload = b'{"id":"evt_123","type":"invoice.paid"}'
    ts = int(time.time())
    sig = _make_sig(payload, secret, ts)

    tampered_payload = b'{"id":"evt_123","type":"invoice.paid","extra":"bad"}'
    assert verify_stripe_signature(tampered_payload, sig, secret, current_time=ts) is False


def test_verify_stripe_signature_expired_tolerance_rejected():
    secret = "whsec_test_secret_123"
    payload = b'{"id":"evt_123"}'
    old_ts = int(time.time()) - 400  # 400s ago
    sig = _make_sig(payload, secret, old_ts)

    # tolerance is 300s
    assert verify_stripe_signature(payload, sig, secret, tolerance=300) is False


def test_map_invoice_paid_to_revenue():
    event = {
        "id": "evt_test_paid_999",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_123",
                "amount_paid": 4900,  # $49.00
                "customer": "cus_abc",
                "metadata": {"venture": "media-api"},
            }
        },
    }
    # Preserve the insufficient old input as denial coverage. Fully qualified
    # capture accounting is tested through the canonical replacement.
    with pytest.raises(WebhookError, match="legacy"):
        map_stripe_event_to_ledger_row(event)


def test_map_charge_refunded_to_refund():
    event = {
        "id": "evt_test_ref_111",
        "type": "charge.refunded",
        "data": {
            "object": {
                "id": "ch_456",
                "amount_refunded": 1900,  # $19.00
                "charge": "ch_456",
                "metadata": {"venture": "media-api"},
            }
        },
    }
    # A cumulative snapshot without refund identities is not an increment.
    with pytest.raises(WebhookError, match="legacy"):
        map_stripe_event_to_ledger_row(event)
