#!/usr/bin/env python3
"""Bot HQ's ONLY executable company tool in the installed local profile.

Fixed inputs, fixed zero-cost implementation, independent Sentinel policy/audit, no
network/model/shell/browser driver. This adapter is NOT an OS sandbox. Root/state
paths are operator startup configuration, never request fields. Interrupted jobs
require inspection, not an automatic retry with a fresh identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import stat
import sys
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

# Collection may work elsewhere; execution still requires the measured Linux controls.
try:
    import fcntl
except ImportError:
    fcntl = None

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services/sentinel"))
from policy import Action, Effect, EgressMode, VenturePolicy, decide  # noqa: E402
from repository import Store  # noqa: E402

INPUTS = (
    ".openbot/state/budget.json",
    ".openbot/state/active_ventures.yaml",
    "audit/verification-current.json",
)
MAX_INPUT_BYTES = 131_072
MAX_REQUEST_BYTES = 4096
POLICY_PATH = "company/hq-local-policy.json"
POLICY = {
    "version": 1, "enabled": True, "egress_mode": "deny_all", "auto_spend_usd": 0,
    "allowed_actions": ["company.readiness"],
}


class EvidenceError(ValueError):
    pass


class AuditUnavailable(RuntimeError):
    pass


@contextmanager
def open_store(path: Path):
    """Lifecycle wrapper; the existing Store does not yet expose a public close()."""
    store = Store(str(path))
    try:
        yield store
    finally:
        store._conn.close()


def _regular_bytes(root: Path, rel: str, limit: int = MAX_INPUT_BYTES) -> bytes:
    """Walk fixed relative paths using directory FDs; never follow a symlink component."""
    parts = Path(rel).parts
    if not parts or Path(rel).is_absolute() or any(p in ("..", ".") for p in parts):
        raise EvidenceError("invalid fixed path")
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(leaf, "rb") as stream:
            meta = os.fstat(stream.fileno())
            if not stat.S_ISREG(meta.st_mode) or meta.st_size > limit:
                raise EvidenceError("not a bounded regular file")
            data = stream.read(limit + 1)
            if len(data) > limit:
                raise EvidenceError("evidence exceeds limit")
            return data
    finally:
        os.close(fd)


def read_evidence(root: Path, rel: str, **kwargs) -> bytes:
    if rel not in INPUTS:
        raise EvidenceError("not an allowed input")
    return _regular_bytes(root, rel, **kwargs)


def _private_dir(path: Path) -> None:
    # Operator-owned state, never supplied in a request. Refuse symlinked state components.
    for parent in [*reversed(path.parents), path]:
        if parent.is_symlink():
            raise EvidenceError("symlinked state directory")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.is_dir() or path.is_symlink():
        raise EvidenceError("invalid state directory")


def _exclusive_json(path: Path, data: dict) -> str:
    encoded = (json.dumps(data, indent=2, allow_nan=False) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return hashlib.sha256(encoded).hexdigest()


def _audit(store: Store, row: dict) -> int:
    try:
        return store.audit(row)
    except (OSError, sqlite3.Error) as exc:
        raise AuditUnavailable from exc


def _refuse(store: Store, code: str, request_id: str = "invalid") -> dict:
    run_id = "hq_refused_" + uuid.uuid4().hex[:16]
    seq = _audit(store, {
        "run_id": run_id, "venture": "platform-hq", "actor": "bot:hq-local",
        "action": "hq.report.request", "decision": "deny", "rule": code,
        "reason": "Local HQ profile refuses this request; no tool executed",
        "initiator": {"kind": "person", "id": request_id}, "cost_usd": 0,
        "target": {"request_id": request_id},
    })
    return {"ok": False, "executed": False, "replayed": False,
            "code": code, "run_id": run_id, "audit_seq": seq}


def _number(value: Any) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise EvidenceError("invalid budget value")
    return value


def _snapshot(raw: dict[str, bytes]) -> dict:
    budget = json.loads(raw[INPUTS[0]])
    ventures = yaml.safe_load(raw[INPUTS[1]])
    verification = json.loads(raw[INPUTS[2]])
    if not all(isinstance(obj, dict) for obj in (budget, ventures, verification)):
        raise EvidenceError("expected bounded objects")
    counts = verification.get("python")
    names = ("passed", "skipped", "failed", "collected")
    if not isinstance(counts, dict) or any(type(counts.get(k)) is not int or counts[k] < 0
                                            for k in names):
        raise EvidenceError("invalid recorded outcomes")
    if counts["passed"] + counts["skipped"] + counts["failed"] != counts["collected"]:
        raise EvidenceError("recorded outcome arithmetic is inconsistent")
    items = ventures.get("ventures")
    if not isinstance(items, list) or len(items) > 100:
        raise EvidenceError("invalid ventures list")
    slugs = []
    for item in items:
        if not isinstance(item, dict) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", str(item.get("slug", ""))):
            raise EvidenceError("invalid venture identity")
        slugs.append(item["slug"])
    paused = budget.get("paused", False)
    if type(paused) is not bool:
        raise EvidenceError("invalid pause value")
    return {
        "company_paused": paused,
        "company_day_cap_usd": _number(budget.get("company_day_cap_usd", 0)),
        "recorded_spent_today_usd": _number(budget.get("spent_today_usd", 0)),
        "active_venture_count": len(items), "venture_slugs": slugs,
        "python": {key: counts[key] for key in names},
        "evidence_is_a_recorded_snapshot_not_a_new_test_run": True,
    }


def _run_locked(request: Any, root: Path, state_dir: Path, store: Store) -> dict:
    if not isinstance(request, dict):
        return _refuse(store, "hq.arguments_not_supported")
    request_id = request.get("request_id")
    try:
        valid = isinstance(request_id, str) and str(uuid.UUID(request_id)) == request_id
    except (ValueError, AttributeError):
        valid = False
    if not valid:
        return _refuse(store, "hq.invalid_request_id")
    if set(request) != {"request_id", "action"}:
        return _refuse(store, "hq.arguments_not_supported", request_id)
    if request.get("action") != "company.readiness":
        return _refuse(store, "hq.action_not_supported", request_id)
    try:
        if json.loads(_regular_bytes(root, POLICY_PATH, 4096)) != POLICY:
            raise EvidenceError("policy cannot widen the local implementation")
    except (OSError, ValueError, TypeError):
        return _refuse(store, "hq.policy_unavailable", request_id)

    digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    report_path = state_dir / "reports" / f"{request_id}.json"
    marker = state_dir / "markers" / f"{request_id}.json"
    if report_path.exists():
        try:
            report_bytes = _regular_bytes(state_dir, f"reports/{request_id}.json")
            report = json.loads(report_bytes)
            report_sha256 = hashlib.sha256(report_bytes).hexdigest()
            if report["request_digest"] != digest:
                raise EvidenceError("identity conflict")
            # A file alone is not authority: require its persisted complete run and audit rows.
            runs = store.runs(limit=1000)
            if not any(r["id"] == report["run_id"] and r["status"] == "ok" for r in runs):
                raise EvidenceError("run is not durably complete")
            rows = store.audit_tail(limit=1000)
            completion = next((r for r in rows if r["run_id"] == report["run_id"]
                               and r["action"] == "hq.report.complete" and r["decision"] == "allow"
                               and r["target"].get("report_sha256") == report_sha256), None)
            if completion is None:
                raise EvidenceError("completion audit or report integrity missing")
            return {"ok": True, "executed": False, "replayed": True, "report": report,
                    "report_sha256": report_sha256, "audit_seqs": [*report["audit_seqs"], completion["seq"]]}
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            return _refuse(store, "hq.reconciliation_required", request_id)
    if marker.exists() or marker.is_symlink():
        return _refuse(store, "hq.reconciliation_required", request_id)

    run_id = store.start_run("hq-company-readiness", "platform-hq")
    seqs = [_audit(store, {
        "run_id": run_id, "venture": "platform-hq", "actor": "bot:hq-local",
        "action": "hq.report.request", "decision": "allow", "rule": "hq.fixed_local_report",
        "reason": "One fixed zero-cost read-only company evidence report",
        "initiator": {"kind": "person", "id": request_id}, "cost_usd": 0,
        "target": {"request_id": request_id, "request_digest": digest},
    })]
    _exclusive_json(marker, {"request_id": request_id, "request_digest": digest, "run_id": run_id})
    policy = VenturePolicy(slug="platform-hq", egress_mode=EgressMode.DENY_ALL,
                           allowed_write_roots=(str(state_dir / "reports"),))
    try:
        raw = {}
        for rel in INPUTS:
            action = Action(kind="file.read", actor="bot:hq-local", venture="platform-hq",
                            name="read company readiness evidence", path=rel,
                            initiator_id=request_id, cost_usd=0)
            verdict = decide(action, policy)
            seqs.append(_audit(store, {**verdict.as_audit(action), "run_id": run_id}))
            if verdict.effect is not Effect.ALLOW:
                raise EvidenceError("independent policy refused")
            raw[rel] = read_evidence(root, rel)
        snapshot = _snapshot(raw)
        output_action = Action(kind="file.write", actor="bot:hq-local", venture="platform-hq",
                               name="write local readiness report", path=str(report_path),
                               initiator_id=request_id, cost_usd=0)
        verdict = decide(output_action, policy)
        seqs.append(_audit(store, {**verdict.as_audit(output_action), "run_id": run_id}))
        if verdict.effect is not Effect.ALLOW:
            raise EvidenceError("independent policy refused report output")
        report = {
            "schema": 1, "request_id": request_id, "request_digest": digest,
            "run_id": run_id, "audit_seqs": seqs,
            "observed_at_utc": datetime.now(UTC).isoformat(),
            "providers_enabled": False, "cost_usd": 0, "snapshot": snapshot,
            "inputs": [{"path": rel, "bytes": len(raw[rel]),
                        "sha256": hashlib.sha256(raw[rel]).hexdigest()} for rel in INPUTS],
            "limits": ["Recorded input evidence can be stale; this does not rerun verification",
                       "No release approval, real provider, shell, browser or payment executed",
                       "Same-user local adapter, not OS-level or hostile-process isolation"],
        }
        report_sha256 = _exclusive_json(report_path, report)
        completion_seq = _audit(store, {
            "run_id": run_id, "venture": "platform-hq", "actor": "bot:hq-local",
            "action": "hq.report.complete", "decision": "allow", "rule": "hq.report_integrity",
            "reason": "Exact report bytes durably written; digest binds replay to audit",
            "initiator": {"kind": "person", "id": request_id}, "cost_usd": 0,
            "target": {"request_id": request_id, "report_sha256": report_sha256},
        })
        store.end_run(run_id, "ok", 0, f"fixed local report {request_id}; three hashed inputs")
        return {"ok": True, "executed": True, "replayed": False, "report": report,
                "report_sha256": report_sha256, "audit_seqs": [*seqs, completion_seq]}
    except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
        # Do not echo potentially sensitive file contents or OS paths to the UI.
        store.end_run(run_id, "error", 0, type(exc).__name__)
        return _refuse(store, "hq.evidence_unavailable", request_id)


def run_request(request: Any, *, root: Path = ROOT, state_dir: Path | None = None) -> dict:
    # Never trade mandatory locking/path semantics for import-time portability.
    # No state was accessed here, so no durable refusal audit is claimed.
    if not sys.platform.startswith("linux") or fcntl is None:
        return {"ok": False, "executed": False, "replayed": False,
                "code": "hq.platform_unavailable"}
    root = Path(root).absolute()
    state_dir = Path(state_dir or root / ".openbot/hq-kernel").absolute()
    try:
        _private_dir(state_dir)
        _private_dir(state_dir / "reports")
        _private_dir(state_dir / "markers")
        if (state_dir / "sentinel.sqlite3").is_symlink():
            raise EvidenceError("invalid audit path")
        lock_fd = os.open(state_dir / "jobs.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(lock_fd, "a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return {"ok": False, "executed": False, "code": "hq.busy"}
            with open_store(state_dir / "sentinel.sqlite3") as store:
                return _run_locked(request, root, state_dir, store)
    except (AuditUnavailable, OSError, sqlite3.Error, EvidenceError):
        request_id = request.get("request_id", "") if isinstance(request, dict) else ""
        valid_id = isinstance(request_id, str) and re.fullmatch(r"[a-f0-9-]{36}", request_id)
        uncertain = bool(valid_id and (state_dir / "markers" / f"{request_id}.json").exists())
        # executed=False means no COMPLETE report execution is claimed. A persisted marker
        # explicitly signals possible partial reads/writes; it must not be treated as no attempt.
        return {"ok": False, "executed": False, "replayed": False,
                "outcome_uncertain": uncertain, "code": "hq.audit_unavailable"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--state-dir", type=Path)
    args = parser.parse_args()
    raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    try:
        request = json.loads(raw) if len(raw) <= MAX_REQUEST_BYTES else None
    except (ValueError, UnicodeDecodeError):
        request = None
    print(json.dumps(run_request(request, root=args.root, state_dir=args.state_dir), allow_nan=False))


if __name__ == "__main__":
    main()
