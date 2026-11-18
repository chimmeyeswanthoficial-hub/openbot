"""Explicit synthetic-only canonical book beside (never replacing) the legacy ledger.

Use only with an explicitly supplied disposable Store and experimental=True. No
normal Store construction migrates this schema. Identity/uniqueness is DB-backed;
new messages, immutable economic postings and transition evidence commit together.
PostgreSQL SQL is provided, but live PG proof requires the dedicated opt-in suite.
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from contextlib import contextmanager, suppress
from dataclasses import replace
from datetime import UTC, datetime

from economic import (
    MAX_MINOR,
    EconomicConflict,
    EconomicError,
    EconomicUnavailable,
    Posting,
    Scope,
    identifier,
    minor,
    prepare_event,
)

_TABLES = f"""
CREATE TABLE IF NOT EXISTS economic_v1_schema (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL);
INSERT INTO economic_v1_schema(id,version) VALUES(1,1) ON CONFLICT(id) DO NOTHING;
CREATE TABLE IF NOT EXISTS economic_v1_messages (
 provider TEXT NOT NULL CHECK(provider='stripe'), account TEXT NOT NULL,
 environment TEXT NOT NULL CHECK(environment='test'), event_id TEXT NOT NULL,
 venture TEXT NOT NULL, event_type TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
 candidates TEXT NOT NULL, dependency_id TEXT NOT NULL, status TEXT NOT NULL,
 reason TEXT NOT NULL, received_at TEXT NOT NULL,
 PRIMARY KEY(provider,account,environment,event_id)
);
CREATE INDEX IF NOT EXISTS economic_v1_waiting ON economic_v1_messages(account,environment,status,dependency_id);
CREATE TABLE IF NOT EXISTS economic_v1_postings (
 provider TEXT NOT NULL CHECK(provider='stripe'), account TEXT NOT NULL,
 environment TEXT NOT NULL CHECK(environment='test'), kind TEXT NOT NULL CHECK(kind IN ('capture','refund')),
 economic_id TEXT NOT NULL, venture TEXT NOT NULL,
 amount_minor BIGINT NOT NULL CHECK(amount_minor>=0 AND amount_minor<={MAX_MINOR}) {{INTEGER_CHECK}},
 currency TEXT NOT NULL CHECK(currency='usd'), parent_id TEXT NOT NULL,
 payment_intent_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
 first_event_id TEXT NOT NULL, recorded_at TEXT NOT NULL,
 PRIMARY KEY(provider,account,environment,kind,economic_id),
 FOREIGN KEY(provider,account,environment,first_event_id)
 REFERENCES economic_v1_messages(provider,account,environment,event_id)
);
CREATE INDEX IF NOT EXISTS economic_v1_parent ON economic_v1_postings(account,environment,parent_id,kind);
CREATE UNIQUE INDEX IF NOT EXISTS economic_v1_capture_intent ON economic_v1_postings(provider,account,environment,payment_intent_id) WHERE kind='capture';
CREATE TABLE IF NOT EXISTS economic_v1_links (
 provider TEXT NOT NULL, account TEXT NOT NULL, environment TEXT NOT NULL,
 event_id TEXT NOT NULL, kind TEXT NOT NULL, economic_id TEXT NOT NULL,
 PRIMARY KEY(provider,account,environment,event_id,kind,economic_id),
 FOREIGN KEY(provider,account,environment,event_id) REFERENCES economic_v1_messages(provider,account,environment,event_id),
 FOREIGN KEY(provider,account,environment,kind,economic_id) REFERENCES economic_v1_postings(provider,account,environment,kind,economic_id)
);
CREATE TABLE IF NOT EXISTS economic_v1_events (
 seq {{SEQUENCE}}, account TEXT NOT NULL, event_id TEXT NOT NULL,
 status TEXT NOT NULL, reason TEXT NOT NULL, recorded_at TEXT NOT NULL
);
"""

_IMMUTABLE_TABLES = ('economic_v1_postings', 'economic_v1_links', 'economic_v1_events')
_SQLITE_GUARDS = '\n'.join(
    f"CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()} BEFORE {action} ON {table} "
    "BEGIN SELECT RAISE(ABORT,'economic evidence is append-only'); END;"
    for table in _IMMUTABLE_TABLES for action in ('UPDATE', 'DELETE')
) + """
CREATE TRIGGER IF NOT EXISTS economic_v1_messages_no_delete BEFORE DELETE ON economic_v1_messages
 BEGIN SELECT RAISE(ABORT,'economic message evidence is retained'); END;
CREATE TRIGGER IF NOT EXISTS economic_v1_messages_identity BEFORE UPDATE ON economic_v1_messages
 WHEN NEW.provider!=OLD.provider OR NEW.account!=OLD.account OR NEW.environment!=OLD.environment
 OR NEW.event_id!=OLD.event_id OR NEW.venture!=OLD.venture OR NEW.event_type!=OLD.event_type
 OR NEW.payload_sha256!=OLD.payload_sha256 OR NEW.candidates!=OLD.candidates
 OR NEW.dependency_id!=OLD.dependency_id OR NEW.received_at!=OLD.received_at
 BEGIN SELECT RAISE(ABORT,'economic message identity is immutable'); END;
"""
_PG_GUARDS = """
CREATE OR REPLACE FUNCTION economic_v1_no_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
 BEGIN RAISE EXCEPTION 'economic evidence is append-only'; END; $$;
""" + '\n'.join(
    f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='{table}_immutable' AND tgrelid='{table}'::regclass) THEN "
    f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
    "FOR EACH ROW EXECUTE FUNCTION economic_v1_no_mutation(); END IF; END; $$;"
    for table in _IMMUTABLE_TABLES
)


_PG_GUARDS += """
CREATE OR REPLACE FUNCTION economic_v1_message_guard() RETURNS trigger LANGUAGE plpgsql AS $$
 BEGIN
  IF TG_OP='DELETE' THEN RAISE EXCEPTION 'economic message evidence is retained'; END IF;
  IF ROW(NEW.provider,NEW.account,NEW.environment,NEW.event_id,NEW.venture,NEW.event_type,
         NEW.payload_sha256,NEW.candidates,NEW.dependency_id,NEW.received_at)
     IS DISTINCT FROM
     ROW(OLD.provider,OLD.account,OLD.environment,OLD.event_id,OLD.venture,OLD.event_type,
         OLD.payload_sha256,OLD.candidates,OLD.dependency_id,OLD.received_at)
  THEN RAISE EXCEPTION 'economic message identity is immutable'; END IF;
  RETURN NEW;
 END; $$;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='economic_v1_messages_guard' AND tgrelid='economic_v1_messages'::regclass) THEN
  CREATE TRIGGER economic_v1_messages_guard BEFORE UPDATE OR DELETE ON economic_v1_messages
  FOR EACH ROW EXECUTE FUNCTION economic_v1_message_guard();
 END IF;
END; $$;
"""


def _now():
    return datetime.now(UTC).isoformat()


class EconomicBook:
    def __init__(self, store, *, experimental=False, reconcile_limit=100, fault_hook=None, clock=None,
                 initialize=True):
        if experimental is not True:
            raise EconomicError('explicit_disposable_experiment_required')
        if type(initialize) is not bool:
            raise EconomicError('initialize_must_be_boolean')
        if type(reconcile_limit) is not int or not 1 <= reconcile_limit <= 1000:
            raise EconomicError('invalid_reconcile_limit')
        if clock is not None and not callable(clock):
            raise EconomicError('invalid_host_clock')
        self.clock = _now if clock is None else clock
        self.store, self.reconcile_limit, self.fault_hook = store, reconcile_limit, fault_hook
        self.pg = store._is_pg
        self.db_errors = (sqlite3.Error, OSError)
        if self.pg:
            import psycopg2
            self.db_errors += (psycopg2.Error,)
        with store._lock:
            self._ensure_idle()  # never commit/rollback a transaction owned by the caller
            cursor = None
            commit_started = False
            try:
                if self.pg:
                    cursor = store._conn.cursor()
                    cursor.execute("SET LOCAL lock_timeout='5000ms'; SET LOCAL statement_timeout='10000ms'")
                    if initialize:
                        # Only the explicit schema-owner path runs migration DDL.
                        cursor.execute('SELECT pg_advisory_xact_lock(5711232095842487857)')
                        cursor.execute(_TABLES.replace('{SEQUENCE}', 'BIGSERIAL PRIMARY KEY').replace('{INTEGER_CHECK}', '') + _PG_GUARDS)
                else:
                    store._conn.execute('PRAGMA foreign_keys=ON')
                    store._conn.execute('PRAGMA recursive_triggers=ON')
                    if store._conn.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
                        raise EconomicError('foreign_keys_required')
                    if initialize:
                        store._conn.executescript('BEGIN IMMEDIATE;\n' +
                            _TABLES.replace('{SEQUENCE}', 'INTEGER PRIMARY KEY AUTOINCREMENT').replace('{INTEGER_CHECK}', "CHECK(typeof(amount_minor)='integer')") + _SQLITE_GUARDS)
                    cursor = store._conn.cursor()
                cursor.execute('SELECT version FROM economic_v1_schema WHERE id=1')
                version = cursor.fetchone()
                if version is None or version[0] != 1:
                    raise EconomicError('unsupported_economic_schema')
                commit_started = True
                store._conn.commit()
            except BaseException as exc:
                with suppress(*self.db_errors):
                    store._conn.rollback()
                if isinstance(exc, self.db_errors):
                    raise EconomicUnavailable(uncertain=commit_started) from exc
                raise
            finally:
                if cursor is not None:
                    with suppress(*self.db_errors):
                        cursor.close()

    def _ensure_idle(self):
        try:
            if self.pg and self.store._conn.closed:
                raise EconomicUnavailable()
            busy = self.store._conn.get_transaction_status() != 0 if self.pg else self.store._conn.in_transaction
        except self.db_errors as exc:
            raise EconomicUnavailable() from exc
        if busy:
            raise EconomicError('existing_transaction_not_owned')

    def _stamp(self):
        value = self.clock()
        try:
            parsed = datetime.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise EconomicError('invalid_host_clock') from exc
        if parsed.tzinfo is None:
            raise EconomicError('invalid_host_clock')
        return value

    def _fault(self, stage):
        if self.fault_hook is not None:
            self.fault_hook(stage)

    def _execute(self, cursor, sql, values=()):
        cursor.execute(sql.replace('?', '%s') if self.pg else sql, values)
        return cursor

    @staticmethod
    def _one(cursor):
        row = cursor.fetchone()
        return dict(zip((c[0] for c in cursor.description), row, strict=True)) if row is not None else None

    @staticmethod
    def _all(cursor):
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    @contextmanager
    def _transaction(self, *, faults=False, read_only=False):
        with self.store._lock:
            self._ensure_idle()
            cursor = None
            commit_started = False
            try:
                cursor = self.store._conn.cursor()
                if not self.pg:
                    cursor.execute('BEGIN' if read_only else 'BEGIN IMMEDIATE')
                else:
                    if read_only:
                        cursor.execute('SET TRANSACTION READ ONLY')
                    cursor.execute("SET LOCAL lock_timeout='5000ms'; SET LOCAL statement_timeout='10000ms'")
                    if not read_only:
                        # Serialize writers; SELECT-only control readers need no write grants.
                        cursor.execute('LOCK TABLE economic_v1_messages IN SHARE ROW EXCLUSIVE MODE')
                yield cursor
                if faults:
                    self._fault('before_commit')
                commit_started = True
                self.store._conn.commit()
            except BaseException as exc:
                with suppress(*self.db_errors):
                    self.store._conn.rollback()
                if isinstance(exc, self.db_errors):
                    raise EconomicUnavailable(uncertain=commit_started) from exc
                raise
            finally:
                if cursor is not None:
                    with suppress(*self.db_errors):
                        cursor.close()

    @staticmethod
    def _scope(scope):
        if not isinstance(scope, Scope):
            raise EconomicError('host_scope_required')
        return ('stripe', scope.account, 'test')

    def _posting(self, cursor, scope, kind, identity):
        return self._one(self._execute(cursor,
            'SELECT * FROM economic_v1_postings WHERE provider=? AND account=? AND environment=? AND kind=? AND economic_id=?',
            (*self._scope(scope), kind, identity)))

    def _transition(self, cursor, scope, event_id, status, reason):
        self._execute(cursor, 'UPDATE economic_v1_messages SET status=?,reason=? '
                      'WHERE provider=? AND account=? AND environment=? AND event_id=?',
                      (status, reason, *self._scope(scope), event_id))
        self._execute(cursor, 'INSERT INTO economic_v1_events(account,event_id,status,reason,recorded_at) VALUES(?,?,?,?,?)',
                      (scope.account, event_id, status, reason, self._stamp()))

    def _apply(self, cursor, scope, event_id, candidates):
        resolved = []
        new_refunds = defaultdict(int)
        for candidate in candidates:
            if candidate.kind == 'capture':
                previous_intent = self._one(self._execute(cursor,
                    "SELECT economic_id FROM economic_v1_postings WHERE provider=? AND account=? AND environment=? "
                    "AND kind='capture' AND payment_intent_id=?", (*self._scope(scope), candidate.payment_intent_id)))
                if previous_intent is not None and previous_intent['economic_id'] != candidate.economic_id:
                    raise EconomicConflict('intent_capture_conflict')
            if candidate.kind == 'refund':
                parent = self._posting(cursor, scope, 'capture', candidate.parent_id)
                if parent is None:
                    return 'awaiting_capture', 'capture_required', 0
                if parent['venture'] != scope.venture or parent['currency'] != candidate.currency:
                    raise EconomicConflict('refund_scope_conflict')
                if candidate.expected_parent_amount_minor is not None and candidate.expected_parent_amount_minor != parent['amount_minor']:
                    raise EconomicConflict('snapshot_parent_amount_conflict')
                if candidate.payment_intent_id and candidate.payment_intent_id != parent['payment_intent_id']:
                    raise EconomicConflict('refund_intent_conflict')
                candidate = replace(candidate, payment_intent_id=parent['payment_intent_id'], expected_parent_amount_minor=None)
            existing = self._posting(cursor, scope, candidate.kind, candidate.economic_id)
            if existing is not None and existing['fingerprint'] != candidate.fingerprint():
                raise EconomicConflict('economic_properties_conflict')
            if existing is None and candidate.kind == 'refund':
                new_refunds[candidate.parent_id] += candidate.amount_minor
            resolved.append((candidate, existing))
        for parent_id, added in new_refunds.items():
            parent = self._posting(cursor, scope, 'capture', parent_id)
            previous = self._one(self._execute(cursor,
                "SELECT COALESCE(SUM(amount_minor),0) AS total FROM economic_v1_postings "
                "WHERE provider=? AND account=? AND environment=? AND kind='refund' AND parent_id=?",
                (*self._scope(scope), parent_id)))['total']
            if previous + added > parent['amount_minor']:
                raise EconomicConflict('refund_exceeds_capture')
        created = 0
        for candidate, existing in resolved:
            if existing is None:
                self._execute(cursor,
                    'INSERT INTO economic_v1_postings(provider,account,environment,kind,economic_id,venture,'
                    'amount_minor,currency,parent_id,payment_intent_id,fingerprint,first_event_id,recorded_at) '
                    'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (*self._scope(scope), candidate.kind, candidate.economic_id, scope.venture,
                     candidate.amount_minor, candidate.currency, candidate.parent_id, candidate.payment_intent_id,
                     candidate.fingerprint(), event_id, self._stamp()))
                created += 1
            self._execute(cursor, 'INSERT INTO economic_v1_links(provider,account,environment,event_id,kind,economic_id) '
                          'VALUES(?,?,?,?,?,?) ON CONFLICT DO NOTHING',
                          (*self._scope(scope), event_id, candidate.kind, candidate.economic_id))
        return 'recorded', 'canonical_capture_or_refund_not_bank_settlement', created

    def _waiting_count(self, cursor, scope):
        return self._one(self._execute(cursor,
            "SELECT COUNT(*) AS count FROM economic_v1_messages WHERE provider=? AND account=? AND environment=? "
            "AND venture=? AND status='awaiting_capture'", (*self._scope(scope), scope.venture)))['count']

    def _reconcile(self, cursor, scope, capture_id, limit):
        rows = self._all(self._execute(cursor,
            "SELECT * FROM economic_v1_messages WHERE provider=? AND account=? AND environment=? AND venture=? "
            "AND status='awaiting_capture' AND dependency_id=? ORDER BY received_at,event_id LIMIT ?",
            (*self._scope(scope), scope.venture, capture_id, limit)))
        reconciled = created = 0
        for row in rows:
            candidates = tuple(Posting(**p) for p in json.loads(row['candidates']))
            try:
                status, reason, added = self._apply(cursor, scope, row['event_id'], candidates)
            except EconomicConflict as exc:
                status, reason, added = 'unresolved', exc.code, 0
            self._transition(cursor, scope, row['event_id'], status, reason)
            reconciled += status == 'recorded'
            created += added
        return reconciled, created

    def ingest(self, payload: bytes, scope: Scope):
        plan = prepare_event(payload, scope)
        with self._transaction(faults=True) as cursor:
            self._fault('before_message')
            old = self._one(self._execute(cursor,
                'SELECT * FROM economic_v1_messages WHERE provider=? AND account=? AND environment=? AND event_id=?',
                (*self._scope(scope), plan.event_id)))
            if old is not None:
                if old['payload_sha256'] != plan.payload_sha256 or old['venture'] != scope.venture:
                    raise EconomicConflict('message_identity_conflict')
                result = {'status': old['status'], 'reason': old['reason'], 'event_id': plan.event_id,
                          'message_created': False, 'created_postings': 0, 'reconciled_messages': 0}
            else:
                dependency = plan.candidates[0].parent_id if plan.candidates and plan.candidates[0].kind == 'refund' else ''
                self._execute(cursor, 'INSERT INTO economic_v1_messages(provider,account,environment,event_id,venture,'
                              'event_type,payload_sha256,candidates,dependency_id,status,reason,received_at) '
                              'VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                              (*self._scope(scope), plan.event_id, scope.venture, plan.event_type, plan.payload_sha256,
                               plan.encoded_candidates(), dependency, 'received', '', self._stamp()))
                self._fault('after_message')
                if plan.reason:
                    status, reason, created = 'unresolved', plan.reason, 0
                else:
                    status, reason, created = self._apply(cursor, scope, plan.event_id, plan.candidates)
                self._transition(cursor, scope, plan.event_id, status, reason)
                self._fault('after_postings')
                reconciled = reconciled_postings = 0
                if status == 'recorded':
                    for candidate in plan.candidates:
                        if candidate.kind == 'capture':
                            count, added = self._reconcile(cursor, scope, candidate.economic_id, self.reconcile_limit)
                            reconciled += count
                            reconciled_postings += added
                result = {'status': status, 'reason': reason, 'event_id': plan.event_id,
                          'message_created': True, 'created_postings': created + reconciled_postings,
                          'reconciled_messages': reconciled}
            result['remaining_awaiting_capture'] = self._waiting_count(cursor, scope)
        try:
            self._fault('after_commit')
        except self.db_errors as exc:
            raise EconomicUnavailable(uncertain=True) from exc
        return result

    def reconcile_waiting(self, scope: Scope, capture_id: str, *, limit=100):
        identifier(capture_id, 'ch_')
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise EconomicError('invalid_reconcile_limit')
        with self._transaction(faults=True) as cursor:
            count, created = self._reconcile(cursor, scope, capture_id, limit)
            return {'reconciled_messages': count, 'created_postings': created,
                    'remaining_awaiting_capture': self._waiting_count(cursor, scope)}

    def messages(self, scope: Scope, *, limit=100, offset=0):
        if type(limit) is not int or not 1 <= limit <= 1000 or type(offset) is not int or offset < 0:
            raise EconomicError('invalid_page')
        with self._transaction(read_only=True) as cursor:
            return self._all(self._execute(cursor,
                'SELECT event_id,event_type,payload_sha256,status,reason,dependency_id FROM economic_v1_messages '
                'WHERE provider=? AND account=? AND environment=? AND venture=? ORDER BY received_at,event_id LIMIT ? OFFSET ?',
                (*self._scope(scope), scope.venture, limit, offset)))

    def postings(self, scope: Scope, *, limit=100, offset=0):
        if type(limit) is not int or not 1 <= limit <= 1000 or type(offset) is not int or offset < 0:
            raise EconomicError('invalid_page')
        with self._transaction(read_only=True) as cursor:
            return self._all(self._execute(cursor,
                'SELECT kind,economic_id,amount_minor,currency,parent_id,payment_intent_id,first_event_id FROM economic_v1_postings '
                'WHERE provider=? AND account=? AND environment=? AND venture=? ORDER BY kind,economic_id LIMIT ? OFFSET ?',
                (*self._scope(scope), scope.venture, limit, offset)))

    def summary(self, scope: Scope, *, expected_net_minor: int | None = None):
        totals = {'capture': 0, 'refund': 0}
        with self._transaction(read_only=True) as cursor:
            self._execute(cursor, 'SELECT kind,amount_minor FROM economic_v1_postings '
                          'WHERE provider=? AND account=? AND environment=? AND venture=?',
                          (*self._scope(scope), scope.venture))
            count = 0
            while rows := cursor.fetchmany(256):
                for kind, amount in rows:
                    totals[kind] += amount
                    count += 1
            unresolved = self._one(self._execute(cursor,
                "SELECT COUNT(*) AS count FROM economic_v1_messages WHERE provider=? AND account=? AND environment=? "
                "AND venture=? AND status!='recorded'", (*self._scope(scope), scope.venture)))['count']
            waiting = self._waiting_count(cursor, scope)
        if any(value > MAX_MINOR for value in totals.values()):
            raise EconomicError('summary_integer_bound_exceeded')
        result = {'mode': 'synthetic_test', 'currency': 'usd', 'posting_count': count,
                  'capture_minor': totals['capture'], 'refund_minor': totals['refund'],
                  'net_captured_minor': totals['capture'] - totals['refund'],
                  'unresolved_messages': unresolved, 'awaiting_capture_messages': waiting,
                  'bank_settlement_verified': False, 'legacy_rows_excluded': True}
        if expected_net_minor is not None:
            result['statement_fixture_drift_minor'] = result['net_captured_minor'] - minor(expected_net_minor)
            result['statement_fixture_matches'] = result['statement_fixture_drift_minor'] == 0
        return result
