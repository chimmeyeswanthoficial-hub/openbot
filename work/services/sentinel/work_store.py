"""Durable local work kernel. Explicit additive setup; no provider or public activation.

One transaction owns occurrence identity, whole-liability reservations, fencing,
pre-effect audit and append-only history on SQLite/PG. Host code and DB owner are
trusted; agents never receive this connection. Money is USD integer minor units,
not a claim that a provider obeys a cap or that synthetic usage is settlement.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal, InvalidOperation

MAX_MINOR = 2**53 - 1
STATES = (
    "preparing",
    "queued",
    "review",
    "running",
    "completed",
    "failed",
    "blocked",
    "uncertain",
    "cancelled",
    "denied",
)
SCHEMA = """
CREATE TABLE IF NOT EXISTS work_v1_schema(id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL);
INSERT INTO work_v1_schema VALUES(1,1) ON CONFLICT(id) DO NOTHING;
CREATE TABLE IF NOT EXISTS work_v1_limits(scope TEXT PRIMARY KEY, cap_minor BIGINT NOT NULL CHECK(cap_minor>=0));
CREATE TABLE IF NOT EXISTS work_v1_tasks(
 id TEXT PRIMARY KEY, venture TEXT NOT NULL, routine TEXT NOT NULL, origin TEXT NOT NULL,
 occurrence_key TEXT NOT NULL, scheduled_utc TEXT NOT NULL, initiator_json TEXT NOT NULL,
 spec_digest TEXT NOT NULL, plan_json TEXT NOT NULL, principal TEXT NOT NULL,
 upper_minor BIGINT NOT NULL CHECK(upper_minor>=0), budget_day TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('preparing','queued','review','running','completed','failed','blocked','uncertain','cancelled','denied')),
 held_minor BIGINT NOT NULL DEFAULT 0 CHECK(held_minor>=0), spent_minor BIGINT NOT NULL DEFAULT 0 CHECK(spent_minor>=0),
 worker TEXT NOT NULL DEFAULT '', fence INTEGER NOT NULL DEFAULT 0, lease_until BIGINT NOT NULL DEFAULT 0,
 attempted INTEGER NOT NULL DEFAULT 0, cancel_requested INTEGER NOT NULL DEFAULT 0,
 approval_digest TEXT NOT NULL DEFAULT '', approval_until BIGINT NOT NULL DEFAULT 0,
 approved_by TEXT NOT NULL DEFAULT '', reviewer_principal TEXT NOT NULL DEFAULT '', result_json TEXT NOT NULL DEFAULT '{}',
 UNIQUE(venture,routine,origin,occurrence_key)
);
CREATE TABLE IF NOT EXISTS work_v1_history(seq {SEQ}, task_id TEXT NOT NULL, kind TEXT NOT NULL,
 payload_json TEXT NOT NULL, stamp BIGINT NOT NULL);
CREATE TABLE IF NOT EXISTS work_v1_legacy(run_id TEXT PRIMARY KEY, venture TEXT NOT NULL,
 budget_day TEXT NOT NULL, upper_minor BIGINT NOT NULL CHECK(upper_minor>=0), evidence_digest TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS work_v1_usage(receipt_id TEXT PRIMARY KEY, task_id TEXT NOT NULL UNIQUE,
 amount_minor BIGINT NOT NULL CHECK(amount_minor>=0), evidence_digest TEXT NOT NULL, recognized_day TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS work_v1_events(task_id TEXT NOT NULL, seq INTEGER NOT NULL,
 payload_json TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(task_id,seq));
CREATE TABLE IF NOT EXISTS work_v1_outbox(task_id TEXT PRIMARY KEY, destination TEXT NOT NULL,
 content_json TEXT NOT NULL, sha256 TEXT NOT NULL, status TEXT NOT NULL, reviewer TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS work_v1_sessions(token_hash TEXT PRIMARY KEY, actor TEXT NOT NULL,
 venture TEXT NOT NULL, role TEXT NOT NULL, initiator_json TEXT NOT NULL,
 expires BIGINT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
"""
IDENTITY = (
    "id",
    "venture",
    "routine",
    "origin",
    "occurrence_key",
    "scheduled_utc",
    "initiator_json",
    "spec_digest",
    "plan_json",
    "principal",
    "upper_minor",
    "budget_day",
)
IMMUTABLE = ("history", "legacy", "usage", "events", "limits")
# Explicit read probes fail closed for an incomplete unreleased prototype shape.
# Setup is additive on a fresh profile; neither runtime nor setup silently ALTERs
# existing work schemas. Real upgrades require a separately reviewed migration.
COLUMNS = {
    "schema": "id,version",
    "limits": "scope,cap_minor",
    "tasks": ",".join(IDENTITY)
    + ",status,held_minor,spent_minor,worker,fence,lease_until,attempted,cancel_requested,approval_digest,approval_until,approved_by,reviewer_principal,result_json",
    "history": "seq,task_id,kind,payload_json,stamp",
    "legacy": "run_id,venture,budget_day,upper_minor,evidence_digest",
    "usage": "receipt_id,task_id,amount_minor,evidence_digest,recognized_day",
    "events": "task_id,seq,payload_json,digest",
    "outbox": "task_id,destination,content_json,sha256,status,reviewer",
    "sessions": "token_hash,actor,venture,role,initiator_json,expires,revoked",
}


class WorkError(ValueError):
    pass


class WorkUnavailable(RuntimeError):
    def __init__(self, *, uncertain=False):
        super().__init__("work_storage_unavailable")
        self.uncertain = uncertain


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def minor(value):
    """Conservative upper bound: never round a positive fractional cent down."""
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or number > Decimal(MAX_MINOR) / 100:
            raise WorkError("invalid_usd_bound")
        return int((number * 100).to_integral_value(rounding=ROUND_CEILING))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise WorkError("invalid_usd_bound") from exc


def integer(value):
    if type(value) is not int or not 0 <= value <= MAX_MINOR:
        raise WorkError("invalid_minor_units")
    return value


def utc(value):
    if not isinstance(value, datetime):
        raise WorkError("datetime_required")
    # Legacy caller-supplied naive clocks are explicitly interpreted as UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _view(row):
    if row is None:
        return None
    result = dict(row)
    for key in ("plan", "initiator", "result"):
        if key + "_json" in result:
            result[key] = json.loads(result[key + "_json"])
    return result


class WorkStore:
    def __init__(self, store, *, initialize=False, clock=time.time, fault_hook=None):
        if type(initialize) is not bool or not callable(clock):
            raise WorkError("explicit_boolean_setup_required")
        self.store, self.pg, self.setup = store, store._is_pg, initialize
        self.clock, self.fault_hook = clock, fault_hook
        self.errors = (OSError,)
        import sqlite3

        self.errors += (sqlite3.Error,)
        if self.pg:
            import psycopg2

            self.errors += (psycopg2.Error,)
        with self.tx() as cur:
            if initialize:
                ddl = SCHEMA.replace(
                    "{SEQ}",
                    "BIGSERIAL PRIMARY KEY" if self.pg else "INTEGER PRIMARY KEY AUTOINCREMENT",
                )
                if self.pg:
                    cur.execute(ddl)
                    cur.execute(
                        "CREATE OR REPLACE FUNCTION work_v1_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'work history is retained'; END; $$"
                    )
                    for name in IMMUTABLE:
                        table = "work_v1_" + name
                        cur.execute(
                            f"DROP TRIGGER IF EXISTS work_retained ON {table}; CREATE TRIGGER work_retained BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION work_v1_immutable()"
                        )
                    fields = ",".join("NEW." + x for x in IDENTITY)
                    old = ",".join("OLD." + x for x in IDENTITY)
                    cur.execute(
                        f"CREATE OR REPLACE FUNCTION work_v1_identity() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF TG_OP='DELETE' THEN RAISE EXCEPTION 'task identity retained'; END IF; IF ROW({fields}) IS DISTINCT FROM ROW({old}) THEN RAISE EXCEPTION 'task identity immutable'; END IF; RETURN NEW; END; $$"
                    )
                    cur.execute(
                        "DROP TRIGGER IF EXISTS work_identity ON work_v1_tasks; CREATE TRIGGER work_identity BEFORE UPDATE OR DELETE ON work_v1_tasks FOR EACH ROW EXECUTE FUNCTION work_v1_identity()"
                    )
                else:
                    # executescript would implicitly commit; execute individual trusted DDL instead.
                    for statement in ddl.split(";"):
                        if statement.strip():
                            cur.execute(statement)
                    for name in IMMUTABLE:
                        for operation in ("UPDATE", "DELETE"):
                            cur.execute(
                                f"CREATE TRIGGER IF NOT EXISTS work_{name}_{operation.lower()} BEFORE {operation} ON work_v1_{name} BEGIN SELECT RAISE(ABORT,'work history retained'); END"
                            )
                    condition = " OR ".join("NEW." + x + " IS NOT OLD." + x for x in IDENTITY)
                    cur.execute(
                        f"CREATE TRIGGER IF NOT EXISTS work_identity BEFORE UPDATE ON work_v1_tasks WHEN {condition} BEGIN SELECT RAISE(ABORT,'task identity immutable'); END"
                    )
                    cur.execute(
                        "CREATE TRIGGER IF NOT EXISTS work_task_delete BEFORE DELETE ON work_v1_tasks BEGIN SELECT RAISE(ABORT,'task identity retained'); END"
                    )
            self.q(cur, "SELECT version FROM work_v1_schema WHERE id=1")
            row = cur.fetchone()
            if row is None or row[0] != 1:
                raise WorkError("unsupported_work_schema")
            for table, columns in COLUMNS.items():
                self.q(cur, f"SELECT {columns} FROM work_v1_{table} WHERE 1=0")

    def fault(self, stage):
        if self.fault_hook:
            self.fault_hook(stage)

    @contextmanager
    def tx(self):
        conn = self.store._conn
        with self.store._lock:
            cur, committing = None, False
            try:
                busy = conn.get_transaction_status() != 0 if self.pg else conn.in_transaction
                if busy:
                    raise WorkError("existing_transaction_not_owned")
                cur = conn.cursor()
                if self.pg:
                    cur.execute(
                        "SET LOCAL lock_timeout='5000ms'; SET LOCAL statement_timeout='10000ms'"
                    )
                    cur.execute("SELECT pg_advisory_xact_lock(5711232095842487861)")
                else:
                    cur.execute("BEGIN IMMEDIATE")
                yield cur
                self.fault("before_commit")
                committing = True
                conn.commit()
                self.fault("after_commit")
            except BaseException as exc:
                # Never alter a caller-owned transaction.
                if not isinstance(exc, WorkError) or str(exc) != "existing_transaction_not_owned":
                    with suppress(*self.errors):
                        conn.rollback()
                if isinstance(exc, self.errors):
                    raise WorkUnavailable(uncertain=committing) from exc
                raise
            finally:
                if cur is not None:
                    with suppress(*self.errors):
                        cur.close()

    def q(self, cur, sql, args=()):
        cur.execute(sql.replace("?", "%s") if self.pg else sql, args)
        return cur

    @staticmethod
    def rows(cur):
        names = [x[0] for x in cur.description]
        return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]

    def _get(self, cur, task_id):
        self.q(cur, "SELECT * FROM work_v1_tasks WHERE id=?", (task_id,))
        rows = self.rows(cur)
        return _view(rows[0]) if rows else None

    def get(self, task_id):
        with self.tx() as cur:
            return self._get(cur, task_id)

    def find(self, venture, routine, origin, key):
        with self.tx() as cur:
            self.q(
                cur,
                "SELECT id FROM work_v1_tasks WHERE venture=? AND routine=? AND origin=? AND occurrence_key=?",
                (venture, routine, origin, key),
            )
            row = cur.fetchone()
            return self._get(cur, row[0]) if row else None

    def list(self, venture):
        with self.tx() as cur:
            self.q(
                cur,
                "SELECT * FROM work_v1_tasks WHERE venture=? ORDER BY scheduled_utc,id LIMIT 200",
                (venture,),
            )
            return [_view(r) for r in self.rows(cur)]

    def event(self, cur, row, kind, payload=None):
        payload = payload or {}
        stamp = int(self.clock())
        self.q(
            cur,
            "INSERT INTO work_v1_history(task_id,kind,payload_json,stamp) VALUES(?,?,?,?)",
            (row["id"], kind, canonical(payload), stamp),
        )
        self.q(
            cur,
            """INSERT INTO audit(ts,run_id,venture,actor,action,decision,rule,initiator_kind,initiator_id,cost_usd,target)
            VALUES(?,?,?,?,?,?,?,?,?,0,?)""",
            (
                datetime.fromtimestamp(stamp, UTC).isoformat(),
                row["id"],
                row["venture"],
                row["initiator"].get("actor", "service:scheduler"),
                "work." + kind,
                "deny" if kind in ("blocked", "denied") else "allow",
                "work." + kind,
                row["initiator"]["kind"],
                row["initiator"]["id"],
                canonical(payload),
            ),
        )

    def status(self, cur, row, state):
        if state not in STATES:
            raise WorkError("unsupported_state")
        self.q(cur, "UPDATE work_v1_tasks SET status=? WHERE id=?", (state, row["id"]))
        legacy = {
            "review": "gated",
            "completed": "succeeded",
            "blocked": "refused",
            "uncertain": "reconciliation_required",
        }.get(state, state)
        self.q(
            cur,
            "UPDATE runs SET status=?,detail=? WHERE id=?",
            (legacy, "governed work; use work_v1 status/usage", row["id"]),
        )

    def configure(self, venture, limits):
        if self.setup is not True or set(limits) != {
            "run",
            "company_day",
            "company",
            "venture_day",
            "venture",
        }:
            raise WorkError("trusted_setup_required")
        with self.tx() as cur:
            for name, amount in limits.items():
                integer(amount)
                key = name + (":" + venture if name.startswith("venture") else "")
                self.q(cur, "SELECT cap_minor FROM work_v1_limits WHERE scope=?", (key,))
                row = cur.fetchone()
                if row and row[0] != amount:
                    raise WorkError("persisted_limit_change_requires_review")
                self.q(
                    cur,
                    "INSERT INTO work_v1_limits(scope,cap_minor) VALUES(?,?) ON CONFLICT(scope) DO NOTHING",
                    (key, amount),
                )

    def register(
        self, *, venture, routine, origin, key, when, initiator, plan, upper_minor, principal=""
    ):
        integer(upper_minor)
        if (
            origin not in {"timer", "manual", "event"}
            or not isinstance(key, str)
            or not 1 <= len(key) <= 256
            or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,95}", venture)
            or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,95}", routine)
            or set(initiator) != {"kind", "id", "actor"}
        ):
            raise WorkError("invalid_occurrence")
        when = utc(when).replace(second=0, microsecond=0).isoformat()
        if origin == "timer" and key != when:
            raise WorkError("timer_key_must_be_scheduled_utc")
        spec_digest = digest(
            {"plan": plan, "initiator": initiator, "principal": principal, "upper": upper_minor}
        )
        with self.tx() as cur:
            self.q(
                cur,
                "SELECT id,spec_digest FROM work_v1_tasks WHERE venture=? AND routine=? AND origin=? AND occurrence_key=?",
                (venture, routine, origin, key),
            )
            found = cur.fetchone()
            if found:
                if found[1] != spec_digest:
                    raise WorkError("occurrence_identity_conflict")
                return self._get(cur, found[0]), False
            task_id = "w" + uuid.uuid4().hex
            self.q(
                cur,
                """INSERT INTO work_v1_tasks(id,venture,routine,origin,occurrence_key,scheduled_utc,initiator_json,spec_digest,plan_json,principal,upper_minor,budget_day,status)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    task_id,
                    venture,
                    routine,
                    origin,
                    key,
                    when,
                    canonical(initiator),
                    spec_digest,
                    canonical(plan),
                    principal,
                    upper_minor,
                    when[:10],
                    "preparing",
                ),
            )
            self.q(
                cur,
                "INSERT INTO runs(id,routine_id,venture,started,status) VALUES(?,?,?,?,?)",
                (task_id, routine, venture, when, "preparing"),
            )
            row = self._get(cur, task_id)
            self.event(cur, row, "registered", {"origin": origin, "spec_digest": spec_digest})
            return row, True

    def _legacy(self, cur, budgets=None, evidence_digest=None):
        # Old rows do not contain an authoritative original budget snapshot.
        # Current routine prices must NEVER be silently substituted for historical liability.
        query = """SELECT r.* FROM runs r WHERE NOT EXISTS(SELECT 1 FROM work_v1_tasks w WHERE w.id=r.id)
            AND NOT EXISTS(SELECT 1 FROM work_v1_legacy l WHERE l.run_id=r.id)
            AND (r.status NOT IN ('refused','blocked','denied','preparing','gated') OR r.cost_usd<>0)"""
        if budgets is None:
            # The runtime needs only an existence check, not an unbounded buffer.
            self.q(cur, query + " LIMIT 1")
            if cur.fetchone():
                raise WorkError("legacy_liability_requires_review")
            return 0
        if (
            not self.setup
            or not isinstance(evidence_digest, str)
            or not re.fullmatch(r"[a-f0-9]{64}", evidence_digest)
        ):
            raise WorkError("legacy_liability_requires_review")
        self.q(cur, query)
        pending = self.rows(cur)  # only the explicit trusted offline importer reads this history
        for row in pending:
            if row["routine_id"] not in budgets:
                raise WorkError("legacy_liability_requires_review")
            amount = max(integer(budgets[row["routine_id"]]), minor(row["cost_usd"] or 0))
            self.q(
                cur,
                "INSERT INTO work_v1_legacy VALUES(?,?,?,?,?)",
                (row["id"], row["venture"], row["started"][:10], amount, evidence_digest),
            )
            self.event(
                cur,
                {
                    "id": row["id"],
                    "venture": row["venture"],
                    "initiator": {
                        "kind": "person",
                        "id": "reviewed-legacy-import",
                        "actor": "service:operator",
                    },
                },
                "legacy_bound_attested",
                {
                    "upper_minor": amount,
                    "evidence_digest": evidence_digest,
                    "settlement_verified": False,
                },
            )
        return len(pending)

    def import_legacy(self, bounds_minor, *, evidence_digest):
        """Owner/migration identity only; explicit attested upper bounds, not settlement."""
        if not self.setup or not isinstance(bounds_minor, dict):
            raise WorkError("trusted_legacy_import_required")
        with self.tx() as cur:
            return self._legacy(cur, bounds_minor, evidence_digest)

    def _totals(self, cur, venture, day):
        # Full-history SQL aggregation: no row window and no unbounded Python history buffer.
        self.q(
            cur,
            """SELECT
            COALESCE(SUM(w.held_minor+CASE WHEN SUBSTR(u.recognized_day,1,7)=? OR u.task_id IS NULL THEN w.spent_minor ELSE 0 END),0) AS company,
            COALESCE(SUM(w.held_minor+CASE WHEN u.recognized_day=? OR u.task_id IS NULL THEN w.spent_minor ELSE 0 END),0) AS company_day,
            COALESCE(SUM(CASE WHEN w.venture=? THEN w.held_minor+CASE WHEN SUBSTR(u.recognized_day,1,7)=? OR u.task_id IS NULL THEN w.spent_minor ELSE 0 END ELSE 0 END),0) AS venture,
            COALESCE(SUM(CASE WHEN w.venture=? THEN w.held_minor+CASE WHEN u.recognized_day=? OR u.task_id IS NULL THEN w.spent_minor ELSE 0 END ELSE 0 END),0) AS venture_day
            FROM work_v1_tasks w LEFT JOIN work_v1_usage u ON u.task_id=w.id""",
            (day[:7], day, venture, day[:7], venture, day),
        )
        total = {key: int(value) for key, value in self.rows(cur)[0].items()}
        self.q(
            cur,
            """SELECT COALESCE(SUM(upper_minor),0) AS company,
            COALESCE(SUM(CASE WHEN venture=? THEN upper_minor ELSE 0 END),0) AS venture FROM work_v1_legacy""",
            (venture,),
        )
        old = self.rows(cur)[0]
        for name in ("company", "company_day"):
            total[name] += int(old["company"])
        for name in ("venture", "venture_day"):
            total[name] += int(old["venture"])
        return total

    def totals(self, venture, day):
        with self.tx() as cur:
            self._legacy(cur)
            return self._totals(cur, venture, day)

    def reserve(self, task_id, *, review=False):
        with self.tx() as cur:
            row = self._get(cur, task_id)
            if not row or row["status"] != "preparing":
                return False
            self._legacy(cur)
            # Schedule identity is not permission to book a new reservation to an old day.
            today = datetime.fromtimestamp(self.clock(), UTC).date().isoformat()
            totals = self._totals(cur, row["venture"], today)
            self.q(cur, "SELECT * FROM work_v1_limits")
            limits = {r["scope"]: r["cap_minor"] for r in self.rows(cur)}
            failed = []
            if row["upper_minor"] > limits.get("run", -1):
                failed.append("run")
            for name, used in totals.items():
                key = name + (":" + row["venture"] if name.startswith("venture") else "")
                if used + row["upper_minor"] > limits.get(key, -1):
                    failed.append(name)
            if failed:
                self.status(cur, row, "blocked")
                self.event(cur, row, "blocked", {"code": "budget.cap", "scopes": failed})
                return False
            self.q(
                cur,
                "UPDATE work_v1_tasks SET held_minor=? WHERE id=?",
                (row["upper_minor"], task_id),
            )
            self.status(cur, row, "review" if review else "queued")
            self.event(
                cur,
                row,
                "reserved",
                {"upper_minor": row["upper_minor"], "currency": "usd", "review": review},
            )
            return True

    def reject(self, task_id, code, *, state="blocked"):
        with self.tx() as cur:
            row = self._get(cur, task_id)
            if (
                not row
                or row["attempted"]
                or row["status"] not in {"preparing", "queued", "review"}
            ):
                return False
            self.q(cur, "UPDATE work_v1_tasks SET held_minor=0 WHERE id=?", (task_id,))
            self.status(cur, row, state)
            self.event(cur, row, state, {"code": code})
            return True

    def approve(
        self,
        task_id,
        expected_digest,
        reviewer,
        *,
        ttl=900,
        reviewer_session="",
        authorize=lambda _cur, _row: True,
    ):
        if type(ttl) is not int or not 1 <= ttl <= 900:
            raise WorkError("invalid_review_ttl")
        with self.tx() as cur:
            row = self._get(cur, task_id)
            if (
                not row
                or row["status"] != "review"
                or row["spec_digest"] != expected_digest
                or not authorize(cur, row)
            ):
                return False
            self.q(
                cur,
                "UPDATE work_v1_tasks SET approval_digest=?,approval_until=?,approved_by=?,reviewer_principal=? WHERE id=?",
                (expected_digest, int(self.clock()) + ttl, reviewer, reviewer_session, task_id),
            )
            self.status(cur, row, "queued")
            self.event(cur, row, "approved", {"digest": expected_digest, "reviewer": reviewer})
            return True

    def claim(self, task_id, worker, *, lease=30):
        if (
            not isinstance(worker, str)
            or not worker
            or type(lease) is not int
            or not 1 <= lease <= 120
        ):
            raise WorkError("invalid_lease")
        with self.tx() as cur:
            row = self._get(cur, task_id)
            if not row:
                return None
            if (
                row["status"] == "running"
                and row["lease_until"] <= int(self.clock())
                and row["attempted"]
            ):
                self.status(cur, row, "uncertain")
                self.event(cur, row, "uncertain", {"code": "lease_lost_after_attempt"})
                return None
            if row["cancel_requested"] or not (
                row["status"] == "queued"
                or (
                    row["status"] == "running"
                    and not row["attempted"]
                    and row["lease_until"] <= int(self.clock())
                )
            ):
                return None
            fence = row["fence"] + 1
            self.q(
                cur,
                "UPDATE work_v1_tasks SET worker=?,fence=?,lease_until=? WHERE id=?",
                (worker, fence, int(self.clock()) + lease, task_id),
            )
            self.status(cur, row, "running")
            self.event(cur, row, "claimed", {"fence": fence, "worker": worker})
            return fence

    def before_effect(self, task_id, fence, expected_digest, *, authorize=lambda _cur, _row: True):
        with self.tx() as cur:
            row = self._get(cur, task_id)
            if (
                not row
                or row["status"] != "running"
                or row["fence"] != fence
                or row["lease_until"] <= int(self.clock())
                or row["attempted"]
                or row["cancel_requested"]
                or row["spec_digest"] != expected_digest
            ):
                return False
            if (
                row["principal"]
                and (
                    row["approval_digest"] != expected_digest
                    or row["approval_until"] <= int(self.clock())
                )
            ) or not authorize(cur, row):
                self.status(cur, row, "blocked")
                self.q(cur, "UPDATE work_v1_tasks SET held_minor=0 WHERE id=?", (task_id,))
                self.event(cur, row, "blocked", {"code": "authority_or_review_invalid"})
                return False
            self.q(cur, "UPDATE work_v1_tasks SET attempted=1 WHERE id=?", (task_id,))
            self.event(cur, row, "effect_authorized", {"fence": fence, "digest": expected_digest})
            return True

    def finish(self, task_id, fence, status, result, *, outbox=False, final_events=()):
        if (
            status not in {"completed", "failed", "cancelled", "uncertain"}
            or len(canonical(result).encode()) > 65536
        ):
            raise WorkError("invalid_result")
        with self.tx() as cur:
            row = self._get(cur, task_id)
            if (
                not row
                or row["status"] != "running"
                or row["fence"] != fence
                or not row["attempted"]
            ):
                return False
            if row["lease_until"] <= int(self.clock()):
                status = "uncertain"
            self.q(
                cur,
                "UPDATE work_v1_tasks SET result_json=? WHERE id=?",
                (canonical(result), task_id),
            )
            for event in final_events:
                self._append_event(cur, task_id, event)
            self.status(cur, row, status)
            if outbox and status == "completed":
                destination = "local-review:" + row["venture"]
                self.q(
                    cur,
                    "INSERT INTO work_v1_outbox(task_id,destination,content_json,sha256,status) VALUES(?,?,?,?,?)",
                    (task_id, destination, canonical(result), digest(result), "review"),
                )
                self.event(
                    cur,
                    row,
                    "outbox_staged",
                    {
                        "sha256": digest(result),
                        "destination": destination,
                        "external_delivery": False,
                    },
                )
            self.event(cur, row, status, {"result_digest": digest(result), "fence": fence})
            return True

    def cancel(self, task_id, actor, *, authorize=lambda _cur, _row: True):
        with self.tx() as cur:
            row = self._get(cur, task_id)
            if (
                not row
                or row["status"] not in {"preparing", "queued", "review", "running"}
                or not authorize(cur, row)
            ):
                return False
            self.q(cur, "UPDATE work_v1_tasks SET cancel_requested=1 WHERE id=?", (task_id,))
            if not row["attempted"]:
                self.q(cur, "UPDATE work_v1_tasks SET held_minor=0 WHERE id=?", (task_id,))
                self.status(cur, row, "cancelled")
            self.event(cur, row, "cancel_requested", {"actor": actor, "stop_confirmed": False})
            return True

    def reconcile(
        self,
        task_id,
        receipt_id,
        amount_minor,
        evidence_digest,
        *,
        authorize=lambda _cur, _row: True,
    ):
        integer(amount_minor)
        if (
            not re.fullmatch(r"[a-f0-9]{64}", evidence_digest)
            or not isinstance(receipt_id, str)
            or not 1 <= len(receipt_id) <= 160
        ):
            raise WorkError("invalid_usage_receipt")
        with self.tx() as cur:
            row = self._get(cur, task_id)
            if not row or not row["attempted"] or not authorize(cur, row):
                raise WorkError("no_attempt_or_authority_for_usage")
            self.q(
                cur,
                "SELECT receipt_id,amount_minor,evidence_digest FROM work_v1_usage WHERE task_id=?",
                (task_id,),
            )
            prior = cur.fetchone()
            if prior:
                if tuple(prior) != (receipt_id, amount_minor, evidence_digest):
                    raise WorkError("usage_receipt_conflict")
                return False
            # Conservative budget recognition: retain the whole upper liability in
            # EVERY window until independent final usage is accepted, then recognize
            # it in this host-observed UTC window, never a backdated schedule window.
            # This is budget accounting, not a bank/provider money-settlement date.
            recognized_day = datetime.fromtimestamp(self.clock(), UTC).date().isoformat()
            self.q(
                cur,
                "INSERT INTO work_v1_usage VALUES(?,?,?,?,?)",
                (receipt_id, task_id, amount_minor, evidence_digest, recognized_day),
            )
            self.q(
                cur,
                "UPDATE work_v1_tasks SET held_minor=0,spent_minor=? WHERE id=?",
                (amount_minor, task_id),
            )
            if amount_minor > row["upper_minor"]:
                self.status(cur, row, "uncertain")
            self.event(
                cur,
                row,
                "usage_reconciled",
                {
                    "receipt_id": receipt_id,
                    "amount_minor": amount_minor,
                    "evidence_digest": evidence_digest,
                    "over_bound": amount_minor > row["upper_minor"],
                    "recognized_day": recognized_day,
                    "basis": "independent_usage_accepted_not_money_settlement",
                },
            )
            return True

    def history(self, task_id):
        with self.tx() as cur:
            self.q(cur, "SELECT * FROM work_v1_history WHERE task_id=? ORDER BY seq", (task_id,))
            return self.rows(cur)

    def append_event(self, task_id, event):
        with self.tx() as cur:
            return self._append_event(cur, task_id, event)

    def _append_event(self, cur, task_id, event):
        from sse_protocol import validate_event

        validate_event(event, task_id)
        content = canonical(event)
        row = self._get(cur, task_id)
        if not row or not row["attempted"]:
            raise WorkError("no_authorized_stream")
        self.q(
            cur,
            "SELECT seq,digest FROM work_v1_events WHERE task_id=? ORDER BY seq DESC LIMIT 1",
            (task_id,),
        )
        previous = cur.fetchone()
        last = previous[0] if previous else 0
        if event["seq"] <= last:
            self.q(
                cur,
                "SELECT digest FROM work_v1_events WHERE task_id=? AND seq=?",
                (task_id, event["seq"]),
            )
            seen = cur.fetchone()
            if not seen or seen[0] != digest(event):
                raise WorkError("stream_replay_conflict")
            return False
        if event["seq"] != last + 1 or event["seq"] > 128:
            raise WorkError("stream_offset_gap_or_limit")
        from sse_protocol import Correlator

        correlation = Correlator(task_id)
        self.q(
            cur,
            "SELECT payload_json,digest FROM work_v1_events WHERE task_id=? ORDER BY seq",
            (task_id,),
        )
        for previous_row in self.rows(cur):
            previous_event = json.loads(previous_row["payload_json"])
            if digest(previous_event) != previous_row["digest"]:
                raise WorkError("stream_readback_mismatch")
            correlation.accept(previous_event)
        correlation.accept(event)
        self.q(
            cur,
            "INSERT INTO work_v1_events VALUES(?,?,?,?)",
            (task_id, event["seq"], content, digest(event)),
        )
        self.event(
            cur,
            row,
            "stream_event",
            {"seq": event["seq"], "type": event["type"], "event_digest": digest(event)},
        )
        return True

    def events(self, task_id, *, after=0):
        if type(after) is not int or not 0 <= after <= 1000000:
            raise WorkError("invalid_reconnect_offset")
        with self.tx() as cur:
            self.q(
                cur,
                "SELECT * FROM work_v1_events WHERE task_id=? AND seq>? ORDER BY seq LIMIT 128",
                (task_id, after),
            )
            rows = self.rows(cur)
            for row in rows:
                row["event"] = json.loads(row["payload_json"])
                if digest(row["event"]) != row["digest"]:
                    raise WorkError("stream_readback_mismatch")
            return rows
