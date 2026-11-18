"""Raw-body Stripe signature verification; retired unsafe event-ID-only mapper.

Economic writes use economic.prepare_event and the explicit synthetic canonical
book. A signature verifies delivery authenticity, not currency, paid status,
economic identity, host authority, settlement or permission to move money.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import time
from typing import Any


class WebhookError(ValueError):
    pass


def verify_stripe_signature(payload: bytes, sig_header: str | None, secret: str, *,
                            tolerance: int = 300, current_time: int | None = None) -> bool:
    if (not isinstance(payload, bytes) or not isinstance(sig_header, str) or len(sig_header) > 4096
            or not isinstance(secret, str) or not secret or len(secret) > 4096 or not secret.isascii()
            or type(tolerance) is not int or not 1 <= tolerance <= 900):
        return False
    timestamp, signatures = [], []
    for element in sig_header.split(','):
        pair = element.strip().split('=', 1)
        if len(pair) != 2:
            return False
        key, value = pair
        if key == 't':
            timestamp.append(value)
        elif key == 'v1':
            signatures.append(value)
    if (len(timestamp) != 1 or not re.fullmatch(r'[0-9]{1,12}', timestamp[0])
            or not 1 <= len(signatures) <= 8):
        return False
    now = int(time.time()) if current_time is None else current_time
    if type(now) is not int or abs(now - int(timestamp[0])) > tolerance:
        return False
    signed = timestamp[0].encode('ascii') + b'.' + payload
    expected = hmac.new(secret.encode('utf-8'), signed, hashlib.sha256).hexdigest()
    return any(re.fullmatch('[a-f0-9]{64}', value) is not None and hmac.compare_digest(expected, value)
               for value in signatures)


def map_stripe_event_to_ledger_row(event: dict[str, Any]) -> dict[str, Any] | None:
    """Compatibility symbol that FAILS CLOSED rather than producing unsafe rows.

    The old one-row mapper double-counted linked notifications and cumulative
    refunds and mislabeled non-USD amounts. It cannot express a transactional
    canonical batch. Use the explicitly versioned synthetic economic API instead.
    """
    raise WebhookError('legacy event-ID-only mapper retired; canonical economic ingestion required')
