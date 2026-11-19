"""OpenBot OS application-owned conversation history, SQLite prototype, MIT.

This is an inert persistence component, NOT an agent, authentication service,
AG-UI conformance implementation, tool executor or multi-tenant security boundary
against a hostile DB/host. Trusted middleware must derive Scope from an
ALREADY authenticated identity. Never derive it from a request body's user ID.

Use a dedicated private SQLite connection with isolation_level=None. The caller
owns its lifecycle, directory/ACLs, backup, retention and capacity monitoring.
No file, network connection, migration of an existing DB, model or telemetry is
opened/enabled by this module. All limits below cap logical application data,
not physical SQLite file size or storage held by backups/journals.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass

SCHEMA_VERSION = 1
MAX_EVENT_BYTES = 32768
MAX_EVENT_NODES = 2048
MAX_EVENT_DEPTH = 12
MAX_PAGE_EVENTS = 100
MAX_PAGE_BYTES = 131072
MAX_EVENTS_PER_THREAD = 4096
MAX_THREAD_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_THREADS_PER_SCOPE = 1000
MAX_THREADS_TOTAL = 10000
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}\Z", re.ASCII)
EVENT_TYPE = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z", re.ASCII)

DDL = (
    "CREATE TABLE os_conversation_v1_schema (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL)",
    "INSERT INTO os_conversation_v1_schema VALUES(1,1)",
    """CREATE TABLE os_conversation_v1_threads (
        tenant TEXT NOT NULL, principal TEXT NOT NULL, thread_id TEXT NOT NULL,
        title TEXT NOT NULL, event_count INTEGER NOT NULL DEFAULT 0 CHECK(event_count>=0),
        byte_count INTEGER NOT NULL DEFAULT 0 CHECK(byte_count>=0),
        PRIMARY KEY(tenant,principal,thread_id)
    )""",
    """CREATE TABLE os_conversation_v1_events (
        tenant TEXT NOT NULL, principal TEXT NOT NULL, thread_id TEXT NOT NULL,
        sequence INTEGER NOT NULL CHECK(sequence>=1), event_id TEXT NOT NULL,
        payload TEXT NOT NULL, digest TEXT NOT NULL,
        PRIMARY KEY(tenant,principal,thread_id,sequence),
        UNIQUE(tenant,principal,thread_id,event_id),
        FOREIGN KEY(tenant,principal,thread_id)
          REFERENCES os_conversation_v1_threads(tenant,principal,thread_id) ON DELETE CASCADE
    )""",
)


class JournalError(ValueError):
    """Safe, stable error code; no stored content or filesystem paths in messages."""


class JournalUnavailable(RuntimeError):
    pass


def _token(value):
    if type(value) is not str or TOKEN.fullmatch(value) is None:
        raise JournalError("invalid_identity")
    return value


@dataclass(frozen=True)
class Scope:
    tenant: str
    principal: str

    def __post_init__(self):
        _token(self.tenant)
        _token(self.principal)


def _scope(value):
    if type(value) is not Scope:
        raise JournalError("authenticated_scope_required")
    return value.tenant, value.principal


def _integer(value, maximum, *, minimum=0):
    if type(value) is not int or not minimum <= value <= maximum:
        raise JournalError("invalid_bound")
    return value


def _event_json(event, thread_id):
    if (
        type(event) is not dict
        or type(event.get("type")) is not str
        or not EVENT_TYPE.fullmatch(event["type"])
    ):
        raise JournalError("invalid_event_type")
    if "threadId" in event and event["threadId"] != thread_id:
        raise JournalError("thread_correlation_conflict")
    nodes = 0

    def inspect(value, depth):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_EVENT_NODES or depth > MAX_EVENT_DEPTH:
            raise JournalError("event_complexity_limit")
        kind = type(value)
        if kind is dict:
            if len(value) > 256:
                raise JournalError("event_complexity_limit")
            for key, item in value.items():
                if type(key) is not str or len(key) > 128:
                    raise JournalError("invalid_json_key")
                inspect(item, depth + 1)
        elif kind is list:
            if len(value) > 256:
                raise JournalError("event_complexity_limit")
            for item in value:
                inspect(item, depth + 1)
        elif kind is float:
            if not math.isfinite(value):
                raise JournalError("invalid_json_number")
        elif kind is int:
            if abs(value) > 2**53 - 1:
                raise JournalError("invalid_json_number")
        elif kind is str:
            if len(value) > MAX_EVENT_BYTES:
                raise JournalError("event_byte_limit")
        elif kind not in (type(None), bool):
            raise JournalError("invalid_json_type")

    inspect(event, 0)
    try:
        payload = json.dumps(
            event, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
        raw = payload.encode("utf-8", errors="strict")
    except (ValueError, UnicodeError) as exc:
        raise JournalError("invalid_json_encoding") from exc
    if len(raw) > MAX_EVENT_BYTES:
        raise JournalError("event_byte_limit")
    return payload, hashlib.sha256(raw).hexdigest(), len(raw)


class ConversationJournal:
    """Ordered, idempotent, owner-scoped event history; no action is ever executed.

    Sequence is a compare-and-swap precondition (the previous committed sequence),
    not an event field. A retry of the SAME event ID/content/precondition returns
    its original sequence. Reusing that ID differently or appending from a stale
    sequence fails. Persistence/replay does NOT resume a running agent or make
    external effects exactly-once. Shares, retention, HTTP and PG are not wired.
    """

    def __init__(self, connection, *, initialize=False):
        if type(initialize) is not bool or not isinstance(connection, sqlite3.Connection):
            raise JournalError("dedicated_sqlite_connection_required")
        if connection.isolation_level is not None or connection.in_transaction:
            raise JournalError("explicit_autocommit_connection_required")
        self.connection = connection
        self.lock = threading.RLock()
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
                raise JournalError("foreign_keys_required")
            with self._tx() as db:
                names = {
                    row[0]
                    for row in db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )
                }
                if initialize and not names:
                    for statement in DDL:
                        db.execute(statement)
                elif names != {
                    "os_conversation_v1_schema",
                    "os_conversation_v1_threads",
                    "os_conversation_v1_events",
                }:
                    raise JournalError("existing_schema_required_or_incompatible")
                version = db.execute(
                    "SELECT version FROM os_conversation_v1_schema WHERE id=1"
                ).fetchone()
                if version is None or version[0] != SCHEMA_VERSION:
                    raise JournalError("incompatible_schema_version")
                db.execute(
                    "SELECT tenant,principal,thread_id,title,event_count,byte_count FROM os_conversation_v1_threads LIMIT 0"
                )
                db.execute(
                    "SELECT tenant,principal,thread_id,sequence,event_id,payload,digest FROM os_conversation_v1_events LIMIT 0"
                )
        except sqlite3.Error as exc:
            raise JournalUnavailable("conversation_storage_unavailable") from exc

    @contextmanager
    def _tx(self):
        # A dedicated connection must not be shared with unrelated transactions.
        with self.lock:
            if self.connection.in_transaction:
                raise JournalError("foreign_transaction_active")
            started = False
            try:
                self.connection.execute("BEGIN IMMEDIATE")
                started = True
                yield self.connection
                self.connection.execute("COMMIT")
            except BaseException as exc:
                if started and self.connection.in_transaction:
                    self.connection.rollback()
                if isinstance(exc, sqlite3.Error):
                    raise JournalUnavailable("conversation_storage_unavailable") from exc
                raise

    @staticmethod
    def _thread(db, key):
        row = db.execute(
            "SELECT title,event_count,byte_count FROM os_conversation_v1_threads WHERE tenant=? AND principal=? AND thread_id=?",
            key,
        ).fetchone()
        if row is None:
            # Wrong tenant/principal is indistinguishable from a missing thread.
            raise JournalError("thread_not_found")
        return row

    def create_thread(self, scope, thread_id, *, title=""):
        key = (*_scope(scope), _token(thread_id))
        if type(title) is not str or len(title) > 200 or "\x00" in title:
            raise JournalError("invalid_title")
        try:
            title.encode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise JournalError("invalid_title") from exc
        with self._tx() as db:
            old = db.execute(
                "SELECT title FROM os_conversation_v1_threads WHERE tenant=? AND principal=? AND thread_id=?",
                key,
            ).fetchone()
            if old is not None:
                if old[0] != title:
                    raise JournalError("thread_identity_conflict")
                return thread_id
            count = db.execute(
                "SELECT COUNT(*) FROM os_conversation_v1_threads WHERE tenant=? AND principal=?",
                key[:2],
            ).fetchone()[0]
            total = db.execute("SELECT COUNT(*) FROM os_conversation_v1_threads").fetchone()[0]
            if count >= MAX_THREADS_PER_SCOPE or total >= MAX_THREADS_TOTAL:
                raise JournalError("thread_count_limit")
            db.execute(
                "INSERT INTO os_conversation_v1_threads(tenant,principal,thread_id,title) VALUES(?,?,?,?)",
                (*key, title),
            )
        return thread_id

    def list_threads(self, scope, *, after="", limit=50):
        owner = _scope(scope)
        if after != "":
            _token(after)
        _integer(limit, MAX_PAGE_EVENTS, minimum=1)
        with self._tx() as db:
            rows = db.execute(
                "SELECT thread_id,title,event_count FROM os_conversation_v1_threads WHERE tenant=? AND principal=? AND thread_id>? ORDER BY thread_id LIMIT ?",
                (*owner, after, limit + 1),
            ).fetchall()
        items = [
            {"thread_id": row[0], "title": row[1], "event_count": row[2]} for row in rows[:limit]
        ]
        return {
            "threads": items,
            "next_after": items[-1]["thread_id"] if len(rows) > limit else None,
        }

    def append(self, scope, thread_id, *, event_id, event, expected_sequence):
        key = (*_scope(scope), _token(thread_id))
        _token(event_id)
        _integer(expected_sequence, MAX_EVENTS_PER_THREAD)
        payload, digest, size = _event_json(event, thread_id)
        with self._tx() as db:
            _, count, used = self._thread(db, key)
            old = db.execute(
                "SELECT sequence,payload,digest FROM os_conversation_v1_events WHERE tenant=? AND principal=? AND thread_id=? AND event_id=?",
                (*key, event_id),
            ).fetchone()
            if old is not None:
                if old[1] != payload or old[2] != digest or old[0] != expected_sequence + 1:
                    raise JournalError("event_identity_conflict")
                return old[0]
            if count != expected_sequence:
                raise JournalError("stale_sequence")
            total = db.execute(
                "SELECT COALESCE(SUM(byte_count),0) FROM os_conversation_v1_threads"
            ).fetchone()[0]
            if (
                count >= MAX_EVENTS_PER_THREAD
                or used + size > MAX_THREAD_BYTES
                or total + size > MAX_TOTAL_BYTES
            ):
                raise JournalError("conversation_capacity_limit")
            sequence = count + 1
            db.execute(
                "INSERT INTO os_conversation_v1_events VALUES(?,?,?,?,?,?,?)",
                (*key, sequence, event_id, payload, digest),
            )
            db.execute(
                "UPDATE os_conversation_v1_threads SET event_count=?,byte_count=? WHERE tenant=? AND principal=? AND thread_id=?",
                (sequence, used + size, *key),
            )
        return sequence

    def read_events(self, scope, thread_id, *, after=0, limit=50):
        key = (*_scope(scope), _token(thread_id))
        _integer(after, MAX_EVENTS_PER_THREAD)
        _integer(limit, MAX_PAGE_EVENTS, minimum=1)
        with self._tx() as db:
            _, count, _ = self._thread(db, key)
            if after > count:
                raise JournalError("cursor_ahead_of_thread")
            # Fetch incrementally: LIMIT alone is not a payload-byte bound.
            cursor = db.execute(
                "SELECT sequence,event_id,payload,digest FROM os_conversation_v1_events WHERE tenant=? AND principal=? AND thread_id=? AND sequence>? ORDER BY sequence LIMIT ?",
                (*key, after, limit),
            )
            events, size = [], 0
            for row in cursor:
                raw = row[2].encode("utf-8")
                if hashlib.sha256(raw).hexdigest() != row[3]:
                    raise JournalError("stored_event_integrity_error")
                if size + len(raw) > MAX_PAGE_BYTES:
                    break
                size += len(raw)
                events.append(
                    {
                        "sequence": row[0],
                        "event_id": row[1],
                        "event": json.loads(row[2]),
                        "sha256": row[3],
                    }
                )
        last = events[-1]["sequence"] if events else after
        return {
            "events": events,
            "next_after": last if last < count else None,
            "head_sequence": count,
            "payload_bytes": size,
        }

    def delete_thread(self, scope, thread_id):
        """Logical deletion only. Not secure erase, backup deletion or audit deletion."""
        key = (*_scope(scope), _token(thread_id))
        with self._tx() as db:
            self._thread(db, key)
            db.execute(
                "DELETE FROM os_conversation_v1_threads WHERE tenant=? AND principal=? AND thread_id=?",
                key,
            )
