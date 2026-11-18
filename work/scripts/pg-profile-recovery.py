#!/usr/bin/env python3
"""Prepare/read back a synthetic local PG restart probe. Never starts/stops a DB.

Requires the two explicit fixture opt-ins and an actual successful restore receipt.
Only a private Unix-socket openbot_fixture_restore_* DB is accepted. No provider,
production fallback, credentials, schema DDL or automatic retry under a new ID.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'services/sentinel'), str(ROOT/'services/ledger/src')]
from economic import Scope  # noqa: E402
from economic_fixtures import encoded  # noqa: E402
from economic_repository import EconomicBook  # noqa: E402
from repository import Store  # noqa: E402

TABLES = ('audit', 'approvals', 'ledger', 'runs', 'economic_v1_schema', 'economic_v1_messages',
          'economic_v1_postings', 'economic_v1_links', 'economic_v1_events')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def state(store):
    data = {}
    with store._conn.cursor() as cur:
        for table in TABLES:  # fixed program constants, never caller-supplied SQL identifiers
            cur.execute('SELECT * FROM ' + table)
            columns = [c[0] for c in cur.description]
            rows = [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]
            data[table] = sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))
    store._conn.rollback()  # only the read transaction owned by this standalone probe
    return {'rows_sha256': digest(data), 'table_counts': {k: len(v) for k, v in data.items()}}


def settings(store):
    with store._conn.cursor() as cur:
        out = {}
        for name in ('server_version', 'listen_addresses', 'fsync', 'synchronous_commit', 'full_page_writes'):
            cur.execute('SHOW ' + name)
            out[name] = cur.fetchone()[0]
        cur.execute('SELECT current_user,rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user')
        out['app_identity'] = list(cur.fetchone())
    store._conn.rollback()
    assert out['listen_addresses'] == ''
    assert all(out[name] == 'on' for name in ('fsync', 'synchronous_commit', 'full_page_writes'))
    assert out['app_identity'][1:] == [False, False, False]
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'verify'))
    parser.add_argument('--restore-receipt', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--before', type=Path)
    args = parser.parse_args()
    if os.environ.get('OPENBOT_TEST_POSTGRES_ALLOW_WRITES') != '1':
        raise ValueError('explicit fixture write opt-in required')
    url = urlsplit(os.environ.get('OPENBOT_TEST_POSTGRES_DSN', ''))
    if url.scheme not in ('postgres', 'postgresql') or not url.path.lstrip('/').startswith('openbot_fixture'):
        raise ValueError('explicit fixture PG URL required; no production fallback')
    query = dict(parse_qsl(url.query))
    socket = query.get('host', '')
    if not socket.startswith('/') or (Path(socket).stat().st_mode & 0o777) != 0o700:
        raise ValueError('private Unix socket directory required')
    fixture = json.loads(args.restore_receipt.read_text())
    if not fixture.get('actual_pg_restore_executed') or not fixture.get('app_delete_denied'):
        raise ValueError('completed real restore receipt required')
    for key, expression in [('schema', r'pc_[0-9a-f]{16}'), ('role', r'app_[0-9a-f]{16}'),
                            ('restored_database', r'openbot_fixture_restore_[0-9a-f]{12}'),
                            ('scope_account', r'acct_profile_[0-9a-f]{16}')]:
        if not re.fullmatch(expression, fixture[key]):
            raise ValueError('unexpected synthetic fixture identity')
    query['options'] = '-csearch_path=' + fixture['schema']
    dsn = urlunsplit(('postgresql', fixture['role']+'@', '/'+fixture['restored_database'], urlencode(query), ''))
    store = Store(dsn, initialize=False)
    try:
        book = EconomicBook(store, experimental=True, initialize=False)
        scope = Scope(fixture['scope_account'], 'media-api')
        if args.phase == 'prepare':
            assert book.summary(scope) == fixture['actual']
            # Commit fresh evidence immediately before the independent immediate-stop.
            # No CHECKPOINT/pg_switch_wal call masks the actual recovery requirement.
            store.audit({'run_id': 'r_server_crash_guard', 'decision': 'allow',
                         'rule': 'test.synthetic_pg_recovery', 'venture': 'media-api'})
            report = {'phase': 'before_immediate_stop', 'fixture_database': fixture['restored_database'],
                      'fixture_schema': fixture['schema'], 'settings': settings(store),
                      'committed_state': state(store), 'summary': book.summary(scope)}
        else:
            if args.before is None:
                raise ValueError('--before is required for verification')
            before = json.loads(args.before.read_text())
            assert before['fixture_database'] == fixture['restored_database']
            assert before['fixture_schema'] == fixture['schema']
            observed = state(store)
            assert observed == before['committed_state']
            assert book.summary(scope) == before['summary']
            replay = book.ingest(encoded(account=scope.account), scope)
            assert not replay['message_created'] and replay['created_postings'] == 0
            assert state(store) == observed
            report = {'phase': 'after_actual_server_restart', 'fixture_database': fixture['restored_database'],
                      'fixture_schema': fixture['schema'], 'settings': settings(store),
                      'committed_state': observed, 'summary': book.summary(scope),
                      'same_message_replay': replay, 'all_rows_and_counts_match': True,
                      'scope': 'same-host disposable PG; not HA/network/provider certification'}
    finally:
        store._conn.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
