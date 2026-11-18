"""Small canonical signed-evidence primitive. Keys live outside evaluated code."""

from __future__ import annotations

import base64
import hashlib
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class TrustError(ValueError):
    pass


def canonical(value):
    def check(item):
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(k) is str for k in item):
            for child in item.values():
                check(child)
            return
        raise TrustError("canonical_integer_json_required")

    check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def encode(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def decode(value):
    if type(value) is not str or len(value) > 32768:
        raise TrustError("invalid_encoding")
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except ValueError as exc:
        raise TrustError("invalid_encoding") from exc
    if encode(raw) != value:
        raise TrustError("noncanonical_encoding")
    return raw


def sign(private_key, key_id, value):
    return {
        "payload": value,
        "key_id": key_id,
        "signature": encode(private_key.sign(canonical(value))),
    }


def verify(envelope, trusted, role):
    try:
        if set(envelope) != {"payload", "key_id", "signature"}:
            raise TrustError("exact_signed_envelope_required")
        entry = trusted[envelope["key_id"]]
        if role not in entry["roles"] or entry.get("revoked") is not False:
            raise TrustError("signer_not_authorized")
        Ed25519PublicKey.from_public_bytes(decode(entry["public_key"])).verify(
            decode(envelope["signature"]), canonical(envelope["payload"])
        )
        return envelope["payload"]
    except (KeyError, TypeError, InvalidSignature, ValueError) as exc:
        raise TrustError("trusted_current_signature_required") from exc
