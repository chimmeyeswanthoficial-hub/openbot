#!/usr/bin/env python3
"""Actual disposable local execution/restart/cancellation proof. No auto-approval.

Generated state stays under excluded .cache; stdout is a credential-free receipt.
This is fixed Python tooling, not a live model turn or a hostile OS sandbox.
"""
from __future__ import annotations

import ctypes
import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "services/gateway/src"), str(ROOT / "services/sentinel")]
from local_executor import Authority, LocalExecutor  # noqa: E402


def request(*, tool="local.wordcount", delay_ms=0):
    return {"request_id": str(uuid.uuid4()), "tool": tool,
            "arguments": {"text": "Observe plan execute verify and report", "output": "result.json", "delay_ms": delay_ms}}


def parent_death_probe(base: Path):
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError("Cannot independently reap the disposable parent-death probe")
    state, body = base / "parent-death", request(delay_ms=3000)
    program = (
        "import sys,json;from pathlib import Path;"
        f"sys.path[:0]={sys.path[:2]!r};"
        "from local_executor import Authority,LocalExecutor;"
        "e=LocalExecutor(Path(sys.argv[1]),Authority('agent:probe','probe','person','parent-death'),capacity=1,timeout_s=4);"
        "e.execute(json.loads(sys.argv[2]))"
    )
    parent = subprocess.Popen([sys.executable, "-c", program, str(state), json.dumps(body)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    child_pid = None
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and parent.poll() is None:
            try:
                with closing(sqlite3.connect(f"file:{state / 'execution.sqlite3'}?mode=ro", uri=True)) as db:
                    row = db.execute("SELECT pid,events FROM local_jobs WHERE request_id=?", (body["request_id"],)).fetchone()
                    if row and row[0] and row[1] and json.loads(row[1])[0]["type"] == "RUN_STARTED":
                        child_pid = row[0]
                        break
            except sqlite3.OperationalError:
                time.sleep(0.01)
            else:
                time.sleep(0.01)
        if child_pid is None:
            raise RuntimeError("Disposable parent did not launch the real fixed worker")
        parent.kill()
        parent.wait(timeout=3)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            reaped, status = os.waitpid(child_pid, os.WNOHANG)
            if reaped:
                break
            time.sleep(0.01)
        else:
            raise RuntimeError("Parent-death guard did not terminate the fixed worker")
        assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
        restarted = LocalExecutor(state, Authority("agent:probe", "probe", "person", "parent-death"), capacity=1, timeout_s=4)
        try:
            reply = restarted.execute(body)
            assert reply["code"] == "reconciliation_required" and not reply["executed"]
            assert restarted.quota()["used_units"] == 1
        finally:
            restarted.close()
        return {"actual_parent_killed": True, "worker_pid": child_pid, "worker_exit_reaped": True,
                "worker_termination_signal": signal.SIGKILL, "interrupted_marker_not_reexecuted": True}
    finally:
        if parent.poll() is None:
            parent.kill()
        parent.wait(timeout=3)
        parent.stderr.close()


def main():
    (ROOT / ".cache").mkdir(exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="execution-demo-", dir=ROOT / ".cache"))
    identity = Authority("agent:cto", "execution-demo", "person", "operator-demo")
    executor = LocalExecutor(base / "kernel", identity, capacity=4)
    try:
        body = request()
        first = executor.execute(body)
        assert first["ok"] and first["executed"] and first["result"]["words"] == 6
        audit_count = executor.audit.audit_count()
        modified = Path(first["output_path"]).stat().st_mtime_ns
        executor.close()
        executor = LocalExecutor(base / "kernel", identity, capacity=4)
        replay = executor.execute(body)
        assert replay["ok"] and replay["replayed"] and not replay["executed"]
        assert replay["result"] == first["result"] and executor.audit.audit_count() == audit_count
        assert Path(replay["output_path"]).stat().st_mtime_ns == modified
        pending = executor.execute(request(tool="local.reviewed_wordcount"))
        assert pending["status"] == "gated" and not pending["executed"]
        denied = executor.execute(request(tool="browser.navigate"))
        assert not denied["ok"] and not denied["executed"]
        cancelled_body = request(delay_ms=2500)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(executor.execute, cancelled_body)
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                row = executor.job(cancelled_body["request_id"])
                if row and row["pid"]:
                    break
                time.sleep(0.01)
            else:
                raise RuntimeError("Cancellation probe did not launch")
            assert executor.cancel(cancelled_body["request_id"])["status"] == "cancel_requested"
            stopped = future.result(timeout=4)
        assert stopped["status"] == "cancelled" and stopped["child_exit_confirmed"]
        limited = LocalExecutor(base / "kernel", identity, capacity=4, timeout_s=0.15)
        try:
            timeout = limited.execute(request(delay_ms=2000))
            assert timeout["status"] == "timed_out" and timeout["child_exit_confirmed"]
        finally:
            limited.close()
        for pid in (stopped["pid"], timeout["pid"]):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                continue
            raise AssertionError("Worker still exists after confirmed stop")
        proof = parent_death_probe(base)
        receipt = {"observed_runner_utc": datetime.now(UTC).isoformat(), "passed": True,
                   "scope": "Actual fixed Linux subprocess and SSE pipe; no model/provider/network/payment/public deployment or hostile OS isolation.",
                   "request_id": body["request_id"], "result": first["result"], "event_types": [e["type"] for e in first["events"]],
                   "artifact_sha256": first["output_sha256"], "artifact_preview": json.loads(Path(first["output_path"]).read_text()),
                   "restart_replay_without_execution_or_redelivery": True, "outbox_rows_for_completed_request": executor.outbox_count(body["request_id"]),
                   "pending_review_was_not_autoapproved": True, "pending_approval_id": pending["approval_id"],
                   "unregistered_network_tool_refused": True, "cancelled_worker_exit_confirmed": True,
                   "deadline_worker_exit_confirmed": True, "parent_death_probe": proof,
                   "quota": executor.quota(), "quota_unit": "fixed execution attempts, not dollars", "cost_usd": 0, "providers_enabled": False,
                   "generated_state": str(base.relative_to(ROOT)), "limits": ["Host-only trusted authority/owner API, not remote authentication", "No arbitrary-code/tenant isolation", "No external delivery or financial budget proof"]}
        print(json.dumps(receipt, indent=2))
    finally:
        executor.close()


if __name__ == "__main__":
    main()
