"""Audited fixed-tool execution slice; NOT an arbitrary/hostile-code sandbox.

Reuses GatewayAdapter, Sentinel policy/audit and approval persistence. Authority
and Owner are trusted HOST capabilities, never JSON fields or authentication
substitutes. No HTTP routes, model/provider, arbitrary program or money authority.
The durable quota counts actual execution attempts, NOT dollars or earned revenue.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import selectors
import signal
import sqlite3
import stat
import subprocess
import sys
import time
import uuid
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from adapter import GatewayAdapter
from policy import Action, Decision, Effect, EgressMode, VenturePolicy, contains_secret, decide
from repository import Store

TOOLS = frozenset({"local.wordcount", "local.reviewed_wordcount"})
EVENTS = ["RUN_STARTED", "TOOL_CALL_START", "TOOL_CALL_END", "TEXT_MESSAGE_START",
          "TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END", "RUN_FINISHED"]
SCHEMA = """
CREATE TABLE IF NOT EXISTS local_jobs (
 request_id TEXT PRIMARY KEY, digest TEXT NOT NULL, identity_json TEXT NOT NULL,
 request_json TEXT NOT NULL, status TEXT NOT NULL, approval_id TEXT, pid INTEGER,
 cancel_requested INTEGER NOT NULL DEFAULT 0, result TEXT, events TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS local_quotas (
 venture TEXT PRIMARY KEY, limit_units INTEGER NOT NULL, used_units INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS local_outbox (
 request_id TEXT PRIMARY KEY, content TEXT NOT NULL, sha256 TEXT NOT NULL,
 output_path TEXT NOT NULL, status TEXT NOT NULL
);
"""


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def private_directory(path: Path) -> None:
    # Startup-owned paths, not model-supplied paths. Every delivery also uses O_NOFOLLOW.
    if any(part.is_symlink() for part in [*path.parents, path]):
        raise ValueError("symlinked operator state")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.is_dir():
        raise ValueError("operator state is not a directory")


@dataclass(frozen=True)
class Authority:
    actor: str
    venture: str
    initiator: str
    initiator_id: str

    def __post_init__(self):
        if not re.fullmatch(r"agent:[a-z0-9][a-z0-9-]{0,63}", self.actor):
            raise ValueError("invalid host actor")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", self.venture):
            raise ValueError("invalid host venture")
        if self.initiator not in {"person", "routine", "handoff", "memory", "deployment", "responsibility"}:
            raise ValueError("invalid host initiator")
        if not isinstance(self.initiator_id, str) or not 1 <= len(self.initiator_id) <= 128:
            raise ValueError("invalid host initiation identity")


@dataclass(frozen=True)
class Owner:
    """Operator-only capability. A remote adapter MUST derive this from real auth."""
    actor: str


class ChildFailure(RuntimeError):
    def __init__(self, pid: int):
        super().__init__("Fixed child did not provide trusted completion")
        self.pid = pid


class LocalExecutor:
    def __init__(self, state: Path, authority: Authority, *, capacity: int = 3, timeout_s: float = 2):
        if not sys.platform.startswith("linux"):
            raise RuntimeError("This measured local execution profile requires Linux")
        if type(capacity) is not int or not 1 <= capacity <= 10000:
            raise ValueError("invalid quota")
        if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or not 0.05 <= timeout_s <= 5:
            raise ValueError("invalid host deadline")
        self.state, self.authority, self.timeout_s = Path(state).absolute(), authority, timeout_s
        self.identity = canonical(asdict(authority))
        private_directory(self.state)
        private_directory(self.state / "outputs")
        for name in ("sentinel.sqlite3", "execution.sqlite3"):
            if (self.state / name).is_symlink():
                raise ValueError("symlinked operator database")
        self.audit = Store(str(self.state / "sentinel.sqlite3"))
        try:
            with closing(sqlite3.connect(self.state / "execution.sqlite3")) as db:
                db.executescript(SCHEMA)
                db.commit()
            with self._transaction() as db:
                row = db.execute("SELECT limit_units FROM local_quotas WHERE venture=?", (authority.venture,)).fetchone()
                if row and row[0] != capacity:
                    raise ValueError("persisted quota cannot be silently changed")
                db.execute("INSERT OR IGNORE INTO local_quotas(venture,limit_units) VALUES (?,?)", (authority.venture, capacity))
        except Exception:
            self.close()
            raise

    def close(self):
        # Existing Store still lacks a public lifecycle API; do not modify its financial tables.
        self.audit._conn.close()

    @contextmanager
    def _transaction(self):
        with closing(sqlite3.connect(self.state / "execution.sqlite3", timeout=5)) as db:
            db.row_factory = sqlite3.Row
            try:
                db.execute("BEGIN IMMEDIATE")
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    def job(self, rid: str):
        with self._transaction() as db:
            row = db.execute("SELECT * FROM local_jobs WHERE request_id=?", (rid,)).fetchone()
            return dict(row) if row else None

    def quota(self):
        with self._transaction() as db:
            return dict(db.execute("SELECT * FROM local_quotas WHERE venture=?", (self.authority.venture,)).fetchone())

    def outbox_count(self, rid: str) -> int:
        with self._transaction() as db:
            return db.execute("SELECT count(*) FROM local_outbox WHERE request_id=?", (rid,)).fetchone()[0]

    def _update(self, rid, **fields):
        with self._transaction() as db:
            db.execute("UPDATE local_jobs SET " + ",".join(key + "=?" for key in fields) + " WHERE request_id=?", (*fields.values(), rid))

    def _audit(self, rid, action, decision, rule, **target):
        seq = self.audit.audit({"run_id": rid, "venture": self.authority.venture,
                                "actor": self.authority.actor, "initiator": {"kind": self.authority.initiator, "id": self.authority.initiator_id},
                                "action": action, "decision": decision, "rule": rule,
                                "cost_usd": 0, "target": target})
        if type(seq) is not int or seq <= 0:
            raise sqlite3.OperationalError("audit persistence not confirmed")
        return seq

    def _refuse(self, rid, code, *, executed=False):
        try:
            self._audit(rid, "local.request.refused", "deny", code)
        except (sqlite3.Error, OSError):
            code = "audit_unavailable"
        return {"ok": False, "executed": executed, "replayed": False, "status": "refused", "code": code}

    def _request(self, body):
        if not isinstance(body, dict) or set(body) != {"request_id", "tool", "arguments"}:
            raise ValueError("exact request fields required")
        rid = body["request_id"]
        if not isinstance(rid, str) or str(uuid.UUID(rid)) != rid or body["tool"] not in TOOLS:
            raise ValueError("unsupported identity or tool")
        args = body["arguments"]
        if not isinstance(args, dict) or set(args) != {"text", "output", "delay_ms"}:
            raise ValueError("exact tool arguments required")
        text, name, delay = args["text"], args["output"], args["delay_ms"]
        if not isinstance(text, str) or len(text.encode()) > 8192 or contains_secret(text):
            raise ValueError("unsafe or oversized text")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,40}\.json", name):
            raise ValueError("only a scoped JSON filename is accepted")
        if type(delay) is not int or not 0 <= delay <= 3000:
            raise ValueError("invalid bounded fixture delay")
        # Copy all values; mutating the caller's input later cannot change the approved draft.
        return {"request_id": rid, "tool": body["tool"], "arguments": {"text": text, "output": name, "delay_ms": delay}}

    def _request_digest(self, body):
        source = Path(__file__)
        implementation = {name: digest(path.read_bytes()) for name, path in {
            "executor": source, "worker": source.with_name("local_tool_worker.py"),
            "adapter": source.with_name("adapter.py"), "mapper": source.with_name("mapper.py"),
            "policy": source.parents[2] / "sentinel/policy.py", "repository": source.parents[2] / "sentinel/repository.py",
        }.items()}
        return digest(canonical({"identity": self.identity, "request": body, "implementation_sha256": implementation}).encode())

    def _target(self, body):
        return self.state / "outputs" / self.authority.venture / body["request_id"] / body["arguments"]["output"]

    def _govern(self, body, request_digest, *, approved=False):
        def decision(action):
            verdict = decide(Action(**action), VenturePolicy(slug=self.authority.venture,
                              egress_mode=EgressMode.DENY_ALL,
                              allowed_write_roots=(str(self.state / "outputs" / self.authority.venture),)))
            if not isinstance(verdict, Decision) or not isinstance(verdict.effect, Effect):
                verdict = Decision(Effect.DENY, "local.malformed_verdict", "no trusted allow")
            if verdict.effect is Effect.ALLOW and body["tool"] == "local.reviewed_wordcount" and not approved:
                verdict = Decision(Effect.GATE, "local.review_before_save", "Host owner must review this exact draft")
            self._audit(body["request_id"], "file.write", verdict.effect.value, verdict.rule,
                        request_digest=request_digest, output_path=str(self._target(body)))
            return {"effect": verdict.effect.value, "run_id": body["request_id"], "rule": verdict.rule}
        return GatewayAdapter(decision).intercept("file.write", {"path": str(self._target(body)), "content": body["arguments"]["text"]},
                    bot_id=self.authority.actor.removeprefix("agent:"), venture=self.authority.venture,
                    initiator=self.authority.initiator, initiator_id=self.authority.initiator_id)

    def _approval(self, row):
        approval = self.audit.get_approval(row["approval_id"]) if row["approval_id"] else None
        expected_action = {"request_digest": row["digest"], "request": json.loads(row["request_json"]),
                           "authority": json.loads(row["identity_json"])}
        if not approval or approval["run_id"] != row["request_id"] or approval["venture"] != self.authority.venture or approval["action"] != expected_action:
            return None
        try:
            age = time.time() - datetime.fromisoformat(approval["created"].replace("Z", "+00:00")).timestamp()
        except (ValueError, TypeError):
            return None
        return approval if 0 <= age <= 900 else None

    def resolve(self, rid, expected_digest, verdict, *, owner: Owner) -> bool:
        """Trusted host-owner entry; NEVER expose owner.actor as a JSON credential."""
        row = self.job(rid)
        if not isinstance(owner, Owner) or owner.actor != "human:owner" or verdict not in {"approved", "denied"}:
            return False
        if not row or row["identity_json"] != self.identity or row["status"] != "gated" or row["digest"] != expected_digest:
            return False
        if self._request_digest(json.loads(row["request_json"])) != expected_digest:
            return False
        approval = self._approval(row)
        if not approval or approval["status"] != "pending":
            return False
        self._audit(rid, "local.approval.resolve", "allow", "local.host_owner", request_digest=expected_digest, reviewer=owner.actor, verdict=verdict)
        return self.audit.resolve_approval(row["approval_id"], verdict, owner.actor)

    def _gated(self, row):
        return {"ok": False, "executed": False, "replayed": False, "status": "gated", "code": "approval_required",
                "approval_id": row["approval_id"], "request_digest": row["digest"], "request": json.loads(row["request_json"])}

    def _claim(self, rid):
        with self._transaction() as db:
            row = db.execute("SELECT status FROM local_jobs WHERE request_id=?", (rid,)).fetchone()
            if row[0] not in {"preparing", "gated"}:
                return "reconciliation_required"
            quota = db.execute("UPDATE local_quotas SET used_units=used_units+1 WHERE venture=? AND used_units<limit_units", (self.authority.venture,))
            if quota.rowcount != 1:
                db.execute("UPDATE local_jobs SET status='refused',error='quota_exhausted' WHERE request_id=?", (rid,))
                return "quota_exhausted"
            db.execute("UPDATE local_jobs SET status='running' WHERE request_id=?", (rid,))
        return None

    def cancel(self, rid):
        row = self.job(rid)
        if not row or row["identity_json"] != self.identity or row["status"] != "running":
            return self._refuse(rid, "not_active_owned_job")
        self._audit(rid, "local.cancel.request", "allow", "local.host_cancel")
        self._update(rid, cancel_requested=1)
        # A request is not a kill receipt. execute() confirms actual process exit.
        return {"ok": True, "status": "cancel_requested"}

    @staticmethod
    def _terminate(process):
        try:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            # A simultaneous normal exit is still an exit; confirm it with wait().
            pass
        process.wait(timeout=2)

    def _child(self, body):
        rid = body["request_id"]
        command = [sys.executable, "-I", "-S", str(Path(__file__).with_name("local_tool_worker.py")), str(os.getpid())]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    cwd=self._target(body).parent, start_new_session=True,
                    env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"})
        try:
            self._update(rid, pid=process.pid)
            process.stdin.write(canonical({"request_id": rid, "text": body["arguments"]["text"], "delay_ms": body["arguments"]["delay_ms"]}).encode())
            process.stdin.close()
            events, pending, total = [], b"", 0
            deadline = time.monotonic() + self.timeout_s
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    cancelled = self.job(rid)["cancel_requested"]
                    if cancelled or time.monotonic() >= deadline:
                        self._terminate(process)
                        return {"terminal": "cancelled" if cancelled else "timed_out", "pid": process.pid, "child_exit_confirmed": True}
                    ready = selector.select(0.03)
                    if not ready:
                        continue
                    chunk = os.read(process.stdout.fileno(), 4096)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > 65536:
                        raise ValueError("stream limit")
                    pending += chunk
                    while b"\n\n" in pending:
                        frame, pending = pending.split(b"\n\n", 1)
                        if not frame.startswith(b"data: "):
                            raise ValueError("not SSE data")
                        event = json.loads(frame[6:])
                        if not isinstance(event, dict) or event.get("runId") != rid or len(events) >= len(EVENTS) or event.get("type") != EVENTS[len(events)]:
                            raise ValueError("uncorrelated/incomplete event stream")
                        if event["type"] in {"TOOL_CALL_START", "TOOL_CALL_END"} and event.get("toolCallId") != rid + ":count":
                            raise ValueError("uncorrelated tool call")
                        if event["type"].startswith("TEXT_MESSAGE_") and event.get("messageId") != rid + ":output":
                            raise ValueError("uncorrelated output message")
                        events.append(event)
                        self._update(rid, events=canonical(events))
            process.wait(timeout=1)
            if process.returncode != 0 or pending or [e["type"] for e in events] != EVENTS:
                raise ValueError("no complete worker stream")
            result = json.loads(events[4]["delta"])
            if result != {"words": len(body["arguments"]["text"].split()), "characters": len(body["arguments"]["text"]), "worker_pid": process.pid, "minimal_environment": True}:
                raise ValueError("untrusted tool result")
            return {"result": result, "events": events, "pid": process.pid}
        except Exception as exc:
            raise ChildFailure(process.pid) from exc
        finally:
            self._terminate(process)
            process.stdout.close()
            if not process.stdin.closed:
                process.stdin.close()

    def _completion_exists(self, rid, request_digest, sha256, action, *, events_sha256=None):
        return any(row["action"] == action and row["decision"] == "allow" and
                   row["target"].get("request_digest") == request_digest and row["target"].get("sha256") == sha256 and
                   (events_sha256 is None or row["target"].get("events_sha256") == events_sha256)
                   for row in self.audit.audit_tail(1, run_id=rid, action=action))

    @staticmethod
    def _read_output(path):
        if any(part.is_symlink() for part in [*path.parents, path]):
            raise ValueError("symlinked output component")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 65536:
                raise ValueError("not a bounded regular output")
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError("oversized output")
        return raw

    def _deliver(self, row, *, replayed, executed):
        rid = row["request_id"]
        with self._transaction() as db:
            outbox = dict(db.execute("SELECT * FROM local_outbox WHERE request_id=?", (rid,)).fetchone())
        body = json.loads(row["request_json"])
        target = self._target(body)
        # Stored routing data is evidence, not authority. Bind to the request's
        # canonical relative destination so a restore can never write to an old host path.
        expected_relative = target.relative_to(self.state).as_posix()
        if outbox["output_path"] != expected_relative:
            return self._refuse(rid, "reconciliation_required", executed=executed)
        raw = outbox["content"].encode()
        result, events = json.loads(row["result"]), json.loads(row["events"])
        if json.loads(raw) != {"request_id": rid, "result": result} or digest(raw) != outbox["sha256"] or not self._completion_exists(
                rid, row["digest"], outbox["sha256"], "local.execution.complete", events_sha256=digest(canonical(events).encode())):
            return self._refuse(rid, "reconciliation_required", executed=executed)
        if row["status"] == "delivered":
            if digest(self._read_output(target)) != outbox["sha256"] or not self._completion_exists(rid, row["digest"], outbox["sha256"], "local.delivery.complete"):
                return self._refuse(rid, "reconciliation_required", executed=executed)
        else:
            body = json.loads(row["request_json"])
            approved = body["tool"] != "local.reviewed_wordcount" or bool((self._approval(row) or {}).get("status") == "approved")
            if not approved or self._govern(body, row["digest"], approved=approved)["status"] != "allowed":
                return self._refuse(rid, "delivery_not_authorized", executed=executed)
            private_directory(target.parent)
            directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                try:
                    fd = os.open(target.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
                except FileExistsError:
                    if self._read_output(target) != raw:
                        return self._refuse(rid, "reconciliation_required", executed=executed)
                else:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(raw)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.fsync(directory)
            finally:
                os.close(directory)
            self._audit(rid, "local.delivery.complete", "allow", "local.outbox_delivered", request_digest=row["digest"], sha256=outbox["sha256"])
            with self._transaction() as db:
                db.execute("UPDATE local_outbox SET status='delivered' WHERE request_id=?", (rid,))
                db.execute("UPDATE local_jobs SET status='delivered' WHERE request_id=?", (rid,))
        return {"ok": True, "executed": executed, "replayed": replayed, "status": "delivered", "request_id": rid,
                "result": json.loads(row["result"]), "events": json.loads(row["events"]),
                "output_path": str(target), "output_sha256": outbox["sha256"], "cost_usd": 0, "providers_enabled": False}

    def execute(self, request):
        try:
            body = self._request(request)
            request_digest = self._request_digest(body)
        except (ValueError, TypeError, KeyError, OSError):
            return self._refuse("invalid_" + uuid.uuid4().hex, "invalid_request")
        rid, started = body["request_id"], False
        try:
            with self._transaction() as db:
                row = db.execute("SELECT * FROM local_jobs WHERE request_id=?", (rid,)).fetchone()
                if row:
                    row = dict(row)
                    fresh = False
                else:
                    db.execute("INSERT INTO local_jobs(request_id,digest,identity_json,request_json,status) VALUES (?,?,?,?,?)", (rid, request_digest, self.identity, canonical(body), "preparing"))
                    fresh = True
            row = self.job(rid)
            if row["digest"] != request_digest or row["identity_json"] != self.identity or json.loads(row["request_json"]) != body:
                return self._refuse(rid, "request_conflict")
            if row["status"] in {"produced", "delivery_pending", "delivered"}:
                return self._deliver(row, replayed=True, executed=False)
            approved = False
            if not fresh:
                if row["status"] != "gated":
                    return self._refuse(rid, row["error"] or "reconciliation_required")
                approval = self._approval(row)
                if not approval or approval["status"] in {"denied", "expired"}:
                    return self._refuse(rid, "approval_not_valid")
                if approval["status"] == "pending":
                    return self._gated(row)
                approved = approval["status"] == "approved"
            governance = self._govern(body, request_digest, approved=approved)
            if governance["status"] == "gated" and fresh:
                approval = self.audit.create_approval({"run_id": rid, "venture": self.authority.venture,
                    "rule": "local.review_before_save", "reason": "Exact local draft/authority/implementation review; no external action",
                    "action": {"request_digest": request_digest, "request": body, "authority": asdict(self.authority)}})
                self._update(rid, status="gated", approval_id=approval["id"])
                return self._gated(self.job(rid))
            if governance["status"] != "allowed":
                self._update(rid, status="refused", error="policy_not_allowed")
                return self._refuse(rid, "policy_not_allowed")
            target = self._target(body)
            private_directory(target.parent)
            if target.exists() or target.is_symlink():
                self._update(rid, status="refused", error="unexpected_existing_output")
                return self._refuse(rid, "unexpected_existing_output")
            error = self._claim(rid)
            if error:
                return self._refuse(rid, error)
            self._audit(rid, "local.execution.start", "allow", "local.quota_reserved", request_digest=request_digest, reserved_units=1)
            if self._request_digest(body) != request_digest:
                raise ValueError("implementation changed before launch")
            child = self._child(body)
            started = True
            if child.get("terminal"):
                self._audit(rid, "local.execution.stop", "deny", "local." + child["terminal"], pid=child["pid"], child_exit_confirmed=True)
                self._update(rid, status=child["terminal"], error=child["terminal"])
                return {"ok": False, "executed": True, "replayed": False, "status": child["terminal"], "code": child["terminal"], "pid": child["pid"], "child_exit_confirmed": True}
            content = canonical({"request_id": rid, "result": child["result"]}) + "\n"
            sha256 = digest(content.encode())
            self._audit(rid, "local.execution.complete", "allow", "local.observed_sse_completion", request_digest=request_digest,
                        sha256=sha256, events_sha256=digest(canonical(child["events"]).encode()), pid=child["pid"])
            with self._transaction() as db:
                db.execute("INSERT INTO local_outbox VALUES (?,?,?,?,?)", (rid, content, sha256, target.relative_to(self.state).as_posix(), "pending"))
                db.execute("UPDATE local_jobs SET status='delivery_pending',result=?,events=? WHERE request_id=?", (canonical(child["result"]), canonical(child["events"]), rid))
            return self._deliver(self.job(rid), replayed=False, executed=True)
        except ChildFailure as exc:
            self._update(rid, status="uncertain", pid=exc.pid, error="reconciliation_required")
            return self._refuse(rid, "reconciliation_required", executed=True)
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError):
            row = self.job(rid)
            if row["status"] not in {"delivery_pending", "delivered"}:
                self._update(rid, status="uncertain", error="reconciliation_required")
            return self._refuse(rid, "reconciliation_required", executed=started)
