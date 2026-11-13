"""Stripe webhook receiver and ledger row mapper (T5).

Validates Stripe webhook HMAC signatures, rejects tampered payloads,
and maps payment provider events to ledger rows (revenue, refund, fee)
using the raw provider event ID as idempotency key.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any


class WebhookError(ValueError):
    pass


def verify_stripe_signature(
    payload: bytes,
    sig_header: str | None,
    secret: str,
    *,
    tolerance: int = 300,
    current_time: int | None = None,
) -> bool:
    """Verify Stripe HMAC-SHA256 signature using constant-time comparison."""
    if not sig_header or not secret:
        return False

    elements = dict(item.strip().split("=", 1) for item in sig_header.split(",") if "=" in item)
    timestamp_str = elements.get("t")
    v1_sig = elements.get("v1")

    if not timestamp_str or not v1_sig:
        return False

    try:
        ts = int(timestamp_str)
    except ValueError:
        return False

    now = current_time if current_time is not None else int(time.time())
    if tolerance > 0 and abs(now - ts) > tolerance:
        return False

    signed_payload = f"{ts}.".encode("utf-8") + payload
    expected_sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()

    return hmac.compare_digest(expected_sig, v1_sig)


def map_stripe_event_to_ledger_row(event: dict[str, Any]) -> dict[str, Any] | None:
    """Map a Stripe event to an OpenBot OS ledger row."""
    event_id = event.get("id")
    event_type = event.get("type", "")
    data_obj = (event.get("data") or {}).get("object") or {}

    if not event_id:
        return None

    meta = data_obj.get("metadata") or {}
    venture = meta.get("venture") or "media-api"

    if event_type in ("invoice.paid", "checkout.session.completed", "payment_intent.succeeded"):
        amount_cents = data_obj.get("amount_paid") or data_obj.get("amount_total") or data_obj.get("amount") or 0
        return {
            "venture": venture,
            "kind": "revenue",
            "amount_usd": round(amount_cents / 100.0, 2),
            "source": "stripe",
            "external_id": data_obj.get("id"),
            "idempotency_key": event_id,
            "meta": {"event_type": event_type, "customer": data_obj.get("customer")},
        }

    elif event_type in ("charge.refunded", "refund.created"):
        amount_refunded_cents = data_obj.get("amount_refunded") or data_obj.get("amount") or 0
        return {
            "venture": venture,
            "kind": "refund",
            "amount_usd": round(amount_refunded_cents / 100.0, 2),
            "source": "stripe",
            "external_id": data_obj.get("id"),
            "idempotency_key": event_id,
            "meta": {"event_type": event_type, "charge": data_obj.get("charge")},
        }

    elif event_type in ("balance.transaction.fee", "fee.collected"):
        fee_cents = data_obj.get("fee") or data_obj.get("amount") or 0
        return {
            "venture": venture,
            "kind": "fee",
            "amount_usd": round(fee_cents / 100.0, 2),
            "source": "stripe",
            "external_id": data_obj.get("id"),
            "idempotency_key": event_id,
            "meta": {"event_type": event_type},
        }

    return None

