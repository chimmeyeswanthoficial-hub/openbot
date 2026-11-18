"""Offline work intake, QA evidence packaging, and revocable reviewed task feedback.

NO job crawler, social API, model training, executor, delivery adapter or remote auth.
Authority/Owner are existing trusted-HOST conventions, not identity from client JSON.
Same-user DB/source tampering, host path races, backups and downstream models are NOT
isolated here. Feedback is quoted untrusted task context, never executable policy.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
import xml.etree.ElementTree as ET
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from local_executor import Authority, Owner, canonical, digest, private_directory
from policy import contains_secret

SERVICES = frozenset({"qa", "docs"})
ALL_SERVICES = SERVICES | {"video_edit", "video_generate", "other"}
DAY = 86400
ID = re.compile(r"[a-z][a-z0-9_-]{0,63}")
SHA = re.compile(r"[0-9a-f]{64}")
FEEDBACK_FIELDS = {"service", "source_kind", "source_ref", "rights_ref",
                   "consent_to_reuse", "text", "expires_at"}


def _text(value, limit=4096):
    if (not isinstance(value, str) or not value.strip() or len(value.encode()) > limit
            or any(ord(c) < 32 and c not in "\n\t" for c in value) or contains_secret(value)):
        raise ValueError("invalid, oversized or credential-shaped text")
    return value


def _time(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware host clock required")
    return value.timestamp()


def _date(value):
    try:
        return _time(datetime.fromisoformat(value))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("timezone-aware ISO timestamp required") from exc


def _service(value):
    if not isinstance(value, str) or value not in SERVICES:
        raise ValueError("unsupported reviewed feedback service")
    return value


def triage(brief: dict, *, now: datetime) -> dict:
    """Operator-attested metadata only. A promising result never permits a send/run."""
    fields = {"title", "source_url", "checked_at", "service", "work_kind", "location",
              "ai_use", "source_permission", "customer_permission"}
    if not isinstance(brief, dict) or set(brief) != fields:
        raise ValueError("exact intake fields required; no authority in JSON")
    _text(brief["title"], 200)
    url = urlsplit(_text(brief["source_url"], 2048))
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError("HTTPS provenance URL without credentials required")
    enums = {"service": ALL_SERVICES, "work_kind": {"deliverable", "human_participation", "employment", "unknown"},
             "location": {"permitted", "restricted", "unknown"},
             "ai_use": {"permitted", "prohibited", "unknown"},
             "source_permission": {"manual_metadata", "approved_api", "unknown"},
             "customer_permission": {"granted", "not_requested", "refused"}}
    for key, choices in enums.items():
        if not isinstance(brief[key], str) or brief[key] not in choices:
            raise ValueError("unknown intake enumeration")
    age = _time(now) - _date(brief["checked_at"])
    questions = []
    for key, question in {
        "location": "Is this business/human eligible in the required location?",
        "ai_use": "Does the customer explicitly permit the proposed AI-assisted method?",
        "source_permission": "What permitted source or approved API supplied this metadata?",
        "customer_permission": "Has the customer granted the required data/testing scope?",
        "work_kind": "Is this a deliverable contract or a request for a real human participant?",
    }.items():
        if brief[key] in {"unknown", "not_requested"}:
            questions.append(question)
    if not 0 <= age <= 7 * DAY:
        questions.append("Recheck availability and terms; the observation is stale or future-dated.")
    if (brief["ai_use"] == "prohibited" or brief["location"] == "restricted"
            or brief["customer_permission"] == "refused"):
        status = "reject"
    elif brief["work_kind"] in {"human_participation", "employment"}:
        status = "human_only"
    elif brief["service"] not in SERVICES:
        status = "not_ready"
    elif questions:
        status = "clarify"
    else:
        status = "review_for_proposal"
    return {"status": status, "questions": questions, "brief_sha256": digest(canonical(brief).encode()),
            "allows_send": False, "allows_execution": False,
            "limits": "Metadata attestations are not verified availability, permissions, a customer or income."}


def qa_packet(xml: bytes, *, brief_sha256: str, revision: str, run_ref: str,
              exit_code: int, required_cases: tuple[str, ...]) -> dict:
    """Parse supplied bounded UTF-8 JUnit. Never runs tests or trusts declared totals."""
    if not isinstance(xml, bytes) or not 0 < len(xml) <= 2_000_000:
        raise ValueError("bounded JUnit bytes required")
    try:
        text = xml.decode("utf-8")
        if "\x00" in text or re.search(r"<!\s*(DOCTYPE|ENTITY)\b", text, re.I) or contains_secret(text):
            raise ValueError("DTD, entity, NUL or credential-shaped content refused")
        root = ET.fromstring(text)
    except (UnicodeError, ET.ParseError) as exc:
        raise ValueError("invalid UTF-8 JUnit") from exc
    if (not isinstance(brief_sha256, str) or not SHA.fullmatch(brief_sha256)
            or not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{7,64}", revision)
            or not isinstance(run_ref, str) or not ID.fullmatch(run_ref)
            or type(exit_code) is not int or not 0 <= exit_code <= 255
            or not isinstance(required_cases, tuple) or len(required_cases) > 10000
            or any(not isinstance(x, str) for x in required_cases)
            or len(set(required_cases)) != len(required_cases)):
        raise ValueError("invalid host evidence contract")
    for name in required_cases:
        _text(name, 1024)
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError("JUnit root required")
    allowed = {"testsuites": {"testsuite", "testsuites"},
               "testsuite": {"testsuite", "testcase", "properties", "system-out", "system-err"},
               "testcase": {"failure", "error", "skipped", "properties", "system-out", "system-err"},
               "properties": {"property"}, "property": set(), "failure": set(), "error": set(),
               "skipped": set(), "system-out": set(), "system-err": set()}
    stack, visited = [(root, 0)], 0
    while stack:
        node, depth = stack.pop()
        visited += 1
        if depth > 64 or visited > 20000 or node.tag not in allowed:
            raise ValueError("unsupported or oversized JUnit structure")
        for child in node:
            if child.tag not in allowed[node.tag]:
                raise ValueError("misplaced JUnit element or unknown outcome")
            stack.append((child, depth + 1))
    cases = list(root.iter("testcase"))
    if not 1 <= len(cases) <= 10000:
        raise ValueError("nonempty bounded cases required")
    outcomes = {}
    for case in cases:
        if (case.get("status", "run") not in {"run", "completed", "passed"}
                or case.get("result", "completed") not in {"completed", "passed"}):
            raise ValueError("unsupported explicit not-run/result status; normalize only with reviewed provenance")
        name = _text(case.get("name"), 512)
        class_name = case.get("classname", "")
        if class_name:
            _text(class_name, 512)
        identity = class_name + "::" + name
        terminal = [x.tag for x in case if x.tag in {"failure", "error", "skipped"}]
        if len(terminal) > 1 or identity in outcomes:
            raise ValueError("duplicate identity or ambiguous outcome")
        outcomes[identity] = terminal[0] if terminal else "passed"
    # Check every declared suite/root count against its actual descendant cases.
    for suite in root.iter():
        if suite.tag not in {"testsuite", "testsuites"}:
            continue
        children = list(suite.iter("testcase"))
        expected = {"tests": len(children), "failures": 0, "errors": 0, "skipped": 0, "disabled": 0}
        for case in children:
            for child in case:
                if child.tag in {"failure", "error", "skipped"}:
                    expected[{"failure": "failures", "error": "errors", "skipped": "skipped"}[child.tag]] += 1
        for key, value in expected.items():
            if key in suite.attrib and suite.get(key) != str(value):
                raise ValueError("declared JUnit counts contradict actual cases")
    counts = {"passed": sum(x == "passed" for x in outcomes.values()),
              "failed": sum(x in {"failure", "error"} for x in outcomes.values()),
              "skipped": sum(x == "skipped" for x in outcomes.values()), "collected": len(cases)}
    unmet = [name for name in required_cases if outcomes.get(name) != "passed"]
    complete = (exit_code == 0 and not counts["failed"] and not counts["skipped"]
                and bool(required_cases) and not unmet)
    return {"counts": counts, "evidence_status": "ready_for_review" if complete else "needs_investigation",
            "brief_sha256": brief_sha256, "source_revision": revision, "run_ref": run_ref,
            "junit_sha256": digest(xml), "runner_exit_code": exit_code,
            "required_cases": list(required_cases), "unmet_cases": unmet,
            "delivery_authorized": False, "specialist_parity": "not_measured",
            "limits": "Parser did not execute tests, authenticate their origin, verify test quality, approve delivery or measure specialist parity."}


class FeedbackBook:
    """One trusted local operator DB; scoped queries are NOT hostile-tenant isolation.

    Max 30-day retention is our conservative direct-feedback rule, not a social-API
    compliance implementation. Expiry runs on API use, not in a background worker.
    Revocation redacts live rows; backups, prior exports and downstream copies need
    their own deletion procedure. No feedback is automatically fed to a model.
    """

    def __init__(self, state: Path, authority: Authority):
        if not isinstance(authority, Authority):
            raise ValueError("trusted host authority required")
        self.authority = authority
        state = Path(state).absolute()
        private_directory(state)
        self.path = state / "work-feedback.sqlite3"
        if self.path.is_symlink() or (self.path.exists() and not self.path.is_file()):
            raise ValueError("operator database must be a regular non-symlink file")
        with closing(sqlite3.connect(self.path)) as db:
            if db.execute("PRAGMA user_version").fetchone()[0] not in {0, 1}:
                raise ValueError("unrecognized feedback schema")
            db.execute("PRAGMA journal_mode=DELETE")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS feedback (
                  id TEXT PRIMARY KEY, venture TEXT NOT NULL, service TEXT NOT NULL,
                  payload TEXT, sha256 TEXT, approved_sha256 TEXT, status TEXT NOT NULL,
                  expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS feedback_audit (
                  seq INTEGER PRIMARY KEY, venture TEXT NOT NULL, actor TEXT NOT NULL,
                  action TEXT NOT NULL, item_id TEXT, stamp INTEGER NOT NULL);
                PRAGMA user_version=1;
            """)
            db.commit()
        os.chmod(self.path, 0o600)

    @contextmanager
    def _tx(self):
        with closing(sqlite3.connect(self.path, timeout=5)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA secure_delete=ON")
            try:
                db.execute("BEGIN IMMEDIATE")
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    def _event(self, db, action, item_id, stamp, actor=None):
        db.execute("INSERT INTO feedback_audit(venture,actor,action,item_id,stamp) VALUES (?,?,?,?,?)",
                   (self.authority.venture, actor or self.authority.actor, action, item_id, stamp))

    @staticmethod
    def _body(body, created):
        if not isinstance(body, dict) or set(body) != FEEDBACK_FIELDS:
            raise ValueError("exact direct-feedback fields required")
        _service(body["service"])
        if body["source_kind"] != "direct_consented" or body["consent_to_reuse"] is not True:
            raise ValueError("only separately consented direct feedback; no social data import")
        for key in ("source_ref", "rights_ref"):
            if not isinstance(body[key], str) or not ID.fullmatch(body[key]):
                raise ValueError("opaque source and consent receipts required")
        _text(body["text"])
        expiry = _date(body["expires_at"])
        if not created < expiry <= created + 30 * DAY or not expiry.is_integer():
            raise ValueError("expiry must be a whole second within 30 days")
        return int(expiry)

    @staticmethod
    def _hash(row):
        return digest(canonical({key: row[key] for key in
                                 ("id", "venture", "service", "payload", "expires_at", "created_at")}).encode())

    def _row(self, db, item_id):
        if not isinstance(item_id, str) or str(uuid.UUID(item_id)) != item_id:
            raise ValueError("canonical feedback UUID required")
        row = db.execute("SELECT * FROM feedback WHERE id=? AND venture=?",
                         (item_id, self.authority.venture)).fetchone()
        if row is None or row["status"] not in {"pending", "approved"} or row["payload"] is None:
            raise ValueError("feedback unavailable in host scope")
        return row

    def _unpack(self, row):
        try:
            body = json.loads(row["payload"])
            expiry = self._body(body, row["created_at"])
            if (self._hash(row) != row["sha256"] or expiry != row["expires_at"]
                    or body["service"] != row["service"]
                    or (row["status"] == "approved" and row["approved_sha256"] != row["sha256"])):
                raise ValueError("stored feedback binding changed")
        except (TypeError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError("corrupt feedback") from exc
        return body

    @staticmethod
    def _owner(owner):
        if (not isinstance(owner, Owner) or not isinstance(owner.actor, str)
                or not re.fullmatch(r"human:[a-z0-9][a-z0-9_-]{0,63}", owner.actor)):
            raise ValueError("trusted host human review capability required; not JSON")

    def submit(self, body: dict, *, now: datetime) -> dict:
        stamp = int(_time(now))
        expiry = self._body(body, stamp)
        payload = canonical(body)  # freeze caller-owned data, including provenance/consent/expiry
        self.expire(now=now)
        row = {"id": str(uuid.uuid4()), "venture": self.authority.venture, "service": body["service"],
               "payload": payload, "expires_at": expiry, "created_at": stamp}
        fingerprint = self._hash(row)
        with self._tx() as db:
            count = db.execute("SELECT count(*) FROM feedback WHERE venture=? AND payload IS NOT NULL",
                               (self.authority.venture,)).fetchone()[0]
            if count >= 1000:
                raise ValueError("local live-feedback capacity reached")
            db.execute("INSERT INTO feedback VALUES (?,?,?,?,?,NULL,'pending',?,?)",
                       (row["id"], row["venture"], row["service"], payload, fingerprint,
                        expiry, stamp))
            self._event(db, "submit", row["id"], stamp)
        return {"id": row["id"], "sha256": fingerprint, "status": "pending"}

    def preview(self, item_id: str, *, now: datetime) -> dict:
        self.expire(now=now)
        with self._tx() as db:
            row = self._row(db, item_id)
            body = self._unpack(row)
            self._event(db, "preview", item_id, int(_time(now)))
            return {"id": item_id, "sha256": row["sha256"], "body": body, "trusted_instruction": False}

    def review(self, item_id: str, expected_sha256: str, owner: Owner, *, now: datetime):
        self._owner(owner)
        self.expire(now=now)
        with self._tx() as db:
            row = self._row(db, item_id)
            self._unpack(row)
            if row["status"] != "pending" or expected_sha256 != row["sha256"]:
                raise ValueError("pending exact-preview review required")
            self._event(db, "review", item_id, int(_time(now)), owner.actor)
            db.execute("UPDATE feedback SET status='approved',approved_sha256=sha256 WHERE id=?", (item_id,))

    def revoke(self, item_id: str, owner: Owner, *, now: datetime):
        self._owner(owner)
        self.expire(now=now)
        with self._tx() as db:
            self._row(db, item_id)
            self._event(db, "revoke", item_id, int(_time(now)), owner.actor)
            db.execute("UPDATE feedback SET payload=NULL,sha256=NULL,approved_sha256=NULL,status='revoked' WHERE id=?", (item_id,))

    def expire(self, *, now: datetime) -> int:
        stamp = int(_time(now))
        with self._tx() as db:
            rows = db.execute("SELECT id FROM feedback WHERE venture=? AND payload IS NOT NULL AND expires_at<=?",
                              (self.authority.venture, stamp)).fetchall()
            for row in rows:
                self._event(db, "expire", row["id"], stamp)
                db.execute("UPDATE feedback SET payload=NULL,sha256=NULL,approved_sha256=NULL,status='expired' WHERE id=?", (row["id"],))
            return len(rows)

    def lessons(self, service: str, *, now: datetime) -> list[dict]:
        _service(service)
        self.expire(now=now)
        with self._tx() as db:
            rows = db.execute("SELECT * FROM feedback WHERE venture=? AND service=? AND status='approved' ORDER BY created_at,id LIMIT 100",
                              (self.authority.venture, service)).fetchall()
            result = []
            for row in rows:
                body = self._unpack(row)
                result.append({"id": row["id"], "text": body["text"], "source_ref": body["source_ref"],
                               "rights_ref": body["rights_ref"], "expires_at": body["expires_at"],
                               "trusted_instruction": False, "use": "quoted_task_context_only"})
            self._event(db, "read", None, int(_time(now)))
            return result
