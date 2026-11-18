#!/usr/bin/env python3
"""Execute bounded offline economic read-back/race/crash evidence on NEW SQLite files.

No DB/provider/env setter, lookup, real payment, server, reset, deletion or network.
Fixture record clocks are deterministic and separately labelled from runner time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import sqlite3
import sys
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'services/sentinel'), str(ROOT / 'services/ledger/src')]

from economic import EconomicConflict, EconomicError  # noqa: E402
from economic_fixtures import charge, checkout, encoded, intent, invoice, refund, scope, snapshot  # noqa: E402
from economic_repository import EconomicBook  # noqa: E402
from repository import Store  # noqa: E402

FIXTURE_TIME = '2000-01-01T00:00:00+00:00'
SALE = {'invoice.paid': invoice, 'payment_intent.succeeded': intent,
        'checkout.session.completed': checkout, 'charge.succeeded': charge, 'charge.captured': charge}
STAGES = ('before_message', 'after_message', 'after_postings', 'before_commit', 'after_commit')


def fixture_clock():
    return FIXTURE_TIME


def open_book(path, *, fault=None):
    store = Store(str(path))
    os.chmod(path, 0o600)
    return EconomicBook(store, experimental=True, clock=fixture_clock, fault_hook=fault)


def read_back(book):
    transitions = [dict(row) for row in book.store._conn.execute(
        'SELECT seq,account,event_id,status,reason,recorded_at FROM economic_v1_events ORDER BY seq')]
    links = [dict(row) for row in book.store._conn.execute(
        'SELECT event_id,kind,economic_id FROM economic_v1_links ORDER BY event_id,kind,economic_id')]
    assert book.store._conn.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
    return {'summary': book.summary(scope()), 'messages': book.messages(scope()),
            'postings': book.postings(scope()), 'transitions': transitions, 'links': links,
            'sqlite_quick_check': 'ok'}


def race_worker(path, payload, participant, barrier, queue):
    book = None
    try:
        book = open_book(path)
        barrier.wait(timeout=15)
        try:
            result = book.ingest(payload, scope())
        except EconomicConflict as exc:
            result = {'status': 'conflict', 'code': exc.code}
        queue.put({'participant': participant, 'pid': os.getpid(), **result})
    except BaseException as exc:
        queue.put({'participant': participant, 'worker_error': type(exc).__name__})
        raise
    finally:
        if book is not None:
            book.store._conn.close()


def run_race(path, case):
    book = open_book(path)
    if case == 'refund_duplicates':
        book.ingest(encoded(), scope())
    book.store._conn.close()
    payloads = []
    for number in range(4):
        if case == 'same_message':
            payloads.append(encoded())
        elif case == 'linked_notifications':
            kind = list(SALE)[number]
            payloads.append(encoded(kind, SALE[kind](), 'evt_race_' + str(number)))
        elif case == 'refund_duplicates':
            payloads.append(encoded('refund.created', refund(), 'evt_race_' + str(number)))
        else:
            payloads.append(encoded('charge.succeeded', charge(amount=10000 if number < 2 else 20000), 'evt_race_' + str(number)))
    context = multiprocessing.get_context('spawn')
    barrier, queue = context.Barrier(4), context.Queue()
    processes = [context.Process(target=race_worker, args=(str(path), payload, number, barrier, queue))
                 for number, payload in enumerate(payloads)]
    try:
        for process in processes:
            process.start()
        outcomes = [queue.get(timeout=20) for _ in processes]
        for process in processes:
            process.join(20)
            assert process.exitcode == 0
        assert all('worker_error' not in result for result in outcomes)
    finally:
        for process in processes:
            if process.is_alive():
                process.kill()
            process.join(5)
        queue.close()
    book = open_book(path)
    state = read_back(book)
    book.store._conn.close()
    if case == 'refund_duplicates':
        assert state['summary']['posting_count'] == 2 and state['summary']['refund_minor'] == 2000
    else:
        assert state['summary']['posting_count'] == 1
        assert state['summary']['capture_minor'] in ({10000, 20000} if case == 'conflicting_amounts' else {10000})
    if case == 'conflicting_amounts':
        assert sum(result['status'] == 'conflict' for result in outcomes) == 2
        assert len(state['messages']) == 2
    else:
        assert sum(result['created_postings'] for result in outcomes) == 1
    return {'case': case, 'workers': sorted(outcomes, key=lambda result: result['participant']),
            'worker_exit_codes': [process.exitcode for process in processes], 'read_back': state}


def crash_worker(path, target):
    def fault(stage):
        if target == stage:
            os._exit(79)  # deliberately bypass Python cleanup/transaction context
    book = open_book(path, fault=fault)
    book.ingest(encoded(), scope())
    raise AssertionError('crash point was not reached')


def run_crash(path, stage):
    context = multiprocessing.get_context('spawn')
    process = context.Process(target=crash_worker, args=(str(path), stage))
    process.start()
    try:
        process.join(20)
        assert process.exitcode == 79
    finally:
        if process.is_alive():
            process.kill()
            process.join(5)
    book = open_book(path)
    before_retry = read_back(book)
    expected = 1 if stage == 'after_commit' else 0
    assert before_retry['summary']['posting_count'] == expected
    replay = book.ingest(encoded(), scope())
    after_retry = read_back(book)
    assert replay['created_postings'] == 1 - expected
    assert after_retry['summary']['capture_minor'] == 10000 and after_retry['summary']['posting_count'] == 1
    book.store._conn.close()
    return {'stage': stage, 'actual_abrupt_child_exit': process.exitcode, 'pid': process.pid,
            'before_same_id_retry': before_retry, 'same_id_retry': replay, 'after_same_id_retry': after_retry}


def run():
    (ROOT / '.cache').mkdir(exist_ok=True)
    state_dir = Path(tempfile.mkdtemp(prefix='economic-demo-', dir=ROOT / '.cache'))
    report = {'mode': 'SYNTHETIC_OFFLINE_ONLY', 'fixture_record_clock_not_measurement': FIXTURE_TIME,
              'host_scope': asdict(scope()), 'generated_disposable_state': state_dir.relative_to(ROOT).as_posix()}
    path = state_dir / 'linked-and-refunds.sqlite3'
    book = open_book(path)
    linked_results = []
    for number, (kind, factory) in enumerate(SALE.items()):
        linked_results.append(book.ingest(encoded(kind, factory(), f'evt_linked_{number}'), scope()))
    report['linked_sale'] = {'outcomes': linked_results, 'read_back': read_back(book)}
    assert report['linked_sale']['read_back']['summary']['capture_minor'] == 10000
    assert report['linked_sale']['read_back']['summary']['posting_count'] == 1
    report['refund_results'] = [
        book.ingest(encoded('charge.refunded', snapshot(), 'evt_snapshot20'), scope()),
        book.ingest(encoded('charge.refunded', snapshot([refund(), refund('second', 3000)]), 'evt_snapshot50'), scope()),
        book.ingest(encoded('refund.created', refund(), 'evt_refund_duplicate'), scope()),
    ]
    report['refunds_read_back'] = read_back(book)
    assert report['refunds_read_back']['summary']['refund_minor'] == 5000
    assert report['refunds_read_back']['summary']['net_captured_minor'] == 5000
    report['reconciliation_match'] = book.summary(scope(), expected_net_minor=5000)
    report['unexplained_drift_reported_not_adjusted'] = book.summary(scope(), expected_net_minor=4000)
    assert report['unexplained_drift_reported_not_adjusted']['statement_fixture_drift_minor'] == 1000
    obj = charge()
    obj['amount_refunded'] = 5000
    report['cumulative_only_outcome'] = book.ingest(encoded('charge.refunded', obj, 'evt_incomplete_snapshot'), scope())
    assert report['cumulative_only_outcome']['status'] == 'unresolved'
    report['unresolved_read_back'] = read_back(book)
    assert report['unresolved_read_back']['summary']['refund_minor'] == 5000
    book.store._conn.close()

    path = state_dir / 'out-of-order.sqlite3'
    book = open_book(path)
    book.ingest(encoded('refund.created', refund()), scope())
    before = read_back(book)
    assert before['summary']['awaiting_capture_messages'] == 1 and before['postings'] == []
    book.store._conn.close()
    book = open_book(path)
    arrival = book.ingest(encoded(), scope())
    after = read_back(book)
    assert after['summary']['refund_minor'] == 2000 and after['summary']['awaiting_capture_messages'] == 0
    report['out_of_order_restart'] = {'before_restart': before, 'capture_arrival': arrival, 'after_restart': after}
    book.store._conn.close()

    path = state_dir / 'legacy-additive.sqlite3'
    legacy = Store(str(path))
    legacy.post_ledger({'ts': FIXTURE_TIME, 'venture': 'media-api', 'kind': 'revenue', 'amount_usd': 42,
                        'source': 'manual', 'idempotency_key': 'synthetic-unverified-legacy-row'})
    before = legacy.ledger_rows()
    assert not legacy._conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'economic_v1_%'").fetchall()
    try:
        EconomicBook(legacy)
    except EconomicError as exc:
        disabled = exc.code
    else:
        raise AssertionError('no implicit schema migration is allowed')
    with sqlite3.connect(state_dir / 'legacy-before-migration.sqlite3') as backup:
        legacy._conn.backup(backup)
    book = EconomicBook(legacy, experimental=True, clock=fixture_clock)
    book.ingest(encoded(), scope())
    after = legacy.ledger_rows()
    assert before == after
    report['additive_legacy_migration'] = {'default_constructor_refusal': disabled, 'legacy_before': before,
                                           'legacy_after': after, 'canonical': read_back(book),
                                           'rollback_means_opening_preserved_fixture_copy_not_deleting_history': True}
    assert report['additive_legacy_migration']['canonical']['summary']['capture_minor'] == 10000
    book.store._conn.close()
    rollback = Store(str(state_dir / 'legacy-before-migration.sqlite3'))
    assert rollback.ledger_rows() == before
    assert not rollback._conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'economic_v1_%'").fetchall()
    rollback._conn.close()

    report['independent_process_races'] = [run_race(state_dir / f'race-{case}.sqlite3', case)
                                         for case in ('same_message', 'linked_notifications', 'refund_duplicates', 'conflicting_amounts')]
    report['actual_process_deaths'] = [run_crash(state_dir / f'crash-{stage}.sqlite3', stage) for stage in STAGES]
    report['fixture_databases'] = [
        {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
         'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in sorted(state_dir.glob('*.sqlite3'))
    ]
    report.update(passed=True, runner_reported_utc=datetime.now(UTC).isoformat(),
                  bank_settlement_verified=False, providers_enabled=False, production_ready=False,
                  external_money_or_customer_code=False, production_migration=False,
                  limits=['Trusted synthetic processes only; not hostile-code isolation or authentication proof',
                          'No live provider, fees/disputes/payouts/FX or real revenue recognition',
                          'SQLite observed here; PostgreSQL requires separate disposable opt-in execution',
                          'Exact integer USD fixture book excludes unverified legacy REAL rows'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='NEW JSON evidence path')
    args = parser.parse_args()
    output = args.output.absolute()
    if output.exists() or output.is_symlink() or any(path.is_symlink() for path in output.parents):
        raise ValueError('new regular evidence path required; nothing is overwritten')
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        result = run()
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'passed': result['passed'], 'output': str(output),
                      'generated_disposable_state': result['generated_disposable_state'],
                      'actual_race_scenarios': len(result['independent_process_races']),
                      'actual_process_deaths': len(result['actual_process_deaths']),
                      'bank_settlement_verified': False, 'production_ready': False}, indent=2))


if __name__ == '__main__':
    main()
