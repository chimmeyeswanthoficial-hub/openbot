"""Persistence for the control plane. One implementation, two backends.

SQLite in memory for tests and evaluation, a file on disk for the demo and for a single-box
deployment. PostgreSQL for production multi-worker environments (T4).

Two rules that live here because they are storage properties, not policy:
  * the audit log is append-only — there is no update and no delete method;
  * an approval can be resolved exactly once — enforced by a conditional UPDATE, so two
    approvals arriving at the same moment cannot both win.
"""

from __future__ import annotations

import json
import math
import sqlite3
import threading
import time
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import psycopg2
    import psycopg2.extras
    _HAVE_PSYCOPG2 = True
except ImportError:
    _HAVE_PSYCOPG2 = False

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit (
  seq        INTEGER PRIMARY KEY AUTOINCREMENT,
  ts         TEXT NOT NULL,
  run_id     TEXT NOT NULL,
  venture    TEXT,
  actor      TEXT,
  action     TEXT,
  decision   TEXT NOT NULL,
  rule       TEXT NOT NULL,
  reason     TEXT,
  initiator_kind TEXT,
  initiator_id   TEXT,
  approval_id    TEXT,
  cost_usd   REAL DEFAULT 0,
  scrubbed   INTEGER DEFAULT 0,
  target     TEXT,
  latency_ms REAL
);
CREATE INDEX IF NOT EXISTS audit_venture_ts ON audit(venture, ts);
CREATE INDEX IF NOT EXISTS audit_decision   ON audit(decision);

CREATE TABLE IF NOT EXISTS approvals (
  id        TEXT PRIMARY KEY,
  created   TEXT NOT NULL,
  resolved  TEXT,
  status    TEXT NOT NULL CHECK (status IN ('pending','approved','denied','expired')),
  run_id    TEXT NOT NULL,
  venture   TEXT NOT NULL,
  rule      TEXT NOT NULL,
  reason    TEXT,
  action    TEXT,
  cost_usd  REAL DEFAULT 0,
  by        TEXT,
  note      TEXT
);
CREATE INDEX IF NOT EXISTS approvals_status ON approvals(status);

CREATE TABLE IF NOT EXISTS ledger (
  seq             INTEGER PRIMARY KEY AUTOINCREMENT,
  ts              TEXT NOT NULL,
  venture         TEXT NOT NULL,
  kind            TEXT NOT NULL,
  amount_usd      REAL NOT NULL,
  source          TEXT NOT NULL,
  external_id     TEXT,
  idempotency_key TEXT NOT NULL UNIQUE,
  meta            TEXT
);

CREATE TABLE IF NOT EXISTS runs (
  id           TEXT PRIMARY KEY,
  routine_id   TEXT NOT NULL,
  venture      TEXT NOT NULL,
  started      TEXT NOT NULL,
  ended        TEXT,
  status       TEXT NOT NULL,
  cost_usd     REAL DEFAULT 0,
  detail       TEXT
);
"""

PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit (
  seq        BIGSERIAL PRIMARY KEY,
  ts         TEXT NOT NULL,
  run_id     TEXT NOT NULL,
  venture    TEXT,
  actor      TEXT,
  action     TEXT,
  decision   TEXT NOT NULL,
  rule       TEXT NOT NULL,
  reason     TEXT,
  initiator_kind TEXT,
  initiator_id   TEXT,
  approval_id    TEXT,
  cost_usd   DOUBLE PRECISION DEFAULT 0,
  scrubbed   INTEGER DEFAULT 0,
  target     TEXT,
  latency_ms DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS audit_venture_ts ON audit(venture, ts);
CREATE INDEX IF NOT EXISTS audit_decision   ON audit(decision);

CREATE TABLE IF NOT EXISTS approvals (
  id        TEXT PRIMARY KEY,
  created   TEXT NOT NULL,
  resolved  TEXT,
  status    TEXT NOT NULL CHECK (status IN ('pending','approved','denied','expired')),
  run_id    TEXT NOT NULL,
  venture   TEXT NOT NULL,
  rule      TEXT NOT NULL,
  reason    TEXT,
  action    TEXT,
  cost_usd  DOUBLE PRECISION DEFAULT 0,
  by        TEXT,
  note      TEXT
);
CREATE INDEX IF NOT EXISTS approvals_status ON approvals(status);

CREATE TABLE IF NOT EXISTS ledger (
  seq             BIGSERIAL PRIMARY KEY,
  ts              TEXT NOT NULL,
  venture         TEXT NOT NULL,
  kind            TEXT NOT NULL,
  amount_usd      DOUBLE PRECISION NOT NULL,
  source          TEXT NOT NULL,
  external_id     TEXT,
  idempotency_key TEXT NOT NULL UNIQUE,
  meta            TEXT
);

CREATE TABLE IF NOT EXISTS runs (
  id           TEXT PRIMARY KEY,
  routine_id   TEXT NOT NULL,
  venture      TEXT NOT NULL,
  started      TEXT NOT NULL,
  ended        TEXT,
  status       TEXT NOT NULL,
  cost_usd     DOUBLE PRECISION DEFAULT 0,
  detail       TEXT
);
"""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass(frozen=True)
class Store:
    path: str = ":memory:"
    initialize: bool = field(default=True, kw_only=True)

    def __post_init__(self) -> None:
        """Open one owned connection; an app role need not be a schema owner.

        The legacy default preserves explicit local/demo initialization. Operators
        can provision with a separate migration identity, then open an existing
        store with initialize=False. That mode executes no schema DDL and never
        creates an absent SQLite file. It is not remote authentication, a grant
        installer, a production migration or a tenant-isolation claim.
        """
        if type(self.initialize) is not bool:
            raise ValueError("initialize_must_be_boolean")
        object.__setattr__(self, "_lock", threading.Lock())
        is_pg = self.path.startswith(("postgres://", "postgresql://"))
        object.__setattr__(self, "_is_pg", is_pg)
        if is_pg:
            if not _HAVE_PSYCOPG2:
                raise RuntimeError("psycopg2 is required for PostgreSQL backend")
            conn = psycopg2.connect(self.path)
        elif self.initialize:
            conn = sqlite3.connect(self.path, check_same_thread=False)
        else:
            if self.path == ":memory:" or self.path.startswith("file:"):
                raise ValueError("existing_plain_sqlite_path_required")
            conn = sqlite3.connect(Path(self.path).resolve().as_uri() + "?mode=rw",
                                   uri=True, check_same_thread=False)
        if not is_pg:
            conn.row_factory = sqlite3.Row
        object.__setattr__(self, "_conn", conn)
        try:
            with self._lock:
                if self.initialize:
                    if is_pg:
                        with conn.cursor() as cur:
                            cur.execute(PG_SCHEMA)
                    else:
                        conn.executescript(SCHEMA)
                    conn.commit()
                else:
                    # Validate required existing tables/columns without DDL,
                    # writes, or leaving our fresh PG connection in a read tx.
                    with closing(conn.cursor()) as cur:
                        for query in (
                            "SELECT seq,ts,run_id,venture,actor,action,decision,rule,reason,initiator_kind,initiator_id,approval_id,cost_usd,scrubbed,target,latency_ms FROM audit WHERE 1=0",
                            "SELECT id,created,resolved,status,run_id,venture,rule,reason,action,cost_usd,by,note FROM approvals WHERE 1=0",
                            "SELECT seq,ts,venture,kind,amount_usd,source,external_id,idempotency_key,meta FROM ledger WHERE 1=0",
                            "SELECT id,routine_id,venture,started,ended,status,cost_usd,detail FROM runs WHERE 1=0",
                        ):
                            cur.execute(query)
                    conn.rollback()  # only the read transaction we just opened
        except BaseException:
            conn.close()  # construction failed; no usable Store escapes
            raise

    # -- audit (append-only) -------------------------------------------------
    def audit(self, row: dict[str, Any]) -> int:
        params = (row.get("ts") or _now(), row["run_id"], row.get("venture"), row.get("actor"),
                  row.get("action"), row["decision"], row["rule"], row.get("reason"),
                  (row.get("initiator") or {}).get("kind"),
                  (row.get("initiator") or {}).get("id"),
                  row.get("approval_id"), row.get("cost_usd") or 0.0,
                  1 if row.get("scrubbed") else 0,
                  json.dumps(row.get("target") or {}), row.get("latency_ms"))
        sql = """INSERT INTO audit(ts,run_id,venture,actor,action,decision,rule,reason,
                       initiator_kind,initiator_id,approval_id,cost_usd,scrubbed,target,latency_ms)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
        with self._lock:
            if self._is_pg:
                with self._conn.cursor() as cur:
                    cur.execute(sql.replace("?", "%s") + " RETURNING seq", params)
                    seq = int(cur.fetchone()[0])
                self._conn.commit()
                return seq
            else:
                cur = self._conn.execute(sql, params)
                self._conn.commit()
                return int(cur.lastrowid or 0)

    def audit_tail(self, limit: int = 50, *, decision: str | None = None,
                   venture: str | None = None, run_id: str | None = None,
                   action: str | None = None) -> list[dict[str, Any]]:
        q, args = "SELECT * FROM audit", []
        where = []
        if decision:
            where.append("decision = ?")
            args.append(decision)
        if venture:
            where.append("venture = ?")
            args.append(venture)
        if run_id:
            where.append("run_id = ?")
            args.append(run_id)
        if action:
            where.append("action = ?")
            args.append(action)
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " ORDER BY seq DESC LIMIT ?"
        args.append(limit)
        with self._lock:
            if self._is_pg:
                with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(q.replace("?", "%s"), tuple(args))
                    rows = [dict(r) for r in cur.fetchall()]
            else:
                rows = [dict(r) for r in self._conn.execute(q, args).fetchall()]
        for r in rows:
            r["target"] = json.loads(r["target"] or "{}") if isinstance(r["target"], str) else (r["target"] or {})
            r["scrubbed"] = bool(r["scrubbed"])
        return rows

    def audit_count(self) -> int:
        with self._lock:
            if self._is_pg:
                with self._conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM audit")
                    return int(cur.fetchone()[0])
            else:
                return int(self._conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0])

    # -- approvals -----------------------------------------------------------
    def create_approval(self, row: dict[str, Any]) -> dict[str, Any]:
        aid = row.get("id") or f"ap_{uuid.uuid4().hex[:12]}"
        sql = """INSERT INTO approvals(id,created,status,run_id,venture,rule,reason,action,cost_usd)
                   VALUES(?,?,?,?,?,?,?,?,?)"""
        params = (aid, row.get("created") or _now(), "pending", row["run_id"], row["venture"],
                  row["rule"], row.get("reason"), json.dumps(row.get("action") or {}),
                  row.get("cost_usd") or 0.0)
        with self._lock:
            if self._is_pg:
                with self._conn.cursor() as cur:
                    cur.execute(sql.replace("?", "%s"), params)
                self._conn.commit()
            else:
                self._conn.execute(sql, params)
                self._conn.commit()
        return self.get_approval(aid)  # type: ignore[return-value]

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        with self._lock:
            if self._is_pg:
                with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM approvals WHERE id = %s", (approval_id,))
                    r = cur.fetchone()
            else:
                r = self._conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        return self._approval_dict(dict(r)) if r else None

    def list_approvals(self, status: str = "pending") -> list[dict[str, Any]]:
        with self._lock:
            if status == "all":
                q = "SELECT * FROM approvals ORDER BY created DESC"
                params = ()
            else:
                q = "SELECT * FROM approvals WHERE status = ? ORDER BY created DESC"
                params = (status,)
            if self._is_pg:
                with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(q.replace("?", "%s"), params)
                    rows = cur.fetchall()
            else:
                rows = self._conn.execute(q, params).fetchall()
        return [self._approval_dict(dict(r)) for r in rows]

    def resolve_approval(self, approval_id: str, decision: str, by: str,
                         note: str | None = None) -> bool:
        """Exactly-once. Returns False if it was already resolved (a lost race, not an error)."""
        if decision not in ("approved", "denied"):
            raise ValueError("decision must be approved|denied")
        sql = """UPDATE approvals SET status=?, resolved=?, by=?, note=?
                   WHERE id=? AND status='pending'"""
        params = (decision, _now(), by, note, approval_id)
        with self._lock:
            if self._is_pg:
                with self._conn.cursor() as cur:
                    cur.execute(sql.replace("?", "%s"), params)
                    rc = cur.rowcount
                self._conn.commit()
                return rc == 1
            else:
                cur = self._conn.execute(sql, params)
                self._conn.commit()
                return cur.rowcount == 1

    def expire_approvals(self, older_than_seconds: int) -> int:
        """An ignored approval must not sit forever looking like work in progress."""
        cutoff = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                               time.gmtime(time.time() - older_than_seconds))
        sql = """UPDATE approvals SET status='expired', resolved=?
                   WHERE status='pending' AND created < ?"""
        params = (_now(), cutoff)
        with self._lock:
            if self._is_pg:
                with self._conn.cursor() as cur:
                    cur.execute(sql.replace("?", "%s"), params)
                    rc = cur.rowcount
                self._conn.commit()
                return rc
            else:
                cur = self._conn.execute(sql, params)
                self._conn.commit()
                return cur.rowcount

    @staticmethod
    def _approval_dict(d: dict[str, Any]) -> dict[str, Any]:
        out = dict(d)
        if isinstance(out.get("action"), str):
            out["action"] = json.loads(out["action"] or "{}")
        elif out.get("action") is None:
            out["action"] = {}
        out["cost_usd"] = float(out.get("cost_usd") or 0)
        return out

    # -- ledger (append-only, idempotent) -----------------------------------
    def post_ledger(self, row: dict[str, Any]) -> bool:
        """Legacy/manual REAL ledger only; canonical economics uses a separate book.

        Only the designated key conflict is a replay, never an unrelated integrity
        error. Existing legacy rows are not rewritten or inferred to be settled.
        """
        if type(row.get("amount_usd")) is bool:
            raise ValueError("legacy_money_must_be_finite_not_boolean")
        try:
            amount = float(row.get("amount_usd"))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("invalid_legacy_money") from exc
        if not math.isfinite(amount):
            raise ValueError("legacy_money_must_be_finite")
        sql = """INSERT INTO ledger(ts,venture,kind,amount_usd,source,external_id,
                       idempotency_key,meta) VALUES(?,?,?,?,?,?,?,?)
                       ON CONFLICT(idempotency_key) DO NOTHING"""
        params = (row.get("ts") or _now(), row["venture"], row["kind"],
                  amount, row["source"], row.get("external_id"),
                  row["idempotency_key"], json.dumps(row.get("meta") or {}))
        with self._lock:
            try:
                with closing(self._conn.cursor()) as cursor:
                    cursor.execute(sql.replace("?", "%s") if self._is_pg else sql, params)
                    created = cursor.rowcount == 1
                self._conn.commit()
                return created
            except Exception:
                self._conn.rollback()
                raise

    def ledger_rows(self, venture: str | None = None) -> list[dict[str, Any]]:
        q, args = "SELECT * FROM ledger", []
        if venture:
            q += " WHERE venture = ?"
            args.append(venture)
        q += " ORDER BY seq"
        with self._lock:
            if self._is_pg:
                with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(q.replace("?", "%s"), tuple(args))
                    rows = [dict(r) for r in cur.fetchall()]
            else:
                rows = [dict(r) for r in self._conn.execute(q, args).fetchall()]
        for r in rows:
            r["meta"] = json.loads(r.get("meta") or "{}") if isinstance(r.get("meta"), str) else (r.get("meta") or {})
        return rows

    # -- runs ----------------------------------------------------------------
    def start_run(self, routine_id: str, venture: str) -> str:
        rid = f"run_{uuid.uuid4().hex[:12]}"
        sql = "INSERT INTO runs(id,routine_id,venture,started,status) VALUES(?,?,?,?,?)"
        params = (rid, routine_id, venture, _now(), "running")
        with self._lock:
            if self._is_pg:
                with self._conn.cursor() as cur:
                    cur.execute(sql.replace("?", "%s"), params)
                self._conn.commit()
            else:
                self._conn.execute(sql, params)
                self._conn.commit()
        return rid

    def claim_run_dispatch(self, run_id: str, routine_id: str, venture: str) -> bool:
        """Durable single attempt, scoped to an existing trusted-host run.

        A claim is not authentication, a spend reservation or provider completion.
        Crash/unknown claims stay unavailable for automatic retry. The conditional
        database write, not this instance's lock, excludes other connections.
        """
        sql = """UPDATE runs SET status='dispatching', ended=NULL, detail=?
                 WHERE id=? AND routine_id=? AND venture=?
                 AND (status='queued' OR (status='running' AND ended IS NULL))"""
        params = ("transport attempt claimed; completion, stop and cost unverified",
                  run_id, routine_id, venture)
        with self._lock:
            try:
                if self._is_pg:
                    with self._conn.cursor() as cur:
                        cur.execute("SELECT to_regclass('work_v1_tasks')")
                        if cur.fetchone()[0] is not None:
                            cur.execute('SELECT 1 FROM work_v1_tasks WHERE id=%s', (run_id,))
                            if cur.fetchone():
                                self._conn.rollback()
                                return False  # never bypass the new authority/reservation/fence boundary
                        cur.execute(sql.replace("?", "%s"), params)
                        won = cur.rowcount == 1
                else:
                    exists = self._conn.execute("SELECT 1 FROM sqlite_master WHERE name='work_v1_tasks' AND type='table'").fetchone()
                    if exists and self._conn.execute('SELECT 1 FROM work_v1_tasks WHERE id=?', (run_id,)).fetchone():
                        return False
                    won = self._conn.execute(sql, params).rowcount == 1
                self._conn.commit()
                return won
            except Exception:
                self._conn.rollback()
                raise

    def finish_run_dispatch(self, run_id: str, routine_id: str, venture: str,
                            status: str, detail: str) -> bool:
        """End only our scoped in-progress claim; never settle unverified money."""
        if status not in {"response_received", "reconciliation_required"}:
            raise ValueError("unsupported transport outcome")
        sql = """UPDATE runs SET ended=?, status=?, cost_usd=0, detail=?
                 WHERE id=? AND routine_id=? AND venture=? AND status='dispatching'"""
        params = (_now(), status, detail, run_id, routine_id, venture)
        with self._lock:
            try:
                if self._is_pg:
                    with self._conn.cursor() as cur:
                        cur.execute(sql.replace("?", "%s"), params)
                        won = cur.rowcount == 1
                else:
                    won = self._conn.execute(sql, params).rowcount == 1
                self._conn.commit()
                return won
            except Exception:
                self._conn.rollback()
                raise

    def end_run(self, run_id: str, status: str, cost_usd: float = 0.0,
                detail: str | None = None) -> None:
        sql = "UPDATE runs SET ended=?, status=?, cost_usd=?, detail=? WHERE id=?"
        params = (_now(), status, cost_usd, detail, run_id)
        with self._lock:
            if self._is_pg:
                with self._conn.cursor() as cur:
                    cur.execute(sql.replace("?", "%s"), params)
                self._conn.commit()
            else:
                self._conn.execute(sql, params)
                self._conn.commit()

    def runs(self, limit: int = 100) -> list[dict[str, Any]]:
        sql = "SELECT * FROM runs ORDER BY started DESC LIMIT ?"
        with self._lock:
            if self._is_pg:
                with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql.replace("?", "%s"), (limit,))
                    return [dict(r) for r in cur.fetchall()]
            else:
                return [dict(r) for r in self._conn.execute(sql, (limit,)).fetchall()]
