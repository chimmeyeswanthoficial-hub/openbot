"""Disposable PG 17 local-profile evidence, NOT production/HA/tenant certification.

Requires both original PG opt-ins and a Unix socket test DB named openbot_fixture*.
Creates new synthetic schemas/roles; no destructive cleanup, production fallback,
real data, payment providers, app server or public listener. Setup is ADMIN work;
all runtime probes use a distinct non-owner, non-superuser application role.
"""
from __future__ import annotations

import inspect
import json
import multiprocessing
import os
import subprocess
import uuid
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest
from economic import EconomicUnavailable, Scope
from economic_fixtures import encoded, refund, snapshot
from economic_repository import EconomicBook
from repository import Store

DSN = os.environ.get('OPENBOT_TEST_POSTGRES_DSN', '')
pytestmark = pytest.mark.skipif(
    os.environ.get('OPENBOT_TEST_POSTGRES_ALLOW_WRITES') != '1'
    or not DSN.startswith(('postgres://', 'postgresql://')),
    reason='explicit disposable PG DSN + test write opt-in required; no production fallback',
)


def runtime_store(dsn):
    # On the untouched AG4 base exercise its actual DDL behavior, not a TypeError
    # caused by a not-yet-added keyword. The regression is the denied DDL itself.
    if 'initialize' in inspect.signature(Store).parameters:
        return Store(dsn, initialize=False)
    return Store(dsn)


def runtime_book(store, **kwargs):
    if 'initialize' in inspect.signature(EconomicBook).parameters:
        return EconomicBook(store, experimental=True, initialize=False, **kwargs)
    return EconomicBook(store, experimental=True, **kwargs)


def scoped_dsn(base, role, schema, database=None):
    source = urlsplit(base)
    query = dict(parse_qsl(source.query))
    host = query.get('host', '')
    if not host.startswith('/') or not source.path.lstrip('/').startswith('openbot_fixture'):
        raise RuntimeError('PG profile tests require a private Unix-socket openbot_fixture database')
    query['options'] = '-csearch_path=' + schema
    return urlunsplit(('postgresql', role + '@', '/' + (database or source.path.lstrip('/')),
                       urlencode(query), ''))


def _grant_profile(connection, database, schema, role):
    from psycopg2 import sql
    statements = [
        sql.SQL('REVOKE CREATE,TEMPORARY ON DATABASE {} FROM PUBLIC').format(sql.Identifier(database)),
        sql.SQL('REVOKE ALL ON SCHEMA {} FROM PUBLIC').format(sql.Identifier(schema)),
        sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema), sql.Identifier(role)),
        sql.SQL('GRANT SELECT,INSERT ON {}.audit,{}.ledger,{}.economic_v1_postings,{}.economic_v1_links,{}.economic_v1_events TO {}').format(*([sql.Identifier(schema)] * 5), sql.Identifier(role)),
        sql.SQL('GRANT SELECT,INSERT,UPDATE ON {}.approvals,{}.runs,{}.economic_v1_messages TO {}').format(*([sql.Identifier(schema)] * 3), sql.Identifier(role)),
        sql.SQL('GRANT SELECT ON {}.economic_v1_schema TO {}').format(sql.Identifier(schema), sql.Identifier(role)),
        sql.SQL('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA {} TO {}').format(sql.Identifier(schema), sql.Identifier(role)),
        sql.SQL('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA {} FROM PUBLIC').format(sql.Identifier(schema)),
    ]
    with connection.cursor() as cur:
        for statement in statements:
            cur.execute(statement)


@pytest.fixture()
def profile():
    import psycopg2
    from psycopg2 import sql
    parsed = urlsplit(DSN)
    if not dict(parse_qsl(parsed.query)).get('host', '').startswith('/') or not parsed.path.lstrip('/').startswith('openbot_fixture'):
        pytest.fail('Refusing profile setup before mutation: private Unix-socket openbot_fixture DSN required')
    token = uuid.uuid4().hex[:16]
    schema, role = 'pc_' + token, 'app_' + token
    admin = psycopg2.connect(DSN)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute('SELECT current_database(),current_user')
        database, owner = cur.fetchone()
        if not database.startswith('openbot_fixture'):
            pytest.fail('Refusing non-fixture database')
        cur.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT').format(sql.Identifier(role)))
        cur.execute(sql.SQL('CREATE SCHEMA {} AUTHORIZATION {}').format(sql.Identifier(schema), sql.Identifier(owner)))
    admin_url = scoped_dsn(DSN, owner, schema)
    app_url = scoped_dsn(DSN, role, schema)
    migration = Store(admin_url)
    EconomicBook(migration, experimental=True)
    migration._conn.close()
    _grant_profile(admin, database, schema, role)
    try:
        yield {'schema': schema, 'role': role, 'owner': owner, 'admin': admin,
               'admin_url': admin_url, 'app_url': app_url, 'database': database,
               'scope': Scope('acct_profile_' + token, 'media-api'), 'base': parsed}
    finally:
        admin.close()  # retain synthetic rows/schema/grants; cluster itself is disposable


def test_pg_application_opens_existing_schema_without_ddl_authority(profile):
    store = runtime_store(profile['app_url'])
    try:
        seq = store.audit({'run_id': 'r_profile', 'decision': 'allow', 'rule': 'test.local'})
        assert seq > 0
        assert store.audit_tail(limit=1)[0]['run_id'] == 'r_profile'
        store._conn.rollback()  # end this test-owned legacy read transaction
        with store._conn.cursor() as cur:
            cur.execute('SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')
            assert cur.fetchone() == (False, False, False)
    finally:
        store._conn.close()


def test_pg_canonical_book_opens_and_posts_without_runtime_migration(profile):
    store = runtime_store(profile['app_url'])
    try:
        book = runtime_book(store)
        scope = profile['scope']
        assert book.ingest(encoded(account=scope.account), scope)['created_postings'] == 1
        assert book.summary(scope)['capture_minor'] == 10000
    finally:
        store._conn.close()


@pytest.mark.parametrize('statement', [
    'UPDATE audit SET rule=rule', 'DELETE FROM audit', 'TRUNCATE audit',
    'ALTER TABLE audit ADD COLUMN forged TEXT', 'DROP TABLE audit',
    'CREATE TABLE forged(id INTEGER)', 'CREATE TEMP TABLE forged(id INTEGER)',
    'CREATE FUNCTION forged() RETURNS integer LANGUAGE SQL AS $$ SELECT 1 $$',
    'ALTER TABLE economic_v1_postings DISABLE TRIGGER ALL',
    'UPDATE economic_v1_postings SET amount_minor=0',
    'DELETE FROM economic_v1_events', 'TRUNCATE economic_v1_messages',
])
def test_pg_runtime_role_cannot_rewrite_evidence_or_perform_ddl(profile, statement):
    import psycopg2
    conn = psycopg2.connect(profile['app_url'])
    try:
        with pytest.raises(psycopg2.errors.InsufficientPrivilege), conn.cursor() as cur:
            cur.execute(statement)
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute('SELECT current_user')
            assert cur.fetchone()[0] == profile['role']
    finally:
        conn.close()


def _race_worker(dsn, account, queue, barrier, approval_id=None):
    store = None
    try:
        store = runtime_store(dsn)
        book = None if approval_id else runtime_book(store)
        barrier.wait(timeout=20)
        if approval_id:
            result = store.resolve_approval(approval_id, 'approved', 'human:synthetic-reviewer')
        else:
            result = book.ingest(encoded(account=account), Scope(account, 'media-api'))
        queue.put(('ok', result))
    except BaseException as exc:
        queue.put(('error', type(exc).__name__))
        raise
    finally:
        if store is not None:
            store._conn.close()


def run_process_race(profile, count, approval_id=None):
    ctx = multiprocessing.get_context('spawn')
    barrier, queue = ctx.Barrier(count), ctx.Queue()
    workers = [ctx.Process(target=_race_worker,
        args=(profile['app_url'], profile['scope'].account, queue, barrier, approval_id))
        for _ in range(count)]
    try:
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=35)
            assert not worker.is_alive() and worker.exitcode == 0
        replies = [queue.get(timeout=5) for _ in workers]
        assert all(status == 'ok' for status, _ in replies), replies
        return [value for _, value in replies]
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=5)
        queue.close()
        queue.join_thread()


def test_pg_twelve_independent_processes_resolve_one_approval(profile):
    store = runtime_store(profile['app_url'])
    try:
        approval = store.create_approval({'id': 'ap_profile', 'run_id': 'r_profile',
            'venture': 'media-api', 'rule': 'test.profile'})
        store._conn.rollback()  # get_approval legacy read belongs to this test
        result = run_process_race(profile, 12, approval_id=approval['id'])
        assert result.count(True) == 1 and result.count(False) == 11
        assert store.get_approval(approval['id'])['status'] == 'approved'
    finally:
        store._conn.close()


def test_pg_four_independent_processes_claim_one_canonical_event(profile):
    result = run_process_race(profile, 4)
    assert sum(row['created_postings'] for row in result) == 1
    assert sum(row['message_created'] for row in result) == 1
    store = runtime_store(profile['app_url'])
    try:
        book = runtime_book(store)
        assert len(book.messages(profile['scope'])) == 1
        assert book.summary(profile['scope'])['posting_count'] == 1
    finally:
        store._conn.close()


def test_pg_missing_event_audit_permission_rolls_back_message_and_posting(profile):
    from psycopg2 import sql
    store = runtime_store(profile['app_url'])
    book = runtime_book(store)
    try:
        with profile['admin'].cursor() as cur:
            cur.execute(sql.SQL('REVOKE INSERT ON {}.economic_v1_events FROM {}').format(sql.Identifier(profile['schema']), sql.Identifier(profile['role'])))
        with pytest.raises(EconomicUnavailable) as error:
            book.ingest(encoded(account=profile['scope'].account), profile['scope'])
        assert not error.value.uncertain
        assert book.messages(profile['scope']) == []
        assert book.postings(profile['scope']) == []
    finally:
        store._conn.close()


@pytest.mark.parametrize('stage', ['before_commit', 'after_commit'])
def test_pg_real_backend_disconnect_keeps_uncertainty_and_same_id_retry(profile, stage):
    store = runtime_store(profile['app_url'])
    book = runtime_book(store)
    pid = store._conn.get_backend_pid()
    def disconnect(at):
        if at != stage:
            return
        with profile['admin'].cursor() as cur:
            cur.execute('SELECT usename,datname FROM pg_stat_activity WHERE pid=%s', (pid,))
            assert cur.fetchone() == (profile['role'], profile['database'])
            cur.execute('SELECT pg_terminate_backend(%s,1000)', (pid,))
            assert cur.fetchone()[0]
        if at == 'after_commit':
            with store._conn.cursor() as cur:
                cur.execute('SELECT 1')  # real broken connection, not a fabricated DB error
    book.fault_hook = disconnect
    with pytest.raises(EconomicUnavailable) as error:
        book.ingest(encoded(account=profile['scope'].account), profile['scope'])
    assert error.value.uncertain
    store._conn.close()
    recovered = runtime_store(profile['app_url'])
    try:
        other = runtime_book(recovered)
        assert other.summary(profile['scope'])['posting_count'] == (stage == 'after_commit')
        other.ingest(encoded(account=profile['scope'].account), profile['scope'])
        assert other.summary(profile['scope'])['posting_count'] == 1
    finally:
        recovered._conn.close()


def _death_worker(dsn, account, stage):
    store = runtime_store(dsn)
    def die(at):
        if at == stage:
            os._exit(79)
    book = runtime_book(store, fault_hook=die)
    book.ingest(encoded(account=account), Scope(account, 'media-api'))
    raise RuntimeError('fault hook not reached')


@pytest.mark.parametrize('stage', ['before_message', 'after_message', 'after_postings', 'before_commit', 'after_commit'])
def test_pg_abrupt_client_process_death_and_retry(profile, stage):
    worker = multiprocessing.get_context('spawn').Process(target=_death_worker,
        args=(profile['app_url'], profile['scope'].account, stage))
    worker.start()
    try:
        worker.join(timeout=25)
        assert not worker.is_alive() and worker.exitcode == 79
        recovered = runtime_store(profile['app_url'])
        try:
            book = runtime_book(recovered)
            assert book.summary(profile['scope'])['posting_count'] == (stage == 'after_commit')
            book.ingest(encoded(account=profile['scope'].account), profile['scope'])
            assert book.summary(profile['scope'])['posting_count'] == 1
            assert len(book.messages(profile['scope'])) == 1
        finally:
            recovered._conn.close()
    finally:
        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=5)


def test_pg_dump_actually_restores_rows_constraints_and_app_grants(profile, tmp_path):
    from psycopg2 import sql
    tools = Path(os.environ['OPENBOT_PG_TEST_BIN'])
    store = runtime_store(profile['app_url'])
    scope = profile['scope']
    try:
        book = runtime_book(store)
        book.ingest(encoded(account=scope.account), scope)
        book.ingest(encoded('charge.refunded', snapshot([refund(), refund('second', 3000)]), 'evt_restore', account=scope.account), scope)
        expected = book.summary(scope)
        store.audit({'run_id': 'r_restore', 'decision': 'allow', 'rule': 'test.restore'})
    finally:
        store._conn.close()
    dump = tmp_path / 'profile.dump'
    command = [str(tools/'pg_dump'), '-Fc', '--no-owner', '--schema='+profile['schema'], '--file='+str(dump), '--dbname='+profile['admin_url']]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)
    restored_db = 'openbot_fixture_restore_' + uuid.uuid4().hex[:12]
    with profile['admin'].cursor() as cur:
        cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(restored_db)))
        cur.execute(sql.SQL('REVOKE CREATE,TEMPORARY ON DATABASE {} FROM PUBLIC').format(sql.Identifier(restored_db)))
    destination = scoped_dsn(DSN, profile['owner'], profile['schema'], restored_db)
    subprocess.run([str(tools/'pg_restore'), '--exit-on-error', '--no-owner', '--dbname='+destination, str(dump)], check=True, capture_output=True, text=True, timeout=30)
    restored = runtime_store(scoped_dsn(DSN, profile['role'], profile['schema'], restored_db))
    try:
        actual = runtime_book(restored).summary(scope)
        assert actual == expected
        assert actual['capture_minor'] == 10000 and actual['refund_minor'] == 5000
        assert restored.audit_tail(limit=1)[0]['run_id'] == 'r_restore'
        restored._conn.rollback()
        import psycopg2
        with pytest.raises(psycopg2.errors.InsufficientPrivilege), restored._conn.cursor() as cur:
            cur.execute('DELETE FROM audit')
        restored._conn.rollback()
    finally:
        restored._conn.close()
    evidence = os.environ.get('OPENBOT_PG_TEST_EVIDENCE')
    if evidence:
        output = Path(evidence)
        output.mkdir(parents=True, exist_ok=True)
        (output/'restore-profile.dump').write_bytes(dump.read_bytes())
        (output/'restore-readback.json').write_text(json.dumps({'schema': profile['schema'], 'role': profile['role'], 'source_database': profile['database'], 'restored_database': restored_db, 'scope_account': scope.account, 'expected': expected, 'actual': actual, 'audit_readback': 'r_restore', 'app_delete_denied': True, 'actual_pg_restore_executed': True}, indent=2)+'\n')


def test_pg_default_initialization_does_not_silently_bypass_missing_authority(profile):
    import psycopg2
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        Store(profile['app_url'])  # only initialize=False is the explicit runtime path
    store = runtime_store(profile['app_url'])
    try:
        with pytest.raises(EconomicUnavailable) as error:
            EconomicBook(store, experimental=True)
        assert not error.value.uncertain
        assert store._conn.get_transaction_status() == 0
        assert runtime_book(store).summary(profile['scope'])['posting_count'] == 0
    finally:
        store._conn.close()


@pytest.mark.parametrize('column,value', [
    ('venture', 'other-venture'), ('account', 'acct_other'),
    ('event_id', 'evt_other'), ('payload_sha256', '0' * 64),
    ('candidates', '[]'), ('received_at', '2000-01-01T00:00:00+00:00'),
])
def test_pg_trigger_protects_message_identity_despite_status_update_privilege(profile, column, value):
    import psycopg2
    from psycopg2 import sql
    store = runtime_store(profile['app_url'])
    try:
        book = runtime_book(store)
        book.ingest(encoded(account=profile['scope'].account), profile['scope'])
        before = book.messages(profile['scope'])
        with pytest.raises(psycopg2.errors.RaiseException), store._conn.cursor() as cur:
            cur.execute(sql.SQL('UPDATE economic_v1_messages SET {}=%s').format(sql.Identifier(column)), (value,))
        store._conn.rollback()
        assert book.messages(profile['scope']) == before
        assert book.summary(profile['scope'])['posting_count'] == 1
    finally:
        store._conn.close()


def test_pg_readonly_constructor_checks_version_without_repair(profile):
    from economic import EconomicError
    from psycopg2 import sql
    with profile['admin'].cursor() as cur:
        cur.execute(sql.SQL('UPDATE {}.economic_v1_schema SET version=2').format(sql.Identifier(profile['schema'])))
    store = runtime_store(profile['app_url'])
    try:
        with pytest.raises(EconomicError, match='unsupported_economic_schema'):
            runtime_book(store)
        assert store._conn.get_transaction_status() == 0
        with store._conn.cursor() as cur:
            cur.execute('SELECT version FROM economic_v1_schema')
            assert cur.fetchone()[0] == 2
    finally:
        store._conn.close()


def test_pg_failed_fresh_economic_migration_is_atomic(profile, monkeypatch):
    import economic_repository
    from psycopg2 import sql
    schema = 'failed_' + uuid.uuid4().hex[:16]
    with profile['admin'].cursor() as cur:
        cur.execute(sql.SQL('CREATE SCHEMA {} AUTHORIZATION {}').format(sql.Identifier(schema), sql.Identifier(profile['owner'])))
    store = Store(scoped_dsn(DSN, profile['owner'], schema))
    try:
        monkeypatch.setattr(economic_repository, '_PG_GUARDS', economic_repository._PG_GUARDS + '\nSELECT 1/0;')
        with pytest.raises(EconomicUnavailable) as error:
            EconomicBook(store, experimental=True)
        assert not error.value.uncertain
        assert store._conn.get_transaction_status() == 0
        with store._conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM pg_tables WHERE schemaname=%s AND tablename LIKE 'economic_v1_%%'", (schema,))
            assert cur.fetchone()[0] == 0
            cur.execute('SELECT count(*) FROM audit')
            assert cur.fetchone()[0] == 0
    finally:
        store._conn.close()
