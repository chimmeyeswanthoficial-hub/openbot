"""Real disposable SQLite atomicity, money identity, process race and crash checks.

These are trusted test processes, NOT hostile-code isolation or live finance proof.
"""
from __future__ import annotations

import itertools
import multiprocessing
import os
import sqlite3

import pytest
from economic import EconomicConflict, EconomicError, EconomicUnavailable, Scope
from economic_fixtures import charge, checkout, encoded, intent, invoice, refund, scope, snapshot
from economic_repository import EconomicBook
from repository import Store


@pytest.fixture()
def book(tmp_path):
    store = Store(str(tmp_path / 'synthetic.sqlite3'))
    instance = EconomicBook(store, experimental=True)
    yield instance
    store._conn.close()


SALE = {'invoice.paid': invoice, 'payment_intent.succeeded': intent, 'checkout.session.completed': checkout,
        'charge.succeeded': charge, 'charge.captured': charge}


@pytest.mark.parametrize('order', list(itertools.permutations(SALE)))
def test_linked_notification_permutations_produce_one_100_dollar_capture(book, order):
    created = 0
    for number, kind in enumerate(order):
        result = book.ingest(encoded(kind, SALE[kind](), f'evt_linked_{number}'), scope())
        assert result['status'] == 'recorded'
        created += result['created_postings']
    summary = book.summary(scope())
    assert created == 1 and summary['capture_minor'] == 10000 and summary['posting_count'] == 1
    assert summary['bank_settlement_verified'] is False
    assert len(book.messages(scope())) == len(order)
    assert {row['event_type'] for row in book.messages(scope())} == set(order)


def test_equal_priced_genuine_distinct_captures_are_not_deduplicated_by_amount(book):
    book.ingest(encoded('charge.succeeded', charge('first'), 'evt_first'), scope())
    book.ingest(encoded('charge.succeeded', charge('second'), 'evt_second'), scope())
    assert book.summary(scope())['capture_minor'] == 20000
    assert book.summary(scope())['posting_count'] == 2


def test_exact_replay_has_no_new_posting_message_or_transition(book):
    payload = encoded()
    first = book.ingest(payload, scope())
    second = book.ingest(payload, scope())
    assert first['message_created'] and first['created_postings'] == 1
    assert not second['message_created'] and second['created_postings'] == 0
    assert len(book.messages(scope())) == 1
    assert book.store._conn.execute('SELECT COUNT(*) FROM economic_v1_events').fetchone()[0] == 1


@pytest.mark.parametrize('conflict', ['message_body', 'amount', 'venture'])
def test_conflicting_message_or_economic_properties_do_not_make_a_second_posting(book, conflict):
    payload = encoded('charge.succeeded', charge(), 'evt_first')
    book.ingest(payload, scope())
    obj = charge()
    target_scope = scope()
    identity = 'evt_second'
    if conflict == 'message_body':
        identity = 'evt_first'
        obj['unused_delivery_note'] = 'changed'
    elif conflict == 'amount':
        obj = charge(amount=20000)
    else:
        del obj['metadata']
        target_scope = Scope('acct_fixture', 'another-venture')
    with pytest.raises(EconomicConflict):
        book.ingest(encoded('charge.succeeded', obj, identity), target_scope)
    assert book.summary(scope())['capture_minor'] == 10000
    assert len(book.messages(scope())) == 1
    assert book.summary(Scope('acct_fixture', 'another-venture'))['posting_count'] == 0


def test_different_host_accounts_have_separate_message_and_posting_namespaces(book):
    book.ingest(encoded(), scope())
    second_scope = Scope('acct_second', 'media-api')
    book.ingest(encoded(account='acct_second'), second_scope)
    assert book.summary(scope())['capture_minor'] == book.summary(second_scope)['capture_minor'] == 10000


@pytest.mark.parametrize('order', list(itertools.permutations((0, 1, 2))))
def test_cumulative_and_individual_refund_families_count_50_not_70(book, order):
    book.ingest(encoded(), scope())
    events = [encoded('charge.refunded', snapshot(), 'evt_refund20'),
              encoded('charge.refunded', snapshot([refund(), refund('second', 3000)]), 'evt_refund50'),
              encoded('refund.created', refund(), 'evt_individual20')]
    for number in order:
        book.ingest(events[number], scope())
    summary = book.summary(scope(), expected_net_minor=5000)
    assert summary['capture_minor'] == 10000 and summary['refund_minor'] == 5000
    assert summary['net_captured_minor'] == 5000 and summary['posting_count'] == 3
    assert summary['statement_fixture_matches'] and summary['statement_fixture_drift_minor'] == 0
    assert {r['economic_id'] for r in book.postings(scope())} == {'ch_sale', 're_first', 're_second'}


def test_refund_before_capture_survives_restart_and_resolves_exactly_once(tmp_path):
    path = str(tmp_path / 'restart.sqlite3')
    store = Store(path)
    book = EconomicBook(store, experimental=True)
    waiting = book.ingest(encoded('refund.created', refund()), scope())
    assert waiting['status'] == 'awaiting_capture' and waiting['created_postings'] == 0
    assert book.summary(scope())['awaiting_capture_messages'] == 1
    store._conn.close()
    store = Store(path)
    book = EconomicBook(store, experimental=True)
    result = book.ingest(encoded(), scope())
    assert result['reconciled_messages'] == 1
    assert book.summary(scope())['net_captured_minor'] == 8000
    assert book.summary(scope())['awaiting_capture_messages'] == 0
    replay = book.ingest(encoded('refund.created', refund()), scope())
    assert replay['status'] == 'recorded' and replay['created_postings'] == 0
    assert book.summary(scope())['posting_count'] == 2
    store._conn.close()


def test_cumulative_only_snapshot_is_retained_as_unresolved_not_guessed(book):
    obj = charge()
    obj['amount_refunded'] = 5000
    pending = book.ingest(encoded('charge.refunded', obj), scope())
    assert pending['status'] == 'unresolved' and pending['created_postings'] == 0
    assert book.summary(scope())['refund_minor'] == 0
    book.ingest(encoded(), scope())
    assert book.summary(scope())['unresolved_messages'] == 1
    assert book.messages(scope())[0]['reason'] == 'unresolved_cumulative_snapshot'


def test_known_overrefund_and_conflicting_batch_roll_back_without_partial_postings(book):
    book.ingest(encoded(), scope())
    book.ingest(encoded('refund.created', refund(), 'evt_valid20'), scope())
    invalid = [refund('new_valid', 3000), refund(amount=3000)]  # re_first already means 2000
    with pytest.raises(EconomicConflict):
        book.ingest(encoded('charge.refunded', snapshot(invalid), 'evt_conflicting_batch'), scope())
    with pytest.raises(EconomicConflict, match='refund_exceeds_capture'):
        book.ingest(encoded('refund.created', refund('over', 9000), 'evt_over'), scope())
    assert book.summary(scope())['refund_minor'] == 2000 and len(book.messages(scope())) == 2
    assert {r['economic_id'] for r in book.postings(scope())} == {'ch_sale', 're_first'}


def test_bad_pending_refund_does_not_block_a_later_valid_capture(book):
    book.ingest(encoded('refund.created', refund(amount=11000)), scope())
    book.ingest(encoded(), scope())
    assert book.summary(scope())['capture_minor'] == 10000 and book.summary(scope())['refund_minor'] == 0
    assert any(r['reason'] == 'refund_exceeds_capture' and r['status'] == 'unresolved' for r in book.messages(scope()))


def test_bounded_inline_reconciliation_exposes_remaining_work_and_operator_can_finish(tmp_path):
    store = Store(str(tmp_path / 'bounded.sqlite3'))
    book = EconomicBook(store, experimental=True, reconcile_limit=2)
    for number in range(5):
        book.ingest(encoded('refund.created', refund(f'pending{number}', 100), f'evt_pending{number}'), scope())
    result = book.ingest(encoded(), scope())
    assert result['reconciled_messages'] == 2 and result['remaining_awaiting_capture'] == 3
    assert book.summary(scope())['refund_minor'] == 200
    for _ in range(3):
        book.reconcile_waiting(scope(), 'ch_sale', limit=2)
    assert book.summary(scope())['awaiting_capture_messages'] == 0
    assert book.summary(scope())['refund_minor'] == 500 and book.summary(scope())['posting_count'] == 6
    store._conn.close()


@pytest.mark.parametrize('table', ['economic_v1_postings', 'economic_v1_links', 'economic_v1_events'])
@pytest.mark.parametrize('action', ['UPDATE', 'DELETE'])
def test_postings_and_evidence_cannot_be_rewritten_through_sql(book, table, action):
    book.ingest(encoded(), scope())
    statement = f'DELETE FROM {table}' if action == 'DELETE' else f'UPDATE {table} SET account=account'
    with pytest.raises(sqlite3.IntegrityError):
        book.store._conn.execute(statement)
    book.store._conn.rollback()
    assert book.summary(scope())['capture_minor'] == 10000


def test_message_identity_is_immutable_and_retained(book):
    book.ingest(encoded(), scope())
    for statement in ('DELETE FROM economic_v1_messages', "UPDATE economic_v1_messages SET payload_sha256='changed'"):
        with pytest.raises(sqlite3.IntegrityError):
            book.store._conn.execute(statement)
        book.store._conn.rollback()
    assert len(book.messages(scope())) == 1


def test_no_implicit_migration_and_legacy_rows_are_preserved_excluded_and_recoverable(tmp_path):
    legacy_path, backup_path = str(tmp_path / 'legacy.sqlite3'), str(tmp_path / 'rollback-fixture.sqlite3')
    store = Store(legacy_path)
    store.post_ledger({'venture': 'media-api', 'kind': 'revenue', 'amount_usd': 42,
                       'source': 'manual', 'idempotency_key': 'old-unverified-row'})
    assert not store._conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'economic_v1_%'").fetchall()
    with pytest.raises(EconomicError):
        EconomicBook(store)
    with sqlite3.connect(backup_path) as backup:
        store._conn.backup(backup)
    before = store.ledger_rows()
    book = EconomicBook(store, experimental=True)
    book.ingest(encoded(), scope())
    assert store.ledger_rows() == before and book.summary(scope())['capture_minor'] == 10000
    assert book.summary(scope())['legacy_rows_excluded']
    rollback = Store(backup_path)
    assert rollback.ledger_rows() == before
    assert not rollback._conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'economic_v1_%'").fetchall()
    rollback._conn.close()
    store._conn.close()


def test_audit_failure_rolls_back_message_and_money_then_safe_same_id_retry(book, monkeypatch):
    original = book._transition
    monkeypatch.setattr(book, '_transition', lambda *_: (_ for _ in ()).throw(OSError('synthetic disk failure')))
    with pytest.raises(EconomicUnavailable) as error:
        book.ingest(encoded(), scope())
    assert not error.value.uncertain
    assert book.messages(scope()) == [] and book.postings(scope()) == []
    monkeypatch.setattr(book, '_transition', original)
    assert book.ingest(encoded(), scope())['created_postings'] == 1


def test_after_commit_response_loss_is_uncertain_not_a_claim_of_no_effect(book):
    def fail(stage):
        if stage == 'after_commit':
            raise OSError('synthetic response loss after commit')
    book.fault_hook = fail
    with pytest.raises(EconomicUnavailable) as error:
        book.ingest(encoded(), scope())
    assert error.value.uncertain
    book.fault_hook = None
    assert book.summary(scope())['posting_count'] == 1
    assert not book.ingest(encoded(), scope())['message_created']


def _process_ingest(path, payload, barrier, queue):
    store = Store(path)
    book = EconomicBook(store, experimental=True)
    barrier.wait(timeout=15)
    try:
        queue.put(book.ingest(payload, scope()))
    except EconomicConflict:
        queue.put({'conflict': True})
    finally:
        store._conn.close()


@pytest.mark.parametrize('case', ['same_message', 'linked_notifications', 'refund_duplicates', 'conflicting_amounts'])
def test_independent_process_races_have_one_canonical_effect(tmp_path, case):
    path = str(tmp_path / 'concurrent.sqlite3')
    store = Store(path)
    book = EconomicBook(store, experimental=True)
    if case == 'refund_duplicates':
        book.ingest(encoded(), scope())
    payloads = []
    for number in range(4):
        if case == 'same_message':
            payloads.append(encoded())
        elif case == 'linked_notifications':
            kind = list(SALE)[number % 3]
            payloads.append(encoded(kind, SALE[kind](), f'evt_process{number}'))
        elif case == 'refund_duplicates':
            payloads.append(encoded('refund.created', refund(), f'evt_process{number}'))
        else:
            payloads.append(encoded('charge.succeeded', charge(amount=10000 if number < 2 else 20000), f'evt_process{number}'))
    context = multiprocessing.get_context('spawn')
    barrier, queue = context.Barrier(4), context.Queue()
    processes = [context.Process(target=_process_ingest, args=(path, payload, barrier, queue)) for payload in payloads]
    try:
        for process in processes:
            process.start()
        results = [queue.get(timeout=20) for _ in processes]
        for process in processes:
            process.join(20)
            assert process.exitcode == 0
        summary = book.summary(scope())
        if case == 'refund_duplicates':
            assert summary['refund_minor'] == 2000 and summary['posting_count'] == 2
        else:
            assert summary['posting_count'] == 1
            assert summary['capture_minor'] in ({10000, 20000} if case == 'conflicting_amounts' else {10000})
        if case != 'conflicting_amounts':
            assert sum(r['created_postings'] for r in results) == 1
        if case == 'same_message':
            assert sum(r['message_created'] for r in results) == 1
        if case == 'conflicting_amounts':
            assert sum(r.get('conflict', False) for r in results) == 2
            assert len(book.messages(scope())) == 2
    finally:
        for process in processes:
            if process.is_alive():
                process.kill()
            process.join(5)
        queue.close()
        store._conn.close()


def _crash_process(path, stage):
    store = Store(path)
    def fault(observed):
        if stage == observed:
            os._exit(79)  # actual abrupt trusted-process death, no finally/rollback hook
    EconomicBook(store, experimental=True, fault_hook=fault).ingest(encoded(), scope())


@pytest.mark.parametrize('stage', ['before_message', 'after_message', 'after_postings', 'before_commit', 'after_commit'])
def test_actual_process_death_has_atomic_explainable_restart_and_same_id_replay(tmp_path, stage):
    path = str(tmp_path / 'crash.sqlite3')
    context = multiprocessing.get_context('spawn')
    process = context.Process(target=_crash_process, args=(path, stage))
    process.start()
    process.join(20)
    try:
        assert process.exitcode == 79
    finally:
        if process.is_alive():
            process.kill()
            process.join(5)
    store = Store(path)
    book = EconomicBook(store, experimental=True)
    count = book.summary(scope())['posting_count']
    assert count == (1 if stage == 'after_commit' else 0)
    replay = book.ingest(encoded(), scope())
    assert replay['created_postings'] == (0 if stage == 'after_commit' else 1)
    assert book.summary(scope())['posting_count'] == 1 and book.summary(scope())['capture_minor'] == 10000
    store._conn.close()


def test_refund_snapshot_must_not_ignore_a_conflicting_parent_capture_amount(book):
    book.ingest(encoded(), scope())
    obj = snapshot()
    obj['amount'] = obj['amount_captured'] = 20000
    with pytest.raises(EconomicConflict):
        book.ingest(encoded('charge.refunded', obj), scope())
    assert book.summary(scope())['refund_minor'] == 0


def test_insert_or_replace_must_not_bypass_append_only_guards(book):
    book.ingest(encoded(), scope())
    with pytest.raises(sqlite3.IntegrityError):
        book.store._conn.execute(
            "INSERT OR REPLACE INTO economic_v1_postings SELECT provider,account,environment,kind,economic_id,"
            "venture,9999,currency,parent_id,payment_intent_id,fingerprint,first_event_id,recorded_at "
            "FROM economic_v1_postings")
    book.store._conn.rollback()
    assert book.summary(scope())['capture_minor'] == 10000


@pytest.mark.parametrize('kind,obj', [('charge.succeeded', charge()), ('refund.created', refund())])
def test_nested_live_object_cannot_be_mixed_into_a_test_book(book, kind, obj):
    obj = dict(obj, livemode=True)
    with pytest.raises(EconomicError) as error:
        book.ingest(encoded(kind, obj), scope())
    assert error.value.http_status == 403
    assert book.messages(scope()) == []


def test_one_payment_intent_cannot_claim_two_capture_identities(book):
    book.ingest(encoded(), scope())
    obj = charge()
    obj['id'] = 'ch_second_identity'
    with pytest.raises(EconomicConflict, match='intent_capture_conflict'):
        book.ingest(encoded('charge.succeeded', obj), scope())
    assert book.summary(scope())['capture_minor'] == 10000


def test_actual_database_audit_failure_is_not_misreported_as_duplicate(book):
    book.store._conn.execute("CREATE TRIGGER fixture_fail_audit BEFORE INSERT ON economic_v1_events "
                             "BEGIN SELECT RAISE(ABORT,'synthetic audit outage'); END")
    with pytest.raises(EconomicUnavailable) as error:
        book.ingest(encoded(), scope())
    assert not error.value.uncertain
    assert book.messages(scope()) == [] and book.postings(scope()) == []
    book.store._conn.execute('DROP TRIGGER fixture_fail_audit')
    assert book.ingest(encoded(), scope())['created_postings'] == 1


def test_constructor_refuses_borrowed_transaction_without_rolling_back_caller_data(tmp_path):
    store = Store(str(tmp_path / 'unowned.sqlite3'))
    store._conn.execute("INSERT INTO ledger(ts,venture,kind,amount_usd,source,idempotency_key) "
                        "VALUES('unit','media-api','revenue',42,'manual','uncommitted-caller')")
    try:
        with pytest.raises(EconomicError, match='existing_transaction_not_owned'):
            EconomicBook(store, experimental=True)
        assert store._conn.in_transaction
        assert store._conn.execute('SELECT COUNT(*) FROM ledger').fetchone()[0] == 1
    finally:
        store._conn.rollback()
        store._conn.close()


def test_ingest_refuses_borrowed_transaction_without_rolling_back_caller_data(book):
    book.store._conn.execute("INSERT INTO ledger(ts,venture,kind,amount_usd,source,idempotency_key) "
                             "VALUES('unit','media-api','revenue',42,'manual','uncommitted-caller')")
    try:
        with pytest.raises(EconomicError, match='existing_transaction_not_owned'):
            book.ingest(encoded(), scope())
        assert book.store._conn.in_transaction
        assert book.store._conn.execute('SELECT COUNT(*) FROM ledger').fetchone()[0] == 1
    finally:
        book.store._conn.rollback()


def test_all_refund_notification_aliases_use_the_same_canonical_identity(book):
    book.ingest(encoded(), scope())
    for number, kind in enumerate(('refund.created', 'refund.updated', 'charge.refund.updated')):
        result = book.ingest(encoded(kind, refund(), f'evt_refund_alias_{number}'), scope())
        assert result['created_postings'] == (1 if number == 0 else 0)
    assert book.summary(scope())['refund_minor'] == 2000 and book.summary(scope())['posting_count'] == 2


def test_summary_uses_exact_python_ints_and_refuses_unsafe_json_aggregate_bound(book):
    from economic import MAX_MINOR

    for suffix in ('huge_first', 'huge_second'):
        book.ingest(encoded('charge.succeeded', charge(suffix, MAX_MINOR), 'evt_' + suffix), scope())
    with pytest.raises(EconomicError, match='summary_integer_bound_exceeded'):
        book.summary(scope())
    assert len(book.postings(scope())) == 2  # no rounding, deletion or balancing adjustment


def test_statement_fixture_drift_is_reported_and_does_not_mutate_postings(book):
    book.ingest(encoded(), scope())
    before = book.postings(scope())
    result = book.summary(scope(), expected_net_minor=9000)
    assert result['statement_fixture_drift_minor'] == 1000 and not result['statement_fixture_matches']
    assert book.postings(scope()) == before


def test_host_fixture_clock_is_explicit_aware_and_cannot_be_taken_from_payload(tmp_path):
    store = Store(str(tmp_path / 'clock.sqlite3'))
    book = EconomicBook(store, experimental=True, clock=lambda: '2000-01-01T00:00:00+00:00')
    book.ingest(encoded(), scope())
    assert store._conn.execute('SELECT received_at FROM economic_v1_messages').fetchone()[0] == '2000-01-01T00:00:00+00:00'
    book.clock = lambda: 'not-a-valid-aware-clock'
    with pytest.raises(EconomicError, match='invalid_host_clock'):
        book.ingest(encoded('charge.succeeded', charge('second'), 'evt_second'), scope())
    assert len(book.postings(scope())) == 1
    store._conn.close()
