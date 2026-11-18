"""Deterministic SYNTHETIC expanded Stripe-subset fixtures for tests/offline demo.

Not downloaded events, real customers, processor settlement, legal accounting policy
or protocol certification. Never configure a live account from these examples.
"""
from __future__ import annotations

import copy
import json

from economic import API_VERSION, Scope


def scope(account='acct_fixture', venture='media-api'):
    return Scope(account, venture)


def charge(suffix='sale', amount=10000):
    return {'object': 'charge', 'livemode': False, 'id': 'ch_' + suffix, 'payment_intent': 'pi_' + suffix,
            'amount': amount, 'amount_captured': amount, 'currency': 'usd',
            'paid': True, 'captured': True, 'status': 'succeeded', 'disputed': False,
            'metadata': {'venture': 'media-api'}}


def intent(suffix='sale', amount=10000):
    return {'object': 'payment_intent', 'livemode': False, 'id': 'pi_' + suffix, 'currency': 'usd',
            'status': 'succeeded', 'amount': amount, 'amount_received': amount,
            'latest_charge': charge(suffix, amount), 'metadata': {'venture': 'media-api'}}


def invoice(suffix='sale', amount=10000):
    return {'object': 'invoice', 'livemode': False, 'id': 'in_' + suffix, 'currency': 'usd',
            'amount_paid': amount, 'status': 'paid', 'paid': True, 'paid_out_of_band': False,
            'payment_intent': intent(suffix, amount), 'metadata': {'venture': 'media-api'}}


def checkout(suffix='sale', amount=10000):
    return {'object': 'checkout.session', 'livemode': False, 'id': 'cs_' + suffix, 'currency': 'usd',
            'mode': 'payment', 'status': 'complete', 'payment_status': 'paid',
            'amount_total': amount, 'payment_intent': intent(suffix, amount),
            'metadata': {'venture': 'media-api'}}


def refund(suffix='first', amount=2000, sale='sale'):
    return {'object': 'refund', 'livemode': False, 'id': 're_' + suffix, 'charge': 'ch_' + sale,
            'payment_intent': 'pi_' + sale, 'currency': 'usd', 'amount': amount,
            'status': 'succeeded', 'metadata': {'venture': 'media-api'}}


def snapshot(refunds=None, sale='sale', amount=10000):
    refunds = [refund()] if refunds is None else copy.deepcopy(refunds)
    obj = charge(sale, amount)
    obj.update(amount_refunded=sum(r['amount'] for r in refunds),
               refunds={'object': 'list', 'has_more': False, 'data': refunds})
    return obj


def event(kind='invoice.paid', obj=None, identity=None, account='acct_fixture'):
    return {'id': identity or 'evt_' + kind.replace('.', '_'), 'type': kind,
            'api_version': API_VERSION, 'livemode': False, 'account': account,
            'data': {'object': invoice() if obj is None else copy.deepcopy(obj)}}


def encoded(kind='invoice.paid', obj=None, identity=None, account='acct_fixture'):
    # Negative UNIT cases may intentionally contain NaN, which the parser must refuse.
    return json.dumps(event(kind, obj, identity, account), sort_keys=True, separators=(',', ':')).encode()
