"""S11 opt-in local operator controls; not witnessed production operations.

Protected host paths/keys/admin objects never come from agent JSON or job mounts.
Backups are bounded AES-256-GCM fixtures, not owner key recovery certification.
A local collector ACK is not an on-call human or external notification service.
"""

from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import struct
import tempfile
import time
import uuid
from contextlib import closing, contextmanager
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from trust_crypto import canonical, digest, encode


class OpsError(ValueError):
    pass


HEX = r"[a-f0-9]{64}"
MAX_BLOB = 16 << 20
PARTS = {"database.sqlite3", "config.json", "secrets.bin", "grants.json"}


def _path(path):
    path = Path(path).absolute()
    if ".." in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise OpsError("non_symlinked_operator_path_required")
    return path


def _private(path, create=False):
    path = _path(path)
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.is_dir() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise OpsError("existing_private_operator_directory_required")
    return path


def _read(path, limit=MAX_BLOB):
    path = _path(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            meta = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(meta.st_mode)
                or meta.st_uid != os.getuid()
                or meta.st_mode & 0o022
                or meta.st_nlink != 1
                or meta.st_size > limit
            ):
                raise OpsError("bounded_single_link_regular_file_required")
            value = handle.read(limit + 1)
            if len(value) > limit:
                raise OpsError("input_bound_exceeded")
            return value
    except OSError as exc:
        raise OpsError("operator_file_unavailable") from exc


def _sqlite_input(path, limit):
    _read(path, limit)
    for suffix in ("-wal", "-shm", "-journal"):
        sibling = Path(str(path) + suffix)
        if sibling.exists() or sibling.is_symlink():
            _read(sibling, limit)


def _write_new(path, value):
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise OpsError("exclusive_output_required") from exc


def _sync(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _rename_new(stage, target):
    # Linux renameat2 NOREPLACE closes the "existing empty target" TOCTOU gap.
    libc = ctypes.CDLL(None, use_errno=True)
    call = getattr(libc, "renameat2", None)
    if call is None:
        raise OpsError("atomic_no_replace_unavailable")
    call.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    call.restype = ctypes.c_int
    fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    source_fd = os.open(stage.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if call(source_fd, os.fsencode(stage.name), fd, os.fsencode(target.name), 1) != 0:
            raise OpsError("new_target_exists_or_atomic_commit_refused")
        os.fsync(fd)
    finally:
        os.close(source_fd)
        os.close(fd)


def backup_sqlite(database, files, target, key, *, source_sha256):
    """Actually snapshot committed SQLite pages, encrypt data/config/secrets/grants.

    Max DB 8 MiB and each sidecar 64 KiB in this bounded local profile. Source
    directory is trusted operator-controlled; this is not an upload backup API.
    Quiesce sidecar/config/grant writers first. The SQLite API is WAL-consistent;
    it does NOT make sidecar changes transactional or recover owner-vault keys.
    Temporary plaintext SQLite pages require a separately protected host volume.
    """
    target = _path(target)
    _private(target.parent)
    if (
        target.exists()
        or type(key) is not bytes
        or len(key) != 32
        or not isinstance(source_sha256, str)
        or not re.fullmatch(HEX, source_sha256)
        or set(files) != PARTS - {"database.sqlite3"}
    ):
        raise OpsError("new_output_key_source_and_exact_sidecars_required")
    database = _path(database)
    _sqlite_input(database, 8 << 20)
    content = {name: _read(path, 65536) for name, path in files.items()}
    directory = Path(tempfile.mkdtemp(prefix=".backup-", dir=target.parent))
    try:
        snapshot = directory / "database.sqlite3"
        deadline = time.monotonic() + 10

        def progress(_status, _remaining, _total):
            if time.monotonic() > deadline:
                raise OpsError("snapshot_deadline")

        with (
            closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=2)) as src,
            closing(sqlite3.connect(snapshot)) as dst,
        ):
            src.backup(dst, pages=64, progress=progress, sleep=0.02)
            if dst.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise OpsError("sqlite_integrity_failed")
        if any(_read(path, 65536) != content[name] for name, path in files.items()):
            raise OpsError("quiescent_sidecars_required")
        content["database.sqlite3"] = _read(snapshot, 8 << 20)
        header = {
            "schema": "openbot.encrypted-backup/1",
            "algorithm": "AES-256-GCM",
            "source_sha256": source_sha256,
            "created": int(time.time()),
            "files": {
                name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                for name, data in sorted(content.items())
            },
        }
        aad = canonical(header)
        nonce = os.urandom(12)
        plain = canonical({"files": {name: encode(data) for name, data in sorted(content.items())}})
        if len(plain) > MAX_BLOB - 16384:
            raise OpsError("backup_bound_exceeded")
        result = (
            b"OBBK1\n"
            + struct.pack("!I", len(aad))
            + aad
            + nonce
            + AESGCM(key).encrypt(nonce, plain, aad)
        )
        _write_new(directory / "encrypted", result)
        _rename_new(directory / "encrypted", target)
        return {
            "source_sha256": source_sha256,
            "encrypted_sha256": hashlib.sha256(result).hexdigest(),
            "files": header["files"],
            "production_backup_accepted": False,
            "key_distributed": False,
        }
    except (sqlite3.Error, OSError, ValueError) as exc:
        raise OpsError("bounded_encrypted_snapshot_failed") from exc
    finally:
        shutil.rmtree(directory)


def _decode_file(value):
    if not isinstance(value, str) or len(value) > MAX_BLOB:
        raise OpsError("encoded_member_bound")
    data = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    if encode(data) != value:
        raise OpsError("noncanonical_member_encoding")
    return data


def restore_backup(source, target, key, *, expected_source_sha256):
    """Authenticate ALL content before a private stage; atomically commit NEW only."""
    target = _path(target)
    _private(target.parent)
    if target.exists() or type(key) is not bytes or len(key) != 32:
        raise OpsError("new_target_and_separate_recovery_key_required")
    try:
        raw = _read(source)
        if raw[:6] != b"OBBK1\n" or len(raw) < 42:
            raise OpsError("invalid_backup")
        length = struct.unpack("!I", raw[6:10])[0]
        if not 0 < length <= 8192:
            raise OpsError("header_bound")
        aad = raw[10 : 10 + length]
        header = json.loads(aad)
        if (
            canonical(header) != aad
            or set(header) != {"schema", "algorithm", "source_sha256", "created", "files"}
            or header["schema"] != "openbot.encrypted-backup/1"
            or header["algorithm"] != "AES-256-GCM"
            or header["source_sha256"] != expected_source_sha256
            or set(header["files"]) != PARTS
        ):
            raise OpsError("bound_manifest_required")
        nonce = raw[10 + length : 22 + length]
        plain = AESGCM(key).decrypt(nonce, raw[22 + length :], aad)
        value = json.loads(plain)
        if canonical(value) != plain or set(value) != {"files"} or set(value["files"]) != PARTS:
            raise OpsError("exact_restore_members_required")
        content = {name: _decode_file(data) for name, data in value["files"].items()}
        for name, data in content.items():
            if len(data) > (8 << 20 if name == "database.sqlite3" else 65536) or header["files"][
                name
            ] != {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}:
                raise OpsError("authenticated_member_mismatch")
    except Exception as exc:
        raise OpsError("backup_authentication_or_manifest_refused") from exc
    stage = Path(tempfile.mkdtemp(prefix=".restore-", dir=target.parent))
    try:
        for name, data in content.items():
            _write_new(stage / name, data)
        with closing(
            sqlite3.connect((stage / "database.sqlite3").as_uri() + "?mode=ro", uri=True)
        ) as conn:
            if (
                conn.execute("PRAGMA integrity_check").fetchone() != ("ok",)
                or conn.execute("PRAGMA foreign_key_check").fetchall()
            ):
                raise OpsError("restored_database_integrity_failed")
        _sync(stage)
        _rename_new(stage, target)
        return {
            "integrity_check": "ok",
            "source_sha256": header["source_sha256"],
            "files": header["files"],
            "production_backup_accepted": False,
            "owner_key_recovery_accepted": False,
        }
    except (OSError, sqlite3.Error) as exc:
        raise OpsError("restore_readback_or_commit_failed") from exc
    finally:
        if stage.exists():
            shutil.rmtree(stage)


class OperatorGate:
    """Private operator DB. Runtime reads only; no public owner/pause grant route."""

    def __init__(self, root, *, initialize=False, admin=False, clock=time.time):
        if type(admin) is not bool or type(initialize) is not bool or (initialize and not admin):
            raise OpsError("explicit_host_setup_required")
        self.root = _private(root, initialize)
        self.path = self.root / "operations.sqlite3"
        self.admin = admin
        self.clock = clock
        if initialize:
            if self.path.exists():
                raise OpsError("existing_profile_refused")
            _write_new(self.path, b"")
            with self.connection(write=True) as conn:
                conn.executescript("""CREATE TABLE state(id INTEGER PRIMARY KEY CHECK(id=1),version INTEGER,profile TEXT,paused INTEGER,epoch INTEGER);
                  CREATE TABLE events(seq INTEGER PRIMARY KEY,kind TEXT,body TEXT,previous TEXT,sha TEXT);
                  CREATE TABLE signals(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT);
                  CREATE TRIGGER keep_events_u BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'immutable'); END;
                  CREATE TRIGGER keep_events_d BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'immutable'); END;""")
                conn.execute("INSERT INTO state VALUES(1,1,?,1,1)", (uuid.uuid4().hex,))
                self._append(
                    conn,
                    "pause",
                    {
                        "epoch": 1,
                        "paused": True,
                        "actor": "host:setup",
                        "decision_ref": "0" * 64,
                        "at": int(clock()),
                    },
                )
        self.status()

    @contextmanager
    def connection(self, write=False):
        _private(self.root)
        _sqlite_input(self.path, 4 << 20)
        if write and not self.admin:
            raise OpsError("protected_operator_authority_required")
        try:
            conn = sqlite3.connect(
                self.path.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=2
            )
            conn.row_factory = sqlite3.Row
            try:
                conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                with conn:
                    yield conn
            finally:
                conn.close()
        except (sqlite3.Error, ValueError, KeyError, TypeError) as exc:
            raise OpsError("operator_state_unavailable") from exc

    def _append(self, conn, kind, body):
        last = conn.execute("SELECT seq,sha FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        seq = last["seq"] + 1 if last else 1
        previous = last["sha"] if last else "0" * 64
        if seq > 4096:
            raise OpsError("operator_event_capacity_review_required")
        sha = digest({"seq": seq, "kind": kind, "body": body, "previous": previous})
        conn.execute(
            "INSERT INTO events VALUES(?,?,?,?,?)",
            (seq, kind, canonical(body).decode(), previous, sha),
        )

    def _state(self, conn):
        row = conn.execute("SELECT * FROM state WHERE id=1").fetchone()
        if not row or row["version"] != 1 or row["paused"] not in (0, 1) or row["epoch"] < 1:
            raise OpsError("compatible_operator_profile_required")
        previous = "0" * 64
        last_pause = None
        last_signal = None
        for count, event in enumerate(conn.execute("SELECT * FROM events ORDER BY seq"), 1):
            body = json.loads(event["body"])
            if (
                count > 4096
                or event["seq"] != count
                or event["previous"] != previous
                or event["sha"]
                != digest({"seq": count, "kind": event["kind"], "body": body, "previous": previous})
            ):
                raise OpsError("operator_audit_readback_failed")
            previous = event["sha"]
            if event["kind"] == "pause":
                last_pause = body
            if event["kind"] == "heartbeat":
                last_signal = body
        if (
            not last_pause
            or last_pause["epoch"] != row["epoch"]
            or last_pause["paused"] != bool(row["paused"])
        ):
            raise OpsError("operator_state_audit_mismatch")
        signal = conn.execute("SELECT body FROM signals WHERE id=1").fetchone()
        if (json.loads(signal["body"]) if signal else None) != last_signal:
            raise OpsError("operator_signal_audit_mismatch")
        return dict(row)

    def status(self):
        try:
            with self.connection() as conn:
                return self._state(conn)
        except (ValueError, KeyError, TypeError) as exc:
            raise OpsError("operator_readback_required") from exc

    def check(self):
        try:
            return self.status()["paused"] == 0
        except (OpsError, OSError):
            return False

    def binding(self):
        s = self.status()
        return {k: s[k] for k in ["profile", "epoch", "paused", "version"]}

    def pause(self, paused, *, actor, decision_ref):
        if (
            type(paused) is not bool
            or not re.fullmatch(r"human:[a-z0-9_-]{1,64}", actor or "")
            or not re.fullmatch(HEX, decision_ref or "")
        ):
            raise OpsError("exact_operator_decision_required")
        with self.connection(write=True) as conn:
            state = self._state(conn)
            epoch = state["epoch"] + 1
            self._append(
                conn,
                "pause",
                {
                    "epoch": epoch,
                    "paused": paused,
                    "actor": actor,
                    "decision_ref": decision_ref,
                    "at": int(self.clock()),
                },
            )
            conn.execute("UPDATE state SET paused=?,epoch=? WHERE id=1", (int(paused), epoch))
        return self.binding()

    def heartbeat(self, *, last_completed, due_at, failure, rss_bytes, disk_bytes, processes):
        body = {
            "last_completed": last_completed,
            "due_at": due_at,
            "failure": failure,
            "rss_bytes": rss_bytes,
            "disk_bytes": disk_bytes,
            "processes": processes,
            "at": int(self.clock()),
        }
        if (
            type(failure) is not bool
            or any(
                type(v) is not int or not 0 <= v < 2**63 for k, v in body.items() if k != "failure"
            )
            or last_completed > body["at"]
        ):
            raise OpsError("trusted_bounded_probe_required")
        with self.connection(write=True) as conn:
            self._state(conn)
            self._append(conn, "heartbeat", body)
            conn.execute("INSERT OR REPLACE INTO signals VALUES(1,?)", (canonical(body).decode(),))

    def signal(self):
        with self.connection() as conn:
            self._state(conn)
            row = conn.execute("SELECT body FROM signals WHERE id=1").fetchone()
            return json.loads(row["body"]) if row else None


class AlertWatchdog:
    """Separate-process-ready durable local outbox; stable IDs and exact ACKs.

    No production outbound transport is selected/enabled here. `send` must be a
    trusted bounded adapter; the executed drill uses only literal loopback HTTP.
    """

    def __init__(self, gate, root, *, limits, initialize=False, clock=time.time):
        self.gate = gate
        self.root = _private(root, initialize)
        self.path = self.root / "alerts.sqlite3"
        self.clock = clock
        if set(limits) != {"heartbeat_seconds", "rss_bytes", "disk_bytes", "processes"} or any(
            type(v) is not int or v < 1 for v in limits.values()
        ):
            raise OpsError("fixed_operator_alert_limits_required")
        self.limits = dict(limits)
        if initialize:
            if self.path.exists():
                raise OpsError("existing_alert_outbox_refused")
            _write_new(self.path, b"")
            with self.connection() as conn:
                conn.executescript("""CREATE TABLE alerts(id TEXT PRIMARY KEY,body TEXT NOT NULL,acked INTEGER NOT NULL CHECK(acked IN (0,1)));
                  CREATE TRIGGER alert_d BEFORE DELETE ON alerts BEGIN SELECT RAISE(ABORT,'retain-alert'); END;
                  CREATE TRIGGER alert_body BEFORE UPDATE OF id,body ON alerts BEGIN SELECT RAISE(ABORT,'immutable'); END;
                  CREATE TRIGGER alert_ack BEFORE UPDATE OF acked ON alerts WHEN OLD.acked=1 AND NEW.acked<>1 BEGIN SELECT RAISE(ABORT,'no-unack'); END;""")
        with self.connection() as conn:
            conn.execute("SELECT id,body,acked FROM alerts LIMIT 0")

    @contextmanager
    def connection(self):
        _private(self.root)
        _sqlite_input(self.path, 4 << 20)
        try:
            conn = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=2)
            try:
                conn.execute("BEGIN IMMEDIATE")
                with conn:
                    yield conn
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise OpsError("alert_outbox_unavailable") from exc

    body_digest = staticmethod(digest)

    def sample(self):
        try:
            signal = self.gate.signal()
            profile = self.gate.status()["profile"]
        except (OpsError, OSError):
            signal = None
            profile = digest(str(self.gate.root))
        now = int(self.clock())
        codes = []
        if (
            not signal
            or signal["at"] > now
            or now - signal["at"] > self.limits["heartbeat_seconds"]
        ):
            codes.append("heartbeat_lost")
        if signal:
            if signal["failure"]:
                codes.append("job_failure")
            if (
                signal["due_at"]
                and now > signal["due_at"]
                and signal["last_completed"] < signal["due_at"]
            ):
                codes.append("missed_job")
            for name in ["rss_bytes", "disk_bytes", "processes"]:
                if signal[name] > self.limits[name]:
                    codes.append("resource_" + name)
        with self.connection() as conn:
            if conn.execute("SELECT count(*) FROM alerts").fetchone()[0] >= 4096:
                raise OpsError("alert_capacity_operator_review_required")
            for code in codes:
                identity = digest({"profile": profile, "signal": signal, "code": code})
                body = {
                    "alert_id": identity,
                    "code": code,
                    "observed_at": now,
                    "signal": signal,
                    "production_oncall_accepted": False,
                }
                conn.execute(
                    "INSERT OR IGNORE INTO alerts VALUES(?,?,0)",
                    (identity, canonical(body).decode()),
                )
        return self.pending()

    def pending(self):
        with self.connection() as conn:
            return [
                {"id": row[0], **json.loads(row[1])}
                for row in conn.execute("SELECT id,body FROM alerts WHERE acked=0 ORDER BY rowid")
            ]

    def deliver(self, send):
        delivered = 0
        for row in self.pending()[:16]:
            body = {k: v for k, v in row.items() if k != "id"}
            try:
                ack = send(row["id"], body)
                if canonical(ack) != canonical(
                    {"accepted": True, "alert_id": row["id"], "body_sha256": digest(body)}
                ):
                    continue
            except Exception:
                continue
            with self.connection() as conn:
                cursor = conn.execute(
                    "UPDATE alerts SET acked=1 WHERE id=? AND acked=0", (row["id"],)
                )
                delivered += cursor.rowcount
        return delivered
