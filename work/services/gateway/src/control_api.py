"""S08 local authenticated control plane; fixed-owned QA only, no paid providers.

Host console issues scoped, one-use pairing/reauth grants. Every device request
proves P-256 key possession against a server-issued single-use request/body-bound
challenge. Device keys are renderer-memory keys, NOT hardware-keystore claims.
TLS identity is mandatory; no certificate-bypass switch exists in application code.
No legacy /v3 routes, provider keys, DDL or authority-grant routes are exposed.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

from conversation_api import (
    HISTORY_SCOPES,
    ConversationAPI,
    HistoryError,
    history_route,
    strict_json,
)
from conversation_api import (
    PREFIX as HISTORY_PREFIX,
)
from conversation_api import (
    required_scope as history_required_scope,
)
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from governed_skills import GovernanceError
from starlette.concurrency import run_in_threadpool
from trust_crypto import decode
from work_service import AuthorityError, Intake, token_hash
from work_store import WorkError, WorkUnavailable

API_VERSION = "1"
CLIENT_VERSION = "0.2.0"
SCOPES = {"read", "propose", "approve", "execute", "cancel", "revoke-self"} | HISTORY_SCOPES
HEX = r"[a-f0-9]{64}"
ID = r"[A-Za-z0-9_-]{32}"
TASK = r"w[a-f0-9]{32}"


class ControlError(ValueError):
    def __init__(self, code="authentication_or_scope_required", status=403):
        super().__init__(code)
        self.code, self.status = code, status


def sha(value):
    return hashlib.sha256(value).hexdigest()


def exact(body, fields):
    if not isinstance(body, dict) or set(body) != set(fields):
        raise ControlError("exact_versioned_fields_required", 422)


def p256_public(encoded):
    try:
        public = serialization.load_der_public_key(decode(encoded))
        if not isinstance(public, ec.EllipticCurvePublicKey) or not isinstance(
            public.curve, ec.SECP256R1
        ):
            raise ControlError()
        if len(decode(encoded)) != 91:
            raise ControlError()
        return public
    except (ValueError, TypeError) as exc:
        raise ControlError() from exc


def verify_device(public, signature, message):
    try:
        raw = decode(signature)
        if len(raw) != 64:
            raise ControlError()
        der = encode_dss_signature(int.from_bytes(raw[:32]), int.from_bytes(raw[32:]))
        p256_public(public).verify(der, message.encode(), ec.ECDSA(hashes.SHA256()))
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise ControlError() from exc


def request_allowed(method, path):
    if method == "GET":
        return bool(
            re.fullmatch(
                r"/api/v1/(snapshot|status|tasks|audit|exact-book|session|tasks/"
                + TASK
                + r"(?:/artifact)?)",
                path,
            )
        )
    if method == "POST":
        return history_route(path) is not None or bool(
            re.fullmatch(
                r"/api/v1/(tasks|session/revoke|tasks/" + TASK + r"/(?:approve|execute|cancel))",
                path,
            )
        )
    return False


class DeviceStore:
    """Explicit new SQLite local profile; not an automatic production migration."""

    def __init__(self, path, server_id, *, initialize=False, clock=time.time):
        self.path, self.server_id, self.clock = Path(path), server_id, clock
        self.lock = threading.RLock()
        if not re.fullmatch(HEX, server_id) or self.path.is_symlink():
            raise ControlError("explicit_private_device_store_required", 503)
        if not initialize and not self.path.is_file():
            raise ControlError("existing_private_device_store_required", 503)
        if initialize:
            with self.tx() as conn:
                conn.executescript("""
                  CREATE TABLE IF NOT EXISTS control_v1_meta(version INTEGER,server_id TEXT);
                  CREATE TABLE IF NOT EXISTS control_v1_grants(code_hash TEXT PRIMARY KEY,actor TEXT,venture TEXT,
                    role TEXT,scopes TEXT,expires INTEGER,session_expires INTEGER,token TEXT,used INTEGER);
                  CREATE TABLE IF NOT EXISTS control_v1_devices(id TEXT PRIMARY KEY,public_key TEXT,actor TEXT,
                    venture TEXT,role TEXT,scopes TEXT,expires INTEGER,token TEXT,revoked INTEGER,label TEXT);
                  CREATE TABLE IF NOT EXISTS control_v1_challenges(id TEXT PRIMARY KEY,device TEXT,message TEXT,
                    method TEXT,path TEXT,body_sha TEXT,expires INTEGER,used INTEGER);
                  CREATE TABLE IF NOT EXISTS control_v1_reauth(code_hash TEXT PRIMARY KEY,device TEXT,task TEXT,
                    digest TEXT,expires INTEGER,used INTEGER);
                  CREATE TABLE IF NOT EXISTS control_v1_rates(key TEXT PRIMARY KEY,window INTEGER,count INTEGER);
                  CREATE TABLE IF NOT EXISTS control_v1_task_catalog(task TEXT PRIMARY KEY,resolution TEXT);
                """)
                rows = conn.execute("SELECT version,server_id FROM control_v1_meta").fetchall()
                if not rows:
                    conn.execute("INSERT INTO control_v1_meta VALUES(1,?)", (server_id,))
        with self.tx() as conn:
            rows = conn.execute("SELECT version,server_id FROM control_v1_meta").fetchall()
            if len(rows) != 1 or tuple(rows[0]) != (1, server_id):
                raise ControlError("device_schema_or_identity_mismatch", 503)

    @contextmanager
    def tx(self):
        with self.lock:
            conn = sqlite3.connect(self.path, timeout=5, isolation_level=None)
            conn.row_factory = sqlite3.Row
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
            except BaseException:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _rate(self, conn, key, cap):
        window = int(self.clock()) // 60
        conn.execute("DELETE FROM control_v1_rates WHERE window<?", (window,))
        row = conn.execute(
            "SELECT count FROM control_v1_rates WHERE key=? AND window=?", (key, window)
        ).fetchone()
        if row and row[0] >= cap:
            raise ControlError("rate_limited", 429)
        if conn.execute("SELECT COUNT(*) FROM control_v1_rates").fetchone()[0] > 4096:
            raise ControlError("capacity_limited", 429)
        conn.execute(
            "INSERT INTO control_v1_rates VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET window=excluded.window,count=CASE WHEN control_v1_rates.window=excluded.window THEN control_v1_rates.count+1 ELSE 1 END",
            (key, window),
        )

    def device(self, conn, identity):
        if not isinstance(identity, str) or not re.fullmatch(ID, identity):
            raise ControlError()
        row = conn.execute("SELECT * FROM control_v1_devices WHERE id=?", (identity,)).fetchone()
        if not row or row["revoked"] or row["expires"] <= int(self.clock()):
            raise ControlError()
        return dict(row)

    def rate(self, key, cap):
        with self.tx() as conn:
            self._rate(conn, key, cap)

    def pair(self, body, ip):
        self.rate("pair:" + sha(ip.encode()), 10)
        exact(body, {"code", "public_key", "signature", "label", "client_version"})
        if (
            body["client_version"] != CLIENT_VERSION
            or not isinstance(body["code"], str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{43}", body["code"])
            or not isinstance(body["label"], str)
            or not 1 <= len(body["label"]) <= 64
            or any(ord(c) < 32 for c in body["label"])
        ):
            raise ControlError("invalid_pairing_contract", 422)
        p256_public(body["public_key"])
        verify_device(
            body["public_key"],
            body["signature"],
            f"openbot.pair/1\n{self.server_id}\n{body['code']}",
        )
        with self.tx() as conn:
            row = conn.execute(
                "SELECT * FROM control_v1_grants WHERE code_hash=?", (sha(body["code"].encode()),)
            ).fetchone()
            if (
                not row
                or row["used"]
                or row["expires"] <= int(self.clock())
                or row["session_expires"] <= int(self.clock())
            ):
                raise ControlError()
            if (
                conn.execute(
                    "SELECT COUNT(*) FROM control_v1_devices WHERE expires>? AND revoked=0",
                    (int(self.clock()),),
                ).fetchone()[0]
                >= 1000
            ):
                raise ControlError("device_capacity_limited", 429)
            device = secrets.token_urlsafe(24)
            conn.execute(
                "INSERT INTO control_v1_devices VALUES(?,?,?,?,?,?,?,?,0,?)",
                (
                    device,
                    body["public_key"],
                    row["actor"],
                    row["venture"],
                    row["role"],
                    row["scopes"],
                    row["session_expires"],
                    row["token"],
                    body["label"],
                ),
            )
            conn.execute(
                "UPDATE control_v1_grants SET used=1,token='' WHERE code_hash=?",
                (sha(body["code"].encode()),),
            )
        return {
            "device": device,
            "expires": row["session_expires"],
            "scopes": json.loads(row["scopes"]),
            "venture": row["venture"],
            "role": row["role"],
            "key_storage": "renderer_memory",
            "hardware_key_bound": False,
        }

    def challenge(self, body, ip):
        self.rate("challenge-ip:" + sha(ip.encode()), 180)
        exact(body, {"device", "method", "path", "body_sha256", "api_version"})
        if (
            body["api_version"] != API_VERSION
            or not isinstance(body["method"], str)
            or not isinstance(body["path"], str)
            or not request_allowed(body["method"], body["path"])
            or not isinstance(body["body_sha256"], str)
            or not re.fullmatch(HEX, body["body_sha256"])
        ):
            raise ControlError("invalid_request_binding", 422)
        with self.tx() as conn:
            self.device(conn, body["device"])
        self.rate("challenge-device:" + body["device"], 120)
        with self.tx() as conn:
            now = int(self.clock())
            conn.execute("DELETE FROM control_v1_challenges WHERE expires<=? OR used=1", (now,))
            if (
                conn.execute(
                    "SELECT COUNT(*) FROM control_v1_challenges WHERE device=?", (body["device"],)
                ).fetchone()[0]
                >= 32
            ):
                raise ControlError("challenge_capacity_limited", 429)
            challenge = secrets.token_urlsafe(24)
            expires = now + 60
            message = "\n".join(
                [
                    "openbot.control-request/1",
                    self.server_id,
                    body["device"],
                    challenge,
                    body["method"],
                    body["path"],
                    body["body_sha256"],
                    str(expires),
                ]
            )
            conn.execute(
                "INSERT INTO control_v1_challenges VALUES(?,?,?,?,?,?,?,0)",
                (
                    challenge,
                    body["device"],
                    message,
                    body["method"],
                    body["path"],
                    body["body_sha256"],
                    expires,
                ),
            )
        return {"id": challenge, "message": message, "expires": expires}

    def authenticate(self, headers, method, path, body):
        identity = headers.get("x-openbot-device", "")
        challenge_id = headers.get("x-openbot-challenge", "")
        if not re.fullmatch(ID, challenge_id):
            raise ControlError()
        with self.tx() as conn:
            device = self.device(conn, identity)
            challenge = conn.execute(
                "SELECT * FROM control_v1_challenges WHERE id=?", (challenge_id,)
            ).fetchone()
            if (
                not challenge
                or challenge["used"]
                or challenge["expires"] <= int(self.clock())
                or challenge["device"] != identity
                or challenge["method"] != method
                or challenge["path"] != path
                or challenge["body_sha"] != sha(body)
            ):
                raise ControlError()
            verify_device(
                device["public_key"], headers.get("x-openbot-signature", ""), challenge["message"]
            )
            conn.execute(
                "UPDATE control_v1_challenges SET used=1 WHERE id=? AND used=0", (challenge_id,)
            )
        return device

    def reauthenticate(self, device, task_id, expected, code):
        if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", code):
            raise ControlError("fresh_owner_reauthentication_required")
        with self.tx() as conn:
            self.device(conn, device["id"])
            row = conn.execute(
                "SELECT * FROM control_v1_reauth WHERE code_hash=?", (sha(code.encode()),)
            ).fetchone()
            if (
                not row
                or row["used"]
                or row["expires"] <= int(self.clock())
                or row["device"] != device["id"]
                or row["task"] != task_id
                or row["digest"] != expected
            ):
                raise ControlError("fresh_exact_owner_reauthentication_required")
            conn.execute(
                "UPDATE control_v1_reauth SET used=1 WHERE code_hash=?", (sha(code.encode()),)
            )


class ControlAuthority:
    """Trusted console API ONLY. Deliberately never mounted over HTTP."""

    def __init__(self, devices, issuer):
        if issuer.work.setup is not True:
            raise ControlError("trusted_setup_issuer_required", 503)
        self.devices, self.issuer = devices, issuer

    def issue_pairing(
        self, *, actor, venture, role="viewer", scopes=("read", "revoke-self"), ttl=900
    ):
        if (
            not isinstance(scopes, list | tuple)
            or not set(scopes) <= SCOPES
            or "read" not in scopes
            or len(set(scopes)) != len(scopes)
            or type(ttl) is not int
            or not 60 <= ttl <= 900
            or role not in {"owner", "viewer"}
            or (role == "viewer" and set(scopes) - {"read", "revoke-self", "history-read"})
        ):
            raise ControlError("least_privilege_pairing_required", 422)
        token = self.issuer.issue_session(
            actor=actor,
            venture=venture,
            role=role,
            initiator={"kind": "person", "id": "device-pairing"},
            ttl=ttl,
        )
        now = int(self.devices.clock())
        code = secrets.token_urlsafe(32)
        with self.devices.tx() as conn:
            conn.execute("DELETE FROM control_v1_grants WHERE expires<=?", (now,))
            if (
                conn.execute("SELECT COUNT(*) FROM control_v1_grants WHERE used=0").fetchone()[0]
                >= 100
            ):
                raise ControlError("pairing_capacity_limited", 429)
            conn.execute(
                "INSERT INTO control_v1_grants VALUES(?,?,?,?,?,?,?,?,0)",
                (
                    sha(code.encode()),
                    actor,
                    venture,
                    role,
                    json.dumps(sorted(scopes)),
                    now + 120,
                    now + ttl,
                    token,
                ),
            )
        return code

    def issue_reauthentication(self, device_id, task_id, expected_digest, *, human):
        with self.devices.tx() as conn:
            device = self.devices.device(conn, device_id)
            if (
                device["role"] != "owner"
                or human != device["actor"]
                or not human.startswith("human:")
            ):
                raise ControlError()
        _session, task = self.issuer.task(device["token"], task_id, mutate=True)
        if task["spec_digest"] != expected_digest or task["status"] != "review":
            raise ControlError("current_exact_review_required")
        code = secrets.token_urlsafe(32)
        with self.devices.tx() as conn:
            conn.execute(
                "DELETE FROM control_v1_reauth WHERE expires<=?", (int(self.devices.clock()),)
            )
            conn.execute(
                "INSERT INTO control_v1_reauth VALUES(?,?,?,?,?,0)",
                (
                    sha(code.encode()),
                    device_id,
                    task_id,
                    expected_digest,
                    int(self.devices.clock()) + 120,
                ),
            )
        return code

    def revoke(self, device_id):
        with self.devices.tx() as conn:
            device = self.devices.device(conn, device_id)
            conn.execute("UPDATE control_v1_devices SET revoked=1 WHERE id=?", (device_id,))
        self.issuer.revoke_session(device["token"])
        return {"revoked": True, "running_work_stop_confirmed": False}


class ControlBridge:
    def __init__(self, devices, work, catalog, *, book, book_scopes, authority=None, history=None):
        if history is not None and type(history) is not ConversationAPI:
            raise ControlError("explicit_history_component_required", 503)
        self.devices, self.work, self.catalog = devices, work, catalog
        self.book, self.book_scopes, self.authority = book, book_scopes, authority
        self.history = history  # None by default: no store is opened/initialized.

    def history_request(self, device, path, body):
        if self.history is None:
            raise ControlError("history_not_configured", 404)
        if not self.work.enabled or self.work.work.pg:
            # PG auth/history fencing is a separate, not-yet-accepted profile.
            raise ControlError("enabled_sqlite_history_profile_required", 503)
        required = history_required_scope(path)
        attempt = "history-" + secrets.token_hex(16)
        operation = history_route(path)[0]
        with self.devices.tx() as devices_conn:
            current = self.devices.device(devices_conn, device["id"])
            if current["public_key"] != device["public_key"] or current["token"] != device["token"]:
                raise ControlError()
            try:
                scopes = strict_json(current["scopes"])
            except ValueError as exc:
                raise ControlError() from exc
            if type(scopes) is not list or required not in scopes:
                raise ControlError()

            def session_in(cur):
                session = self.work._session(cur, token_hash(current["token"]))
                if any(session[k] != current[k] for k in ("venture", "actor", "role")):
                    raise ControlError()
                if session["role"] not in {"owner", "viewer"} or (
                    required != "history-read"
                    and (session["role"] != "owner" or not session["actor"].startswith("human:"))
                ):
                    raise ControlError()
                return session

            def record(cur, session, kind):
                self.work.work.event(
                    cur,
                    {
                        "id": attempt,
                        "venture": session["venture"],
                        "initiator": session["initiator"],
                    },
                    kind,
                    {"operation": operation, "conversation_content_recorded": False},
                )

            # Commit a content-free attempt BEFORE history access/mutation. A
            # later journal/auth-DB failure may leave attempt without completion.
            with self.work.work.tx() as cur:
                session = session_in(cur)
                record(cur, session, "conversation_history_attempt")
            # Lock order is devices -> work/auth -> journal. SQLite transactions
            # fence protocol-respecting device/session revocation and scope edits
            # until history commit. Never call scope() here (it reacquires stores).
            with self.work.work.tx() as cur:
                self.devices.device(devices_conn, device["id"])
                session = session_in(cur)
                data = self.history.dispatch(self.devices.server_id, session, path, body)
                record(cur, session, "conversation_history_complete")
                return {**data, "audit_attempt": attempt}

    def scope(self, device, required):
        with self.devices.tx() as conn:
            self.devices.device(conn, device["id"])
        if required not in json.loads(device["scopes"]):
            raise ControlError()
        session = self.work.session(device["token"])
        if session["venture"] != device["venture"] or session["actor"] != device["actor"]:
            raise ControlError()
        return session

    def tasks(self, device):
        session = self.scope(device, "read")
        return [
            self.work.public(row)
            for row in self.work.work.list(session["venture"])
            if self.work._owns(session, row)
        ][:100]

    def audit(self, device):
        session = self.scope(device, "read")
        with self.work.work.tx() as cur:
            self.work.work.q(
                cur,
                "SELECT h.seq,h.task_id,h.kind,h.payload_json,h.stamp FROM work_v1_history h JOIN work_v1_tasks t ON t.id=h.task_id WHERE t.venture=? ORDER BY h.seq DESC LIMIT 100",
                (session["venture"],),
            )
            return [
                {**r, "payload": json.loads(r.pop("payload_json"))}
                for r in self.work.work.rows(cur)
            ]

    def exact_book(self, device):
        session = self.scope(device, "read")
        scope = self.book_scopes.get(session["venture"])
        if scope is None or scope.venture != session["venture"]:
            raise ControlError("exact_book_scope_unavailable", 503)
        summary = self.book.summary(scope)
        summary = {k: str(v) if k.endswith("_minor") else v for k, v in summary.items()}
        postings = [
            {k: str(v) if k == "amount_minor" else v for k, v in p.items()}
            for p in self.book.postings(scope, limit=100)
        ]
        return {
            "summary": summary,
            "postings": postings,
            "source": "economic_v1_postings",
            "legacy_float_pnl_used": False,
            "not_profit_or_bank_settlement": True,
        }

    def status(self, device):
        self.scope(device, "read")
        rows = self.tasks(device)
        return {
            "venture": device["venture"],
            "tasks": len(rows),
            "needs_review": sum(t["status"] == "review" for t in rows),
            "completed": sum(t["status"] == "completed" for t in rows),
            "execution_mode": "fixed_owned_qa_only",
            "paid_provider_enabled": False,
            "customer_execution_enabled": False,
            "s09_external_gate_passed": False,
            "source": "work_v1_tasks",
            "task_page_limit": 100,
        }

    def dispatch(self, device, method, path, body):
        if method == "POST" and path.startswith(HISTORY_PREFIX + "/"):
            return self.history_request(device, path, body)
        token = device["token"]
        if method == "GET":
            if body:
                raise ControlError("get_body_refused", 422)
            if path == "/api/v1/snapshot":
                return {
                    "status": self.status(device),
                    "tasks": self.tasks(device),
                    "audit": self.audit(device),
                    "exact_book": self.exact_book(device),
                }
            if path == "/api/v1/status":
                return self.status(device)
            if path == "/api/v1/tasks":
                return self.tasks(device)
            if path == "/api/v1/audit":
                return self.audit(device)
            if path == "/api/v1/exact-book":
                return self.exact_book(device)
            if path == "/api/v1/session":
                self.scope(device, "read")
                return {
                    k: device[k] for k in ("id", "actor", "venture", "role", "expires", "label")
                }
            match = re.fullmatch("/api/v1/tasks/(" + TASK + ")(/artifact)?", path)
            if match:
                self.scope(device, "read")
                if match[2]:
                    return self.work.outbox(token, match[1])
                _session, row = self.work.task(token, match[1])
                return self.work.public(row)
        if method == "POST":
            try:
                value = strict_json(body)
            except (ValueError, TypeError) as exc:
                raise ControlError("valid_json_required", 422) from exc
            if path == "/api/v1/tasks":
                self.scope(device, "propose")
                resolution = self.catalog.resolve("owned.qa", device["venture"])
                try:
                    intake = Intake.model_validate(value).model_dump()
                except ValueError as exc:
                    raise ControlError("exact_owned_intake_required", 422) from exc
                row = self.work.prepare(token, intake)
                if row.get("status") == "clarify":
                    return row
                with self.devices.tx() as conn:
                    old = conn.execute(
                        "SELECT resolution FROM control_v1_task_catalog WHERE task=?", (row["id"],)
                    ).fetchone()
                    if old and old[0] != resolution["resolution_digest"]:
                        raise ControlError("catalog_changed_new_exact_proposal_required", 409)
                    conn.execute(
                        "INSERT OR IGNORE INTO control_v1_task_catalog VALUES(?,?)",
                        (row["id"], resolution["resolution_digest"]),
                    )
                return row
            if path == "/api/v1/session/revoke":
                exact(value, set())
                self.scope(device, "revoke-self")
                if self.authority is None:
                    raise ControlError("console_revocation_required", 503)
                return self.authority.revoke(device["id"])
            match = re.fullmatch("/api/v1/tasks/(" + TASK + ")/(approve|execute|cancel)", path)
            if match:
                task_id, action = match.groups()
                self.scope(device, action)
                if action == "cancel":
                    exact(value, set())
                    return self.work.cancel(token, task_id)
                exact(value, {"digest", "reauth_code"} if action == "approve" else {"digest"})
                _session, task = self.work.task(token, task_id, mutate=True)
                resolution = self.catalog.resolve("owned.qa", device["venture"])
                with self.devices.tx() as conn:
                    binding = conn.execute(
                        "SELECT resolution FROM control_v1_task_catalog WHERE task=?", (task_id,)
                    ).fetchone()
                    if (
                        not binding
                        or binding[0] != resolution["resolution_digest"]
                        or value["digest"] != task["spec_digest"]
                    ):
                        raise ControlError("current_exact_plan_and_catalog_required", 409)
                if action == "approve":
                    if device["role"] != "owner":
                        raise ControlError()
                    self.devices.reauthenticate(
                        device, task_id, value["digest"], value["reauth_code"]
                    )
                    return {"approved": self.work.approve(token, task_id, value["digest"], ttl=120)}
                return self.work.execute(token, task_id)
        raise ControlError("versioned_route_not_found", 404)


def create_control_app(bridge, *, origin, client_file, client_sha256, enabled=False):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    if enabled is not True:
        return app
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username
    ):
        raise ControlError("explicit_https_server_origin_required", 503)
    client_file = Path(client_file)
    if client_file.is_symlink() or sha(client_file.read_bytes()) != client_sha256:
        raise ControlError("reviewed_client_source_required", 503)
    client_bytes = client_file.read_bytes()
    scripts = re.findall(rb"<script>(.*?)</script>", client_bytes, re.S)
    import base64

    hashes_csp = " ".join(
        "'sha256-" + base64.b64encode(hashlib.sha256(s).digest()).decode() + "'" for s in scripts
    )
    policy = f"default-src 'none'; script-src {hashes_csp}; style-src 'unsafe-inline'; img-src data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'"

    @app.middleware("http")
    async def boundary(request, call_next):
        if (
            request.url.scheme != "https"
            or request.headers.get("host", "").lower() != parsed.netloc.lower()
            or request.headers.get("origin", origin) != origin
        ):
            return JSONResponse({"detail": "trusted_https_origin_required"}, status_code=403)
        if request.url.query or "%" in request.scope.get("raw_path", b"").decode(
            "ascii", errors="replace"
        ):
            return JSONResponse({"detail": "canonical_path_required"}, status_code=422)
        try:
            bridge.devices.rate(
                "http:" + sha((request.client.host if request.client else "unknown").encode()), 600
            )
        except ControlError as exc:
            return JSONResponse({"detail": exc.code}, status_code=exc.status)
        value = bytearray()
        try:
            async with __import__("asyncio").timeout(5):
                async for chunk in request.stream():
                    if len(value) + len(chunk) > 16384:
                        return JSONResponse({"detail": "bounded_request_exceeded"}, status_code=413)
                    value.extend(chunk)
        except TimeoutError:
            return JSONResponse({"detail": "request_deadline"}, status_code=408)
        request._body = bytes(value)
        response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": policy,
                "Referrer-Policy": "no-referrer",
                "Strict-Transport-Security": "max-age=31536000",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            }
        )
        return response

    @app.exception_handler(ControlError)
    async def control_error(_request, exc):
        return JSONResponse({"detail": exc.code}, status_code=exc.status)

    @app.exception_handler(HistoryError)
    async def history_error(_request, exc):
        return JSONResponse({"detail": exc.code}, status_code=exc.status)

    @app.exception_handler(AuthorityError)
    async def authority_error(_request, _exc):
        return JSONResponse({"detail": "authentication_or_scope_required"}, status_code=403)

    @app.exception_handler(GovernanceError)
    async def governance_error(_request, _exc):
        return JSONResponse({"detail": "current_trusted_tool_required"}, status_code=409)

    @app.exception_handler(WorkError)
    async def work_error(_request, _exc):
        return JSONResponse({"detail": "work_contract_refused_no_automatic_retry"}, status_code=409)

    @app.exception_handler(WorkUnavailable)
    async def unavailable(_request, _exc):
        return JSONResponse({"detail": "store_unavailable_no_automatic_retry"}, status_code=503)

    def envelope(data):
        return {
            "api_version": API_VERSION,
            "server_id": bridge.devices.server_id,
            "observed_at": int(bridge.devices.clock()),
            "fresh_for_seconds": 15,
            "source": "local_authenticated_server",
            "data": data,
        }

    @app.get("/control/")
    async def control_page():
        return HTMLResponse(client_bytes)

    @app.get("/api/v1/identity")
    async def identity():
        return envelope(
            {
                "client_version": CLIENT_VERSION,
                "client_sha256": client_sha256,
                "tls_required": True,
                "mode": "local_owned_fixture",
                "public_or_production_release": False,
            }
        )

    @app.post("/api/v1/pair")
    async def pair(request: Request):
        try:
            body = strict_json(await request.body())
        except ValueError as exc:
            raise ControlError("valid_json_required", 422) from exc
        return envelope(
            bridge.devices.pair(body, request.client.host if request.client else "unknown")
        )

    @app.post("/api/v1/challenge")
    async def challenge(request: Request):
        try:
            body = strict_json(await request.body())
        except ValueError as exc:
            raise ControlError("valid_json_required", 422) from exc
        return envelope(
            bridge.devices.challenge(body, request.client.host if request.client else "unknown")
        )

    @app.api_route("/api/v1/{path:path}", methods=["GET", "POST"])
    async def authenticated(request: Request, path: str):
        target = "/api/v1/" + path
        if not request_allowed(request.method, target):
            raise ControlError("versioned_route_not_found", 404)
        body = await request.body()
        device = bridge.devices.authenticate(request.headers, request.method, target, body)
        data = await run_in_threadpool(bridge.dispatch, device, request.method, target, body)
        return envelope(data)

    return app
