"""S07 first-party catalog, consented untrusted quotes and review-only candidates.

All authority/config files are host-owned and excluded from evaluated namespaces.
No training, scraping, arbitrary plugin loader or automatic code deployment exists.
SQLite fixtures are local-only; production DB-role/storage/key review is external.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from policy import contains_secret
from trust_crypto import TrustError, canonical, digest, verify


class GovernanceError(ValueError):
    pass


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_:-]{0,95}", value):
        raise GovernanceError("scoped_identity_required")
    return value


def file_sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


class ToolCatalog:
    FIXED = {"owned.qa": frozenset({"owned-sample-read", "local-artifact-write"})}

    def __init__(
        self, root, lock, expected_sha, authority, trusted, *, minimum_epoch=1, clock=time.time
    ):
        self.root, self.lock, self.authority = Path(root), Path(lock), Path(authority)
        self.expected_sha, self.trusted = expected_sha, trusted
        self.epoch, self.authority_digest, self.clock = minimum_epoch, None, clock

    def resolve(self, tool, venture, *, capabilities=None):
        identifier(venture)
        try:
            if self.lock.is_symlink() or file_sha(self.lock) != self.expected_sha:
                raise GovernanceError("catalog_changed")
            lock = json.loads(self.lock.read_text())
            envelope = json.loads(self.authority.read_text())
            authority = verify(envelope, self.trusted, "catalog-admin")
            now = int(self.clock())
            if (
                set(authority) != {"schema", "epoch", "not_before", "expires", "revoked", "grants"}
                or authority["schema"] != "openbot.tool-authority/1"
                or type(authority["epoch"]) is not int
                or authority["epoch"] < self.epoch
                or not authority["not_before"] <= now < authority["expires"]
                or not isinstance(authority["revoked"], list)
                or not isinstance(authority["grants"], dict)
            ):
                raise GovernanceError("current_catalog_authority_required")
            authority_digest = digest(authority)
            if (
                authority["epoch"] == self.epoch
                and self.authority_digest is not None
                and authority_digest != self.authority_digest
            ):
                raise GovernanceError("conflicting_authority_epoch")
            self.epoch, self.authority_digest = authority["epoch"], authority_digest
            entry = lock["tools"][tool]
            expected = self.FIXED[tool]
            if (
                lock["schema"] != "openbot.first-party-tools/1"
                or set(entry) != {"version", "source", "license", "capabilities", "origin"}
                or entry["origin"] != "first-party"
                or not re.fullmatch(r"\d+\.\d+\.\d+", entry["version"])
                or frozenset(entry["capabilities"]) != expected
                or len(entry["capabilities"]) != len(expected)
                or (capabilities is not None and not set(capabilities) <= expected)
                or tool in authority["revoked"]
                or tool not in authority["grants"].get(venture, [])
            ):
                raise GovernanceError("tool_scope_or_revocation")
            for item in [*entry["source"], entry["license"]]:
                relative = PurePosixPath(item["path"])
                if relative.is_absolute() or ".." in relative.parts:
                    raise GovernanceError("catalog_path_refused")
                path = self.root.joinpath(*relative.parts)
                if (
                    any(p.is_symlink() for p in (path, *path.parents))
                    or file_sha(path) != item["sha256"]
                ):
                    raise GovernanceError("tool_source_changed")
            return {
                "tool": tool,
                **json.loads(canonical(entry)),
                "resolution_digest": digest(
                    {"lock": self.expected_sha, "authority": authority_digest}
                ),
                "execution_kind": "fixed-owned-only",
            }
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise GovernanceError("trusted_tool_reresolution_required") from exc


@dataclass(frozen=True)
class MemoryIdentity:
    client: str
    subject: str
    scope: str

    def key(self):
        return tuple(identifier(v) for v in (self.client, self.subject, self.scope))


class ConsentedMemory:
    RETENTION_SECONDS = 7 * 86400

    def __init__(self, path, deletion_authority, *, host_admin=False, clock=time.time):
        self.path, self.authority = Path(path), Path(deletion_authority)
        self.host_admin, self.clock = host_admin, clock
        for path in (self.path, self.authority):
            if path.is_symlink():
                raise GovernanceError("private_memory_storage_required")
        if host_admin:
            with self.connection() as conn:
                conn.executescript("""
                 CREATE TABLE IF NOT EXISTS consents(id TEXT PRIMARY KEY,client TEXT,subject TEXT,scope TEXT,
                   purpose TEXT,source TEXT,consent_ref TEXT,created INTEGER,expires INTEGER,revoked INTEGER);
                 CREATE TABLE IF NOT EXISTS quotes(id TEXT PRIMARY KEY,consent TEXT,text TEXT,
                   artifact TEXT,created INTEGER,expires INTEGER);
                 CREATE TABLE IF NOT EXISTS backup_meta(created INTEGER,expires INTEGER);
                """)
            with self.authority_connection() as conn:
                conn.executescript("""
                 CREATE TABLE IF NOT EXISTS tombstones(client TEXT,subject TEXT,scope TEXT,deleted INTEGER);
                 CREATE TABLE IF NOT EXISTS backups(path TEXT PRIMARY KEY,sha TEXT,created INTEGER,expires INTEGER);
                """)

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA secure_delete=ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @contextmanager
    def authority_connection(self):
        # This journal must NOT be rolled back with a content snapshot.
        conn = sqlite3.connect(self.authority)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def admin(self):
        if self.host_admin is not True:
            raise GovernanceError("protected_host_authority_required")

    def grant(self, identity, *, purpose, source, consent_ref, expires, human):
        self.admin()
        key = identity.key()
        identifier(purpose)
        now = int(self.clock())
        if (
            not isinstance(human, str)
            or not human.startswith("human:")
            or type(expires) is not int
            or not now < expires <= now + 30 * 86400
            or not isinstance(source, str)
            or not source.startswith("owned:")
            or len(source) > 128
            or not isinstance(consent_ref, str)
            or not consent_ref.startswith("consent:")
            or len(consent_ref) > 128
        ):
            raise GovernanceError("explicit_scoped_expiring_consent_required")
        consent = str(uuid.uuid4())
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO consents VALUES(?,?,?,?,?,?,?,?,?,0)",
                (consent, *key, purpose, source, consent_ref, now, expires),
            )
        return consent

    def _consent(self, conn, identity, consent, purpose):
        row = conn.execute(
            "SELECT * FROM consents WHERE id=? AND client=? AND subject=? AND scope=? AND purpose=?",
            (consent, *identity.key(), identifier(purpose)),
        ).fetchone()
        if not row or row["revoked"] or row["expires"] <= int(self.clock()):
            raise GovernanceError("current_scoped_consent_required")
        return row

    def add(self, identity, consent, *, purpose, text, artifact_sha256, expires):
        if (
            not isinstance(text, str)
            or not 1 <= len(text.encode()) <= 2048
            or contains_secret(text)
            or any(ord(c) < 32 and c not in "\n\t" for c in text)
            or re.search(
                r"(?i)ignore (all |previous |prior )?(instructions|polic)|system\s*prompt|grant (owner|admin)|disable (safety|budget)|self.promot",
                text,
            )
            or not re.fullmatch("[a-f0-9]{64}", artifact_sha256 or "")
        ):
            raise GovernanceError("unsafe_or_unproven_feedback")
        with self.connection() as conn:
            row = self._consent(conn, identity, consent, purpose)
            now = int(self.clock())
            if type(expires) is not int or not now < expires <= row["expires"]:
                raise GovernanceError("feedback_expiry_exceeds_consent")
            quote_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO quotes VALUES(?,?,?,?,?,?)",
                (quote_id, consent, text, artifact_sha256, now, expires),
            )
        return quote_id

    def quote(self, identity, *, purpose):
        now = int(self.clock())
        with self.connection() as conn:
            self._replay_deletions(conn)
            conn.execute(
                "DELETE FROM quotes WHERE expires<=? OR consent IN (SELECT id FROM consents WHERE revoked=1 OR expires<=?)",
                (now, now),
            )
            rows = conn.execute(
                """SELECT q.*,c.source,c.consent_ref FROM quotes q JOIN consents c ON c.id=q.consent
                WHERE c.client=? AND c.subject=? AND c.scope=? AND c.purpose=? AND c.revoked=0 AND c.expires>?
                ORDER BY q.created,q.id LIMIT 32""",
                (*identity.key(), identifier(purpose), now),
            ).fetchall()
        return [
            {
                "kind": "untrusted_quote",
                "authority": False,
                "training_use": False,
                "id": r["id"],
                "text": r["text"],
                "artifact_sha256": r["artifact"],
                "source": r["source"],
                "consent_ref": r["consent_ref"],
                "expires": r["expires"],
            }
            for r in rows
        ]

    def _replay_deletions(self, conn):
        with self.authority_connection() as journal:
            for row in journal.execute("SELECT * FROM tombstones ORDER BY deleted"):
                args = (row["client"], row["subject"], row["scope"], row["deleted"])
                conn.execute(
                    "DELETE FROM quotes WHERE consent IN (SELECT id FROM consents WHERE client=? AND subject=? AND scope=? AND created<=?)",
                    args,
                )
                conn.execute(
                    "UPDATE consents SET revoked=1 WHERE client=? AND subject=? AND scope=? AND created<=?",
                    args,
                )

    def delete(self, identity):
        self.admin()
        # Tombstone commits FIRST: a crash cannot resurrect an older content backup.
        with self.authority_connection() as conn:
            conn.execute(
                "INSERT INTO tombstones VALUES(?,?,?,?)", (*identity.key(), int(self.clock()))
            )
        with self.connection() as conn:
            self._replay_deletions(conn)
        return {
            "deleted": True,
            "backup_retention_max_seconds": self.RETENTION_SECONDS,
            "physical_media_erasure_certified": False,
        }

    def revoke(self, identity):
        return self.delete(identity)

    def backup(self, target):
        self.admin()
        target = Path(target).absolute()
        if target.exists() or target.is_symlink():
            raise GovernanceError("new_snapshot_target_required")
        now = int(self.clock())
        with self.connection() as conn:
            self._replay_deletions(conn)
            conn.execute("DELETE FROM backup_meta")
            conn.execute("INSERT INTO backup_meta VALUES(?,?)", (now, now + self.RETENTION_SECONDS))
        dest = sqlite3.connect(target)
        try:
            with self.connection() as conn:
                conn.backup(dest)
        finally:
            dest.close()
        with self.authority_connection() as journal:
            journal.execute(
                "INSERT INTO backups VALUES(?,?,?,?)",
                (str(target), file_sha(target), now, now + self.RETENTION_SECONDS),
            )
        return target

    def restore(self, source):
        self.admin()
        source = Path(source).absolute()
        with self.authority_connection() as journal:
            row = journal.execute("SELECT * FROM backups WHERE path=?", (str(source),)).fetchone()
        if (
            not row
            or row["expires"] <= int(self.clock())
            or source.is_symlink()
            or file_sha(source) != row["sha"]
        ):
            raise GovernanceError("current_verified_snapshot_required")
        # Trusted maintenance only; callers stop the local service before restoring.
        shutil.copyfile(source, self.path)
        with self.connection() as conn:
            self._replay_deletions(conn)
        return {"restored": True, "deletions_replayed": True}

    def sweep_backups(self):
        self.admin()
        removed = []
        with self.authority_connection() as journal:
            rows = journal.execute(
                "SELECT * FROM backups WHERE expires<=?", (int(self.clock()),)
            ).fetchall()
            for row in rows:
                path = Path(row["path"])
                if path.is_symlink():
                    raise GovernanceError("snapshot_symlink_refused")
                path.unlink(missing_ok=True)
                journal.execute("DELETE FROM backups WHERE path=?", (row["path"],))
                removed.append(str(path))
        return removed


class CandidateGate:
    """Records signed review stages; never edits source or deploys a candidate."""

    STAGES = {
        "isolated_tests": ("proposed", "tested", "test-runner"),
        "protected_evaluation": ("tested", "evaluated", "evaluator"),
        "human_review": ("evaluated", "reviewed", "qualified-reviewer"),
        "canary": ("reviewed", "canary", "operator"),
        "promote": ("canary", "eligible", "release-owner"),
    }

    def __init__(self, path, *, source_digest, policy, trusted, clock=time.time):
        self.path, self.source_digest = Path(path), source_digest
        self.policy = json.loads(canonical(policy))
        self.policy_digest, self.trusted, self.clock = digest(policy), trusted, clock
        if (
            set(policy) != {"protected_suite_sha256", "min_cases", "canary_seconds", "environment"}
            or not re.fullmatch("[a-f0-9]{64}", policy["protected_suite_sha256"])
            or type(policy["min_cases"]) is not int
            or policy["min_cases"] < 20
            or type(policy["canary_seconds"]) is not int
            or policy["canary_seconds"] < 3600
        ):
            raise GovernanceError("protected_evaluation_policy_required")
        with sqlite3.connect(self.path) as conn:
            conn.executescript("""CREATE TABLE IF NOT EXISTS candidates(id TEXT PRIMARY KEY,body TEXT,state TEXT,changed INTEGER);
              CREATE TABLE IF NOT EXISTS reviews(candidate TEXT,kind TEXT,envelope TEXT,PRIMARY KEY(candidate,kind));""")

    def propose(self, files, *, reproducer, base_sha256):
        if (
            base_sha256 != self.source_digest
            or not isinstance(files, dict)
            or not 1 <= len(files) <= 4
            or not isinstance(reproducer, dict)
            or set(reproducer) != {"artifact_sha256", "steps"}
            or not re.fullmatch("[a-f0-9]{64}", reproducer["artifact_sha256"])
            or not isinstance(reproducer["steps"], str)
            or not 1 <= len(reproducer["steps"]) <= 2048
        ):
            raise GovernanceError("bound_reproducer_required")
        for name, content in files.items():
            path = PurePosixPath(name)
            if (
                not isinstance(name, str)
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in name
                or str(path) != name
                or not (
                    re.fullmatch(r"skills/first_party/[a-z][a-z0-9_]{0,40}\.py", name)
                    or name == "prompts/owned_qa.txt"
                )
                or not isinstance(content, str)
                or len(content.encode()) > 32768
                or contains_secret(content)
            ):
                raise GovernanceError("protected_authority_or_path_refused")
        body = {
            "files": files,
            "reproducer": reproducer,
            "base_sha256": base_sha256,
            "policy_digest": self.policy_digest,
            "training": False,
        }
        identity = digest(body)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO candidates VALUES(?,?,?,?)",
                (identity, canonical(body).decode(), "proposed", int(self.clock())),
            )
        return identity

    def status(self, identity):
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT state FROM candidates WHERE id=?", (identity,)).fetchone()
        if not row:
            raise GovernanceError("candidate_not_found")
        return {
            "candidate": identity,
            "state": row[0],
            "automatic_deployment": False,
            "performance_improvement_proven": False,
            "environment": self.policy["environment"],
        }

    def attach(self, identity, kind, envelope):
        if kind not in self.STAGES and kind != "rollback":
            raise GovernanceError("review_stage_required")
        role = "operator" if kind == "rollback" else self.STAGES[kind][2]
        try:
            receipt = verify(envelope, self.trusted, role)
            required = {
                "schema",
                "kind",
                "candidate",
                "policy_digest",
                "issued",
                "expires",
                "evidence_sha256",
                "result",
                "metrics",
            }
            now = int(self.clock())
            if (
                set(receipt) != required
                or receipt["schema"] != "openbot.candidate-review/1"
                or receipt["kind"] != kind
                or receipt["candidate"] != identity
                or receipt["policy_digest"] != self.policy_digest
                or type(receipt["issued"]) is not int
                or type(receipt["expires"]) is not int
                or not receipt["issued"] <= now < receipt["expires"] <= receipt["issued"] + 86400
                or receipt["result"] != "pass"
                or not re.fullmatch("[a-f0-9]{64}", receipt["evidence_sha256"])
            ):
                raise GovernanceError("current_bound_review_required")
            m = receipt["metrics"]
            if kind == "isolated_tests" and (
                set(m) != {"passed", "failed", "isolated"}
                or type(m["passed"]) is not int
                or m["passed"] < 1
                or m["failed"] != 0
                or m["isolated"] is not True
            ):
                raise GovernanceError("isolated_test_evidence_required")
            if kind == "protected_evaluation" and (
                set(m) != {"passed", "failed", "unsafe", "suite_sha256"}
                or type(m["passed"]) is not int
                or m["passed"] < self.policy["min_cases"]
                or m["failed"] != 0
                or m["unsafe"] != 0
                or m["suite_sha256"] != self.policy["protected_suite_sha256"]
            ):
                raise GovernanceError("protected_evaluation_evidence_required")
            if kind == "human_review":
                signer = self.trusted[envelope["key_id"]]
                if (
                    m != {"approved": True}
                    or signer.get("human") is not True
                    or not signer.get("qualification")
                ):
                    raise GovernanceError("qualified_human_review_required")
            if kind in {"canary", "promote", "rollback"} and m != {"approved": True}:
                raise GovernanceError("explicit_operator_decision_required")
            with sqlite3.connect(self.path, isolation_level=None) as conn:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT state,changed,body FROM candidates WHERE id=?", (identity,)
                ).fetchone()
                if (
                    not row
                    or json.loads(row[2])["policy_digest"] != self.policy_digest
                    or json.loads(row[2])["base_sha256"] != self.source_digest
                ):
                    raise GovernanceError("bound_candidate_required")
                before, after = (
                    ("canary", "rolled_back") if kind == "rollback" else self.STAGES[kind][:2]
                )
                if row[0] != before and not (kind == "rollback" and row[0] == "eligible"):
                    raise GovernanceError("review_order_or_replay_refused")
                if kind == "promote" and now - row[1] < self.policy["canary_seconds"]:
                    raise GovernanceError("canary_observation_window_incomplete")
                conn.execute(
                    "INSERT INTO reviews VALUES(?,?,?)",
                    (identity, kind, canonical(envelope).decode()),
                )
                conn.execute(
                    "UPDATE candidates SET state=?,changed=? WHERE id=?", (after, now, identity)
                )
                conn.commit()
        except (TrustError, KeyError, TypeError, ValueError) as exc:
            raise GovernanceError("signed_independent_review_required") from exc
        return self.status(identity)


class MemoryFeedbackService:
    """Trusted adapter: never take client/subject/scope from submitted feedback.

    Only a verified scoped artifact can be referenced. Quotes are returned as
    data; this adapter has no tool/approval/policy mutation or training API.
    """

    def __init__(self, work_service, memory):
        self.work, self.memory = work_service, memory

    def identity(self, token):
        session = self.work.session(token)
        return MemoryIdentity(session["venture"], session["actor"], "qa:owned")

    def quote(self, token):
        return self.memory.quote(self.identity(token), purpose="qa-context")

    def submit(self, token, body):
        if not isinstance(body, dict) or set(body) != {
            "task_id",
            "artifact_sha256",
            "consent_id",
            "text",
            "expires",
        }:
            raise GovernanceError("feedback_cannot_supply_identity_or_authority")
        identity = self.identity(token)
        artifact = self.work.outbox(token, body["task_id"])
        if not artifact or artifact["sha256"] != body["artifact_sha256"]:
            raise GovernanceError("verified_scoped_artifact_required")
        quote_id = self.memory.add(
            identity,
            body["consent_id"],
            purpose="qa-context",
            text=body["text"],
            artifact_sha256=body["artifact_sha256"],
            expires=body["expires"],
        )
        return {
            "id": quote_id,
            "untrusted_data_only": True,
            "training": False,
            "authority_changed": False,
        }
