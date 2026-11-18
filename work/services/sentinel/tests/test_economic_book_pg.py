"""OPT-IN ONLY: additive synthetic canonical book on a disposable PostgreSQL DSN.

Never reads DATABASE_URL/SENTINEL_DB, never resets/truncates/deletes records. Each
case uses a new synthetic provider-account namespace; test history is retained.
A skipped case is NOT PostgreSQL, restricted-role or process-crash evidence.
"""
from __future__ import annotations

import concurrent.futures
import os
import threading
import uuid

import pytest
from economic import EconomicConflict, EconomicUnavailable, Scope
from economic_fixtures import charge, encoded, refund, snapshot
from economic_repository import EconomicBook
from repository import Store

DSN = os.environ.get('OPENBOT_TEST_POSTGRES_DSN', '')
pytestmark = pytest.mark.skipif(
    os.environ.get('OPENBOT_TEST_POSTGRES_ALLOW_WRITES') != '1'
    or not DSN.startswith(('postgres://', 'postgresql://')),
    reason='dedicated disposable OPENBOT_TEST_POSTGRES_DSN and explicit write opt-in required; no production fallback',
)


@pytest.fixture()
def pg_book():
    host_scope = Scope('acct_synthetic_pg_' + uuid.uuid4().hex, 'media-api')
    store = Store(DSN)
    book = EconomicBook(store, experimental=True)
    try:
        yield book, host_scope
    finally:
        store._conn.close()  # retain all audit/posting/schema history


def _payload(host_scope, kind='invoice.paid', obj=None, identity=None):
    return encoded(kind, obj, identity, account=host_scope.account)


def test_pg_canonical_refunds_replay_and_legacy_compatibility(pg_book):
    book, host_scope = pg_book
    legacy_key = 'pg-legacy-' + uuid.uuid4().hex
    book.store.post_ledger({'venture': 'media-api', 'kind': 'revenue', 'amount_usd': 42,
                            'source': 'manual', 'idempotency_key': legacy_key})
    book.ingest(_payload(host_scope), host_scope)
    book.ingest(_payload(host_scope, 'charge.refunded', snapshot(), 'evt_pg_refund20'), host_scope)
    book.ingest(_payload(host_scope, 'charge.refunded', snapshot([refund(), refund('second', 3000)]), 'evt_pg_refund50'), host_scope)
    book.ingest(_payload(host_scope), host_scope)
    assert book.summary(host_scope)['net_captured_minor'] == 5000
    assert book.summary(host_scope)['posting_count'] == 3
    assert any(row['idempotency_key'] == legacy_key for row in book.store.ledger_rows())
    book.store._conn.rollback()  # end ONLY this test-owned legacy read transaction


def test_pg_conflicting_properties_are_not_successful_duplicates(pg_book):
    book, host_scope = pg_book
    book.ingest(_payload(host_scope), host_scope)
    with pytest.raises(EconomicConflict):
        book.ingest(_payload(host_scope, 'charge.succeeded', charge(amount=20000)), host_scope)
    assert book.summary(host_scope)['capture_minor'] == 10000
    assert len(book.messages(host_scope)) == 1


def test_pg_new_message_and_postings_roll_back_together_on_audit_failure(pg_book):
    book, host_scope = pg_book
    def fault(stage):
        if stage == 'after_postings':
            raise OSError('synthetic PG transaction failure')
    book.fault_hook = fault
    with pytest.raises(EconomicUnavailable) as error:
        book.ingest(_payload(host_scope), host_scope)
    assert not error.value.uncertain
    book.fault_hook = None
    assert book.messages(host_scope) == [] and book.postings(host_scope) == []
    assert book.ingest(_payload(host_scope), host_scope)['created_postings'] == 1


def test_pg_independent_connection_race_not_just_one_python_lock(pg_book):
    book, host_scope = pg_book
    payload = _payload(host_scope)
    barrier = threading.Barrier(4)
    def worker(_):
        other = Store(DSN)
        try:
            instance = EconomicBook(other, experimental=True)
            barrier.wait(timeout=15)
            return instance.ingest(payload, host_scope)
        finally:
            other._conn.close()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(worker, range(4)))
    assert sum(result['created_postings'] for result in results) == 1
    assert sum(result['message_created'] for result in results) == 1
    assert book.summary(host_scope)['capture_minor'] == 10000
    assert len(book.messages(host_scope)) == 1
