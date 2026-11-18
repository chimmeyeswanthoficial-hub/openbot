"""Pure canonical normalization: no provider, real event, money or database."""
from __future__ import annotations

import json
from dataclasses import asdict

import pytest
from economic import MAX_BODY_BYTES, MAX_MINOR, EconomicError, Scope, prepare_event
from economic_fixtures import (
    charge,
    checkout,
    encoded,
    event,
    intent,
    invoice,
    refund,
    scope,
    snapshot,
)


@pytest.mark.parametrize('kind,obj', [
    ('invoice.paid', invoice()), ('payment_intent.succeeded', intent()),
    ('checkout.session.completed', checkout()), ('charge.succeeded', charge()),
    ('charge.captured', charge()),
])
def test_all_supported_sale_families_share_authoritative_charge_identity(kind, obj):
    plan = prepare_event(encoded(kind, obj), scope())
    assert plan.reason == '' and len(plan.candidates) == 1
    posting = plan.candidates[0]
    assert posting.kind == 'capture' and posting.economic_id == 'ch_sale'
    assert posting.amount_minor == 10000 and type(posting.amount_minor) is int
    assert posting.payment_intent_id == 'pi_sale' and posting.currency == 'usd'


@pytest.mark.parametrize('kind', ['refund.created', 'refund.updated', 'charge.refund.updated'])
def test_individual_succeeded_refund_has_stable_identity(kind):
    posting = prepare_event(encoded(kind, refund()), scope()).candidates[0]
    assert posting.kind == 'refund' and posting.economic_id == 're_first'
    assert posting.parent_id == 'ch_sale' and posting.amount_minor == 2000


def test_complete_snapshot_produces_individual_refunds_not_cumulative_posting():
    plan = prepare_event(encoded('charge.refunded', snapshot([refund(), refund('second', 3000)])), scope())
    assert [p.economic_id for p in plan.candidates] == ['re_first', 're_second']
    assert [p.amount_minor for p in plan.candidates] == [2000, 3000]


@pytest.mark.parametrize('amount', [None, True, False, -1, 1.5, '100', [], {}, MAX_MINOR + 1, float('nan'), float('inf')])
def test_amount_is_an_exact_bounded_integer_not_boolean_or_float(amount):
    obj = charge()
    obj['amount'] = obj['amount_captured'] = amount
    with pytest.raises(EconomicError):
        prepare_event(encoded('charge.succeeded', obj), scope())


@pytest.mark.parametrize('amount', [0, 1, MAX_MINOR])
def test_exact_zero_and_boundary_amounts_are_not_replaced_via_truthiness(amount):
    candidate = prepare_event(encoded('charge.succeeded', charge(amount=amount)), scope()).candidates[0]
    assert candidate.amount_minor == amount


@pytest.mark.parametrize('currency', [None, 'inr', 'USD', '', 123])
def test_non_usd_or_missing_currency_is_not_labeled_usd(currency):
    obj = charge()
    obj['currency'] = currency
    with pytest.raises(EconomicError, match='unsupported_currency'):
        prepare_event(encoded('charge.succeeded', obj), scope())


@pytest.mark.parametrize('field,value', [('livemode', True), ('livemode', 0), ('account', 'acct_foreign')])
def test_host_account_and_test_environment_are_mandatory(field, value):
    obj = event('charge.succeeded', charge())
    obj[field] = value
    with pytest.raises(EconomicError):
        prepare_event(json.dumps(obj).encode(), scope())


def test_own_account_envelope_can_omit_account_but_never_derive_it_from_metadata():
    obj = event('charge.succeeded', charge())
    del obj['account']
    plan = prepare_event(json.dumps(obj).encode(), scope())
    assert plan.scope.account == 'acct_fixture'
    obj['data']['object']['metadata']['venture'] = 'foreign-venture'
    with pytest.raises(EconomicError, match='venture_scope_mismatch'):
        prepare_event(json.dumps(obj).encode(), scope())


@pytest.mark.parametrize('kind,obj,reason', [
    ('invoice.paid', {**invoice(), 'paid_out_of_band': True}, 'invoice_payment'),
    ('invoice.paid', {**invoice(), 'paid': False}, 'invoice_payment'),
    ('checkout.session.completed', {**checkout(), 'payment_status': 'unpaid'}, 'checkout_not_paid'),
    ('checkout.session.completed', {**checkout(), 'mode': 'subscription'}, 'checkout_not_paid'),
    ('payment_intent.succeeded', {**intent(), 'status': 'processing'}, 'payment_not_succeeded'),
    ('charge.succeeded', {**charge(), 'captured': False}, 'capture_not_verified'),
    ('charge.succeeded', {**charge(), 'paid': False}, 'capture_not_verified'),
    ('charge.succeeded', {**charge(), 'disputed': True}, 'disputed_or_unknown'),
    ('charge.succeeded', {**charge(), 'amount_captured': 5000}, 'partial_or_changing'),
    ('refund.created', {**refund(), 'status': 'pending'}, 'refund_not_succeeded'),
    ('refund.updated', {**refund(), 'status': 'failed'}, 'refund_not_succeeded'),
    ('payment_intent.succeeded', {**intent(), 'latest_charge': 'ch_sale'}, 'expanded_object_required'),
    ('invoice.paid', {**invoice(), 'payment_intent': None}, 'expanded_object_required'),
    ('charge.succeeded', {**charge(), 'payment_intent': None}, 'economic_link_required'),
    ('charge.succeeded', {**charge(), 'on_behalf_of': 'acct_other'}, 'unsupported_account_flow'),
    ('charge.succeeded', {**charge(), 'transfer_data': {}}, 'unsupported_account_flow'),
    ('charge.succeeded', {**charge(), 'application_fee_amount': 0}, 'unsupported_account_flow'),
])
def test_missing_or_unverified_facts_are_unresolved_never_invented(kind, obj, reason):
    plan = prepare_event(encoded(kind, obj), scope())
    assert plan.reason.startswith(reason) and not plan.candidates


@pytest.mark.parametrize('mutation', ['missing', 'truncated', 'bad_sum', 'pending_refund', 'empty'])
def test_cumulative_snapshot_requires_complete_successful_individual_evidence(mutation):
    obj = snapshot()
    if mutation == 'missing':
        del obj['refunds']
    elif mutation == 'truncated':
        obj['refunds']['has_more'] = True
    elif mutation == 'bad_sum':
        obj['amount_refunded'] += 1
    elif mutation == 'pending_refund':
        obj['refunds']['data'][0]['status'] = 'pending'
    else:
        obj['refunds']['data'] = []
    plan = prepare_event(encoded('charge.refunded', obj), scope())
    assert plan.reason and not plan.candidates


@pytest.mark.parametrize('kind,obj', [
    ('invoice.paid', {**invoice(), 'amount_paid': 20000}),
    ('checkout.session.completed', {**checkout(), 'amount_total': 20000}),
    ('payment_intent.succeeded', {**intent(), 'amount_received': 20000}),
    ('charge.refunded', snapshot([refund(), refund()])),
])
def test_contradictory_object_links_or_refund_identities_are_conflicts(kind, obj):
    with pytest.raises(EconomicError):
        prepare_event(encoded(kind, obj), scope())


@pytest.mark.parametrize('payload', [b'[]', b'null', b'{bad', b'\xff', b'{"id":"evt_a","id":"evt_b"}', b'', b' ' * (MAX_BODY_BYTES + 1)])
def test_malformed_ambiguous_nonobject_and_oversized_bodies_are_refused(payload):
    with pytest.raises(EconomicError):
        prepare_event(payload, scope())


def test_unknown_version_and_unsupported_money_events_remain_unresolved():
    obj = event('balance.available', charge())
    assert prepare_event(json.dumps(obj).encode(), scope()).reason == 'unsupported_event_type'
    obj['api_version'] = 'unknown-future-version'
    assert prepare_event(json.dumps(obj).encode(), scope()).reason == 'unsupported_api_version'


@pytest.mark.parametrize('account,venture,mode', [('acct_fixture', 'media-api', True), ('wrong', 'media-api', False), ('acct_fixture', '../foreign', False)])
def test_context_is_host_owned_and_synthetic_only(account, venture, mode):
    with pytest.raises(EconomicError):
        Scope(account, venture, mode)


def test_candidate_receipts_minimize_data_and_make_no_settlement_claim():
    obj = invoice()
    obj['customer_email'] = 'private-fixture@example.invalid'
    obj['metadata']['private_note'] = 'fixture-not-for-ledger-storage'
    plan = prepare_event(encoded('invoice.paid', obj), scope())
    serialized = plan.encoded_candidates()
    assert 'private' not in serialized and 'settled' not in serialized
    assert set(asdict(plan.candidates[0])) == {'kind', 'economic_id', 'amount_minor', 'currency',
                                              'venture', 'parent_id', 'payment_intent_id', 'expected_parent_amount_minor'}


def test_connected_account_requires_explicit_envelope_not_only_a_shared_secret():
    obj = event('charge.succeeded', charge())
    connected = Scope('acct_fixture', 'media-api', account_mode='connected')
    assert prepare_event(json.dumps(obj).encode(), connected).candidates
    del obj['account']
    with pytest.raises(EconomicError, match='connected_account_envelope_required'):
        prepare_event(json.dumps(obj).encode(), connected)
    # Own-account binding is deliberately distinct and may omit account.
    assert prepare_event(json.dumps(obj).encode(), scope()).candidates


@pytest.mark.parametrize('kind,obj', [('invoice.paid', invoice()), ('checkout.session.completed', checkout())])
def test_source_object_identity_cannot_be_omitted_even_with_a_valid_nested_charge(kind, obj):
    del obj['id']
    with pytest.raises(EconomicError, match='invalid_object_identity'):
        prepare_event(encoded(kind, obj), scope())


def test_expanded_backlinks_are_outside_v1_subset_not_silently_partially_trusted():
    obj = charge()
    obj['payment_intent'] = {'id': 'pi_sale', 'object': 'payment_intent', 'livemode': True}
    plan = prepare_event(encoded('charge.succeeded', obj), scope())
    assert not plan.candidates and plan.reason == 'unexpanded_backlink_id_required'


def test_missing_object_environment_is_unresolved_not_assumed_from_money_fields():
    obj = charge()
    del obj['livemode']
    plan = prepare_event(encoded('charge.succeeded', obj), scope())
    assert not plan.candidates and plan.reason == 'object_environment_required'


def test_snapshot_refund_intent_must_agree_with_its_parent_witness():
    obj = snapshot()
    obj['refunds']['data'][0]['payment_intent'] = 'pi_wrong'
    with pytest.raises(EconomicError, match='snapshot_refund_intent_conflict'):
        prepare_event(encoded('charge.refunded', obj), scope())


def test_fixture_schema_and_frozen_facts_are_explicitly_pinned_to_runtime_contract():
    import hashlib
    from pathlib import Path

    from economic import API_VERSION, MAX_REFUNDS

    root = Path(__file__).resolve().parents[3]
    profile = json.loads((root / 'audit/fixture-profiles/stripe-2024-06-20.json').read_text())
    assert profile['provider_api_version'] == API_VERSION
    assert profile['money']['max'] == MAX_MINOR and not profile['money']['bound_is_spend_budget']
    source = profile['source_reference']
    assert source['commit'] == '3587026b839435d072b7d220967c476d4c6b9a9b'
    assert {entry['path'] for entry in source['files']} >= {'LICENSE', 'stripe/_api_version.py'}
    for entry in source['files']:
        assert entry['source_url'].startswith('https://raw.githubusercontent.com/stripe/stripe-python/' + source['commit'] + '/')
    for name in ('accepted_subset_schema', 'frozen_arithmetic_facts'):
        entry = profile[name]
        assert hashlib.sha256((root / entry['path']).read_bytes()).hexdigest() == entry['sha256']
    schema = json.loads((root / profile['accepted_subset_schema']['path']).read_text())
    assert schema['properties']['api_version']['const'] == API_VERSION
    assert set(schema['properties']['type']['enum']) == set(profile['supported_event_families'])
    assert schema['$defs']['charge_capture']['properties']['amount']['maximum'] == MAX_MINOR
    snapshot_schema = schema['$defs']['charge_refund_snapshot']['allOf'][1]
    assert snapshot_schema['properties']['refunds']['properties']['data']['maxItems'] == MAX_REFUNDS
