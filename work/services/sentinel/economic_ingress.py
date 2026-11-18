"""Host-owned, explicit disposable test ingress; never an auth/activation substitute.

There is no environment-variable or HTTP setter. The regular app has no instance
configured. A trusted test/operator must supply a disposable book, host scope and
fixture secret. This is NOT AG1 authentication or permission to attach live Stripe.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from economic import MAX_BODY_BYTES, EconomicError, Scope
from economic_repository import EconomicBook
from webhook import verify_stripe_signature


@dataclass(frozen=True)
class SyntheticIngress:
    book: EconomicBook
    scope: Scope
    signing_secret: str = field(repr=False)
    experimental: bool = False
    current_time: Callable[[], int] | None = field(default=None, repr=False)

    def __post_init__(self):
        if (self.experimental is not True or not isinstance(self.scope, Scope)
                or not isinstance(self.book, EconomicBook)
                or not isinstance(self.signing_secret, str) or not 16 <= len(self.signing_secret) <= 4096
                or not self.signing_secret.isascii()
                or self.current_time is not None and not callable(self.current_time)):
            raise EconomicError('explicit_synthetic_host_configuration_required')

    def ingest(self, payload: bytes, signature: str | None):
        if not isinstance(payload, bytes) or len(payload) > MAX_BODY_BYTES:
            raise EconomicError('invalid_body_size', 413)
        now = self.current_time() if self.current_time is not None else None
        if not verify_stripe_signature(payload, signature, self.signing_secret, current_time=now):
            raise EconomicError('invalid_webhook_signature', 400)
        return self.book.ingest(payload, self.scope)
