"""Legacy transport must not invent a stop, delivery, spend proof or replay permission."""
from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from dispatch_agui import AGUIDispatcher
from repository import Store


def spec(**kw):
    return SimpleNamespace(**{'id': 'fixture', 'venture': 'transport-fixture', 'bot': 'ceo',
                              'body': 'synthetic fixture', 'budget_usd': 2.0,
                              'max_runtime_min': 1, 'outputs': [{'channel': '#draft-only'}], **kw})


def setup(transport):
    store = Store()
    rid = store.start_run('fixture', 'transport-fixture')
    return store, rid, AGUIDispatcher(store=store, transport=transport)


@pytest.mark.parametrize('error', [TimeoutError, ConnectionError, RuntimeError])
def test_unknown_transport_outcome_never_means_killed_or_safe_retry(error):
    def uncertain(*_):
        raise error('synthetic-sensitive-error-do-not-publish')
    store, rid, dispatch = setup(uncertain)
    result = dispatch.execute_turn(spec(), rid)
    assert not result['ok'] and result['status'] == 'reconciliation_required'
    assert result['stop_confirmed'] is False and result['delivery_confirmed'] is False
    assert result['automatic_retry_allowed'] is False and result['cost_usd'] is None
    assert store.runs(1)[0]['status'] == 'reconciliation_required'
    assert all('killed' not in r['rule'] for r in store.audit_tail(20))
    assert 'synthetic-sensitive-error-do-not-publish' not in json.dumps(store.audit_tail(20))


@pytest.mark.parametrize('value', [None, True, False, '0.1', 'bad', math.nan, math.inf, -1, {}, 1e20])
def test_malformed_or_nonfinite_reported_cost_is_never_success(value):
    store, rid, dispatch = setup(lambda *_: {'output': 'candidate', 'cost_usd': value})
    result = dispatch.execute_turn(spec(), rid)
    assert not result['ok'] and result['status'] == 'reconciliation_required'
    assert result['cost_usd'] is None and result['delivery_confirmed'] is False
    assert store.runs(1)[0]['cost_usd'] == 0.0
    assert not store.ledger_rows()


@pytest.mark.parametrize('reply', [{}, {'cost_usd': 0}, {'cost_usd': 0, 'output': ''},
                                    {'cost_usd': 0, 'output': {}},
                                    {'cost_usd': 0, 'output': 'x', 'ok': False},
                                    {'cost_usd': 0, 'output': 'x', 'message': 'different'},
                                    {'cost_usd': 0, 'output': 'x' * 65537}, []])
def test_no_fabricated_output_or_completion(reply):
    _, rid, dispatch = setup(lambda *_: reply)
    result = dispatch.execute_turn(spec(), rid)
    assert not result['ok'] and result['status'] == 'reconciliation_required'
    assert not result.get('outputs') and result['delivery_confirmed'] is False


@pytest.mark.parametrize('invalid', [{'budget_usd': math.nan}, {'budget_usd': -1},
                                      {'budget_usd': True}, {'max_runtime_min': 0},
                                      {'bot': 'not-an-approved-bot'}])
def test_invalid_host_plan_never_reaches_transport(invalid):
    calls = []
    _, rid, dispatch = setup(lambda *_: calls.append(True))
    result = dispatch.execute_turn(spec(**invalid), rid)
    assert not result['ok'] and not calls


def test_no_store_means_no_transport_call():
    calls = []
    result = AGUIDispatcher(transport=lambda *_: calls.append(True)).execute_turn(spec(), 'missing')
    assert not result['ok'] and not calls


def test_default_network_transport_is_disabled_before_side_effect(monkeypatch):
    calls = []
    monkeypatch.setattr('urllib.request.urlopen', lambda *_a, **_k: calls.append(True))
    store = Store()
    rid = store.start_run('fixture', 'transport-fixture')
    result = AGUIDispatcher(store=store).execute_turn(spec(), rid)
    assert not result['ok'] and result['code'] == 'runtime.unconfigured'
    assert not calls


@pytest.mark.parametrize('stored_routine,stored_venture', [('other', 'transport-fixture'),
                                                        ('fixture', 'another-venture')])
def test_run_scope_is_verified_before_transport(stored_routine, stored_venture):
    calls = []
    store = Store()
    rid = store.start_run(stored_routine, stored_venture)
    result = AGUIDispatcher(store=store, transport=lambda *_: calls.append(True)).execute_turn(spec(), rid)
    assert not result['ok'] and not calls


def test_pre_effect_audit_failure_refuses_without_transport(monkeypatch):
    calls = []
    store, rid, dispatch = setup(lambda *_: calls.append(True))
    def broken(_):
        raise OSError('fixture audit unavailable')
    monkeypatch.setattr(Store, 'audit', lambda *_: broken(None))
    result = dispatch.execute_turn(spec(), rid)
    assert not result['ok'] and not calls


def test_reported_overspend_is_not_a_kill_receipt_or_settled_cost():
    store, rid, dispatch = setup(lambda *_: {'output': 'candidate', 'cost_usd': 15})
    result = dispatch.execute_turn(spec(), rid)
    assert result['code'] == 'budget.exceeded' and result['status'] == 'reconciliation_required'
    assert result['reported_cost_usd'] == 15 and result['cost_usd'] is None
    assert not result['stop_confirmed'] and not result['delivery_confirmed']
    assert store.runs(1)[0]['cost_usd'] == 0 and not store.ledger_rows()


def test_adapter_response_is_only_an_unverified_draft_not_delivery_or_settlement():
    store, rid, dispatch = setup(lambda *_: {'output': 'candidate', 'cost_usd': 0.45})
    result = dispatch.execute_turn(spec(), rid)
    assert result['ok'] and result['status'] == 'response_received'
    assert result['outputs'][0]['content'] == 'candidate'
    assert not result['delivery_confirmed'] and result['delivery_status'] == 'not_attempted'
    assert result['reported_cost_usd'] == 0.45 and result['cost_usd'] is None
    assert result['reservation_enforced'] is False and not store.ledger_rows()


def test_restart_or_repeated_call_cannot_dispatch_same_run_twice(tmp_path):
    path = str(tmp_path / 'store.sqlite3')
    calls = []
    store = Store(path)
    rid = store.start_run('fixture', 'transport-fixture')
    def transport(*_):
        calls.append(True)
        return {'output': 'candidate', 'cost_usd': 0}
    assert AGUIDispatcher(store=store, transport=transport).execute_turn(spec(), rid)['ok']
    restarted = Store(path)
    assert not AGUIDispatcher(store=restarted, transport=transport).execute_turn(spec(), rid)['ok']
    assert len(calls) == 1


def test_independent_connections_cannot_claim_same_transport_attempt(tmp_path):
    path = str(tmp_path / 'store.sqlite3')
    primary = Store(path)
    rid = primary.start_run('fixture', 'transport-fixture')
    stores = [Store(path) for _ in range(10)]
    calls = []
    def transport(*_):
        calls.append(True)
        return {'output': 'candidate', 'cost_usd': 0}
    def dispatch(store):
        return AGUIDispatcher(store=store, transport=transport).execute_turn(spec(), rid)
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(dispatch, stores))
    assert len(calls) == 1 and sum(r['ok'] for r in results) == 1


@pytest.mark.parametrize('reply', [{'output': 'candidate', 'cost_usd': 10 ** 1000},
                                   {'output': 'candidate', 'cost_usd': 0, 'status': []},
                                   {'output': '\ud800', 'cost_usd': 0},
                                   {'output': 'candidate', 'cost_usd': 0, 'run_id': 'other-run'}])
def test_adversarial_response_is_refused_without_escaping_dispatcher(reply):
    _, rid, dispatch = setup(lambda *_: reply)
    result = dispatch.execute_turn(spec(), rid)
    assert not result['ok'] and result['status'] == 'reconciliation_required'


def test_unconfirmed_audit_number_blocks_effect(monkeypatch):
    calls = []
    _, rid, dispatch = setup(lambda *_: calls.append(True))
    monkeypatch.setattr(Store, 'audit', lambda *_: True)
    assert not dispatch.execute_turn(spec(), rid)['ok'] and not calls


def test_post_effect_persistence_failure_is_not_success_or_replay(monkeypatch):
    calls = []
    store, rid, dispatch = setup(lambda *_: calls.append(True) or {'output': 'candidate', 'cost_usd': 0})
    monkeypatch.setattr(Store, 'finish_run_dispatch', lambda *_: False)
    result = dispatch.execute_turn(spec(), rid)
    assert not result['ok'] and result['status'] == 'reconciliation_required'
    assert not dispatch.execute_turn(spec(), rid)['ok'] and len(calls) == 1
    assert store.runs(1)[0]['status'] == 'dispatching'


def test_unknown_outcome_consumes_run_claim_across_reinstantiation():
    calls = []
    def transport(*_):
        calls.append(True)
        raise TimeoutError('fixture')
    store, rid, dispatch = setup(transport)
    assert not dispatch.execute_turn(spec(), rid)['ok']
    assert not AGUIDispatcher(store=store, transport=transport).execute_turn(spec(), rid)['ok']
    assert len(calls) == 1


def test_scoped_claim_accepts_queued_work_but_never_a_finished_run():
    store, rid, dispatch = setup(lambda *_: {'output': 'candidate', 'cost_usd': 0})
    store.end_run(rid, 'queued', 0, 'fixture queued')
    assert dispatch.execute_turn(spec(), rid)['ok']
    assert not dispatch.execute_turn(spec(), rid)['ok']
