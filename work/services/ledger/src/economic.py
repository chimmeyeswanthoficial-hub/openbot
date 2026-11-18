"""Strict, offline Stripe-fixture normalization. NOT live payment/settlement authority.

Only the documented 2024-06-20 expanded-object subset is supported. Missing facts
stay unresolved; no network lookups, FX guesses, float money, metadata authority,
provider account creation or bank-settlement claims exist in this module.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from typing import Literal

API_VERSION = '2024-06-20'
MAX_BODY_BYTES = 131_072
MAX_MINOR = (1 << 53) - 1  # exact JSON integer round-trip bound, NOT a spend budget
MAX_REFUNDS = 100


class EconomicError(ValueError):
    def __init__(self, code: str, http_status: int = 422):
        super().__init__(code)  # codes only: never echo provider bodies/credentials
        self.code, self.http_status = code, http_status


class EconomicConflict(EconomicError):
    def __init__(self, code='economic_conflict'):
        super().__init__(code, 409)


class EconomicUnavailable(RuntimeError):
    def __init__(self, *, uncertain=False):
        super().__init__('economic_store_unavailable')
        self.uncertain = uncertain


class _Unresolved(Exception):
    pass


def identifier(value, prefix: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(re.escape(prefix) + r'[A-Za-z0-9_]{1,96}', value):
        raise EconomicError('invalid_object_identity')
    return value


def minor(value) -> int:
    if type(value) is not int or not 0 <= value <= MAX_MINOR:
        raise EconomicError('invalid_minor_units')
    return value


def _currency(obj):
    if obj.get('currency') != 'usd':
        raise EconomicError('unsupported_currency')


def _link(value, prefix):
    if value is None:
        raise _Unresolved('economic_link_required')
    if isinstance(value, dict):
        raise _Unresolved('unexpanded_backlink_id_required')
    return identifier(value, prefix)


@dataclass(frozen=True)
class Scope:
    account: str
    venture: str
    livemode: bool = False
    api_version: str = API_VERSION
    account_mode: Literal['own', 'connected'] = 'own'

    def __post_init__(self):
        identifier(self.account, 'acct_')
        if not isinstance(self.venture, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', self.venture):
            raise EconomicError('invalid_host_venture')
        if self.livemode is not False or self.api_version != API_VERSION:
            raise EconomicError('synthetic_profile_only')
        if not isinstance(self.account_mode, str) or self.account_mode not in {'own', 'connected'}:
            raise EconomicError('invalid_host_account_mode')


@dataclass(frozen=True)
class Posting:
    kind: Literal['capture', 'refund']
    economic_id: str
    amount_minor: int
    currency: str
    venture: str
    parent_id: str = ''
    payment_intent_id: str = ''
    expected_parent_amount_minor: int | None = None  # snapshot witness, not a new monetary posting

    def fingerprint(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@dataclass(frozen=True)
class Plan:
    scope: Scope
    event_id: str
    event_type: str
    payload_sha256: str
    candidates: tuple[Posting, ...] = ()
    reason: str = ''

    def encoded_candidates(self):
        return json.dumps([asdict(p) for p in self.candidates], sort_keys=True, separators=(',', ':'))


def _metadata(obj, scope):
    if 'livemode' not in obj:
        raise _Unresolved('object_environment_required')
    if obj['livemode'] is not False:
        raise EconomicError('object_environment_scope_mismatch', 403)
    meta = obj.get('metadata', {})
    if not isinstance(meta, dict):
        raise EconomicError('invalid_metadata')
    if 'venture' in meta and meta['venture'] != scope.venture:
        raise EconomicError('venture_scope_mismatch', 403)
    if any(obj.get(key) is not None for key in ('on_behalf_of', 'transfer_data', 'source_transfer',
                                               'transfer', 'application_fee', 'application_fee_amount')):
        raise _Unresolved('unsupported_account_flow')


def _object(obj, kind):
    if not isinstance(obj, dict) or obj.get('object') != kind:
        raise _Unresolved('expanded_object_required')
    return obj


def _capture(obj, scope):
    obj = _object(obj, 'charge')
    _metadata(obj, scope)
    identity = identifier(obj.get('id'), 'ch_')
    _currency(obj)
    amount, captured = minor(obj.get('amount')), minor(obj.get('amount_captured'))
    if (obj.get('status') != 'succeeded' or obj.get('paid') is not True
            or obj.get('captured') is not True):
        raise _Unresolved('capture_not_verified')
    if obj.get('disputed') is not False:
        raise _Unresolved('disputed_or_unknown_charge')
    if captured != amount:
        raise _Unresolved('partial_or_changing_capture_unsupported')
    parent = _link(obj.get('payment_intent'), 'pi_')
    return Posting('capture', identity, captured, 'usd', scope.venture, payment_intent_id=parent)


def _intent(obj, scope):
    obj = _object(obj, 'payment_intent')
    _metadata(obj, scope)
    identity = identifier(obj.get('id'), 'pi_')
    _currency(obj)
    received = minor(obj.get('amount_received'))
    if obj.get('status') != 'succeeded':
        raise _Unresolved('payment_not_succeeded')
    capture = _capture(obj.get('latest_charge'), scope)
    if capture.payment_intent_id != identity or capture.amount_minor != received:
        raise EconomicConflict('inconsistent_capture_link')
    return capture


def _refund(obj, scope, expected_parent=None):
    obj = _object(obj, 'refund')
    _metadata(obj, scope)
    identity = identifier(obj.get('id'), 're_')
    _currency(obj)
    amount = minor(obj.get('amount'))
    parent = _link(obj.get('charge'), 'ch_')
    if expected_parent and parent != expected_parent:
        raise EconomicConflict('refund_parent_conflict')
    if obj.get('status') != 'succeeded':
        raise _Unresolved('refund_not_succeeded')
    intent = _link(obj['payment_intent'], 'pi_') if obj.get('payment_intent') is not None else ''
    return Posting('refund', identity, amount, 'usd', scope.venture, parent, intent)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EconomicError('duplicate_json_key', 400)
        result[key] = value
    return result


def _constant(_):
    raise EconomicError('nonfinite_json_number', 400)


def prepare_event(payload: bytes, scope: Scope) -> Plan:
    if not isinstance(scope, Scope):
        raise EconomicError('host_scope_required')
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_BODY_BYTES:
        raise EconomicError('invalid_body_size', 413)
    try:
        event = json.loads(payload.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, EconomicError):
            raise
        raise EconomicError('invalid_json', 400) from exc
    if not isinstance(event, dict):
        raise EconomicError('invalid_event', 400)
    event_id = identifier(event.get('id'), 'evt_')
    event_type = event.get('type')
    if not isinstance(event_type, str) or not re.fullmatch(r'[a-z_.]{1,96}', event_type):
        raise EconomicError('invalid_event_type')
    if event.get('livemode') is not False:
        raise EconomicError('environment_scope_mismatch', 403)
    # Own-account events may omit account. The expected account is a trusted host binding.
    if scope.account_mode == 'connected' and 'account' not in event:
        raise EconomicError('connected_account_envelope_required', 403)
    if 'account' in event and event['account'] != scope.account:
        raise EconomicError('account_scope_mismatch', 403)
    plan = Plan(scope, event_id, event_type, hashlib.sha256(payload).hexdigest())
    if event.get('api_version') != scope.api_version:
        return replace(plan, reason='unsupported_api_version')
    data = event.get('data')
    if not isinstance(data, dict) or not isinstance(data.get('object'), dict):
        raise EconomicError('invalid_event_object')
    obj = data['object']
    try:
        _metadata(obj, scope)
        if event_type in {'charge.succeeded', 'charge.captured'}:
            candidates = (_capture(obj, scope),)
        elif event_type == 'payment_intent.succeeded':
            candidates = (_intent(obj, scope),)
        elif event_type == 'invoice.paid':
            _object(obj, 'invoice')
            identifier(obj.get('id'), 'in_')
            _currency(obj)
            paid = minor(obj.get('amount_paid'))
            if obj.get('status') != 'paid' or obj.get('paid') is not True or obj.get('paid_out_of_band') is not False:
                raise _Unresolved('invoice_payment_unverified_or_out_of_band')
            candidate = _intent(obj.get('payment_intent'), scope)
            if candidate.amount_minor != paid:
                raise EconomicConflict('invoice_capture_amount_conflict')
            candidates = (candidate,)
        elif event_type == 'checkout.session.completed':
            _object(obj, 'checkout.session')
            identifier(obj.get('id'), 'cs_')
            _currency(obj)
            total = minor(obj.get('amount_total'))
            if obj.get('mode') != 'payment' or obj.get('status') != 'complete' or obj.get('payment_status') != 'paid':
                raise _Unresolved('checkout_not_paid_or_unsupported_mode')
            candidate = _intent(obj.get('payment_intent'), scope)
            if candidate.amount_minor != total:
                raise EconomicConflict('checkout_capture_amount_conflict')
            candidates = (candidate,)
        elif event_type in {'refund.created', 'refund.updated', 'charge.refund.updated'}:
            candidates = (_refund(obj, scope),)
        elif event_type == 'charge.refunded':
            _object(obj, 'charge')
            _currency(obj)
            parent_witness = _capture(obj, scope)
            identity = parent_witness.economic_id
            cumulative = minor(obj.get('amount_refunded'))
            refunds = obj.get('refunds')
            if (not isinstance(refunds, dict) or refunds.get('object') != 'list'
                    or refunds.get('has_more') is not False or not isinstance(refunds.get('data'), list)
                    or len(refunds['data']) > MAX_REFUNDS):
                raise _Unresolved('unresolved_cumulative_snapshot')
            candidates = tuple(_refund(item, scope, identity) for item in refunds['data'])
            if any(p.payment_intent_id and p.payment_intent_id != parent_witness.payment_intent_id for p in candidates):
                raise EconomicConflict('snapshot_refund_intent_conflict')
            candidates = tuple(replace(p, payment_intent_id=parent_witness.payment_intent_id,
                                       expected_parent_amount_minor=parent_witness.amount_minor) for p in candidates)
            if len({p.economic_id for p in candidates}) != len(candidates):
                raise EconomicConflict('duplicate_refund_identity_in_snapshot')
            if not candidates or sum(p.amount_minor for p in candidates) != cumulative:
                raise _Unresolved('unresolved_cumulative_snapshot')
        else:
            raise _Unresolved('unsupported_event_type')
    except _Unresolved as exc:
        return replace(plan, reason=str(exc))
    return replace(plan, candidates=candidates)
