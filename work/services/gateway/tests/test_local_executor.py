"""A real fixed subprocess must not turn a policy card into an execution permit."""
from __future__ import annotations

import dataclasses
import json
import os
import shutil
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from local_executor import Authority, LocalExecutor, Owner
from policy import Decision, Effect


def request(*, reviewed=False, text="one two three", delay_ms=0, output="count.json"):
    return {"request_id": str(uuid.uuid4()),
            "tool": "local.reviewed_wordcount" if reviewed else "local.wordcount",
            "arguments": {"text": text, "output": output, "delay_ms": delay_ms}}


@pytest.fixture
def executor(tmp_path):
    value = LocalExecutor(tmp_path / "kernel", Authority("agent:cto", "sandbox", "person", "test-order"), capacity=3)
    yield value
    value.close()


def wait_for_pid(executor, rid):
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        row = executor.job(rid)
        if row and row.get("pid"):
            return row["pid"]
        time.sleep(0.01)
    raise AssertionError("actual child process never started")


def test_real_child_stream_audit_delivery_and_no_inherited_keys(executor, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-must-not-reach-child")
    monkeypatch.setenv("SSH_AUTH_SOCK", "test-must-not-reach-child")
    body = request()
    result = executor.execute(body)
    assert result["ok"] and result["executed"] and not result["replayed"]
    assert result["result"]["words"] == 3 and result["result"]["characters"] == 13
    assert result["result"]["worker_pid"] != os.getpid()
    assert result["result"]["minimal_environment"] is True
    assert result["cost_usd"] == 0 and result["providers_enabled"] is False
    types = [event["type"] for event in result["events"]]
    assert types[0] == "RUN_STARTED" and types[-1] == "RUN_FINISHED"
    assert "TOOL_CALL_START" in types and "TEXT_MESSAGE_CONTENT" in types
    delivered = Path(result["output_path"])
    assert json.loads(delivered.read_text())["result"]["words"] == 3
    rows = list(reversed(executor.audit.audit_tail(100)))
    assert rows[0]["action"] == "file.write"
    assert [r["action"] for r in rows].index("local.execution.start") < [r["action"] for r in rows].index("local.execution.complete")
    assert rows[-1]["action"] == "local.delivery.complete"
    assert all(row["actor"] == "agent:cto" and row["initiator_kind"] == "person" for row in rows)
    assert executor.quota()["used_units"] == 1
    assert executor.outbox_count(body["request_id"]) == 1


@pytest.mark.parametrize("extra", ["actor", "venture", "initiator", "approval_id", "cost_usd", "command", "url"])
def test_request_cannot_supply_authority_payment_program_or_approval(executor, extra):
    body = request()
    body[extra] = "untrusted"
    result = executor.execute(body)
    assert not result["ok"] and not result["executed"]
    assert executor.quota()["used_units"] == 0


@pytest.mark.parametrize("output", ["../outside.json", "/tmp/outside.json", "other-venture/file.json", "x/../file.json", "..\\outside.json", "%2e%2e.json", ".env"])
def test_normalized_cross_venture_and_credential_paths_never_execute(executor, output):
    result = executor.execute(request(output=output))
    assert not result["ok"] and not result["executed"]
    assert executor.quota()["used_units"] == 0


@pytest.mark.parametrize("tool", ["browser.navigate", "http.request", "shell.exec", "gmail.send_message", "money"])
def test_unregistered_egress_shell_and_financial_tools_never_execute(executor, tool):
    body = request()
    body["tool"] = tool
    result = executor.execute(body)
    assert not result["ok"] and not result["executed"]


def test_secret_input_is_refused_without_persisting_it(executor):
    secret = "sk-" + "s" * 30
    result = executor.execute(request(text=secret))
    assert not result["ok"] and not result["executed"]
    for path in executor.state.glob("*.sqlite3"):
        assert secret.encode() not in path.read_bytes()


def test_authority_is_frozen_and_cannot_downgrade_unattended_initiator(executor):
    with pytest.raises(dataclasses.FrozenInstanceError):
        executor.authority.initiator = "person"
    other = LocalExecutor(executor.state, Authority("agent:cto", "sandbox", "routine", "nightly"), capacity=3)
    try:
        body = request(reviewed=True)
        assert executor.execute(body)["status"] == "gated"
        assert other.execute(body)["code"] == "request_conflict"
    finally:
        other.close()


def test_gate_is_bound_to_exact_arguments_and_only_host_owner_can_resolve(executor):
    body = request(reviewed=True)
    pending = executor.execute(body)
    assert pending["status"] == "gated" and not pending["executed"]
    assert executor.quota()["used_units"] == 0
    assert not executor.resolve(body["request_id"], "0" * 64, "approved", owner=Owner("human:owner"))
    assert not executor.resolve(body["request_id"], pending["request_digest"], "approved", owner=Owner("human:not-owner"))
    altered = {**body, "arguments": {**body["arguments"], "text": "changed draft"}}
    assert executor.execute(altered)["code"] == "request_conflict"
    assert executor.resolve(body["request_id"], pending["request_digest"], "approved", owner=Owner("human:owner"))
    assert not executor.resolve(body["request_id"], pending["request_digest"], "approved", owner=Owner("human:owner"))
    result = executor.execute(body)
    assert result["ok"] and result["result"]["words"] == 3


def test_denied_and_expired_approval_do_not_execute(executor):
    body = request(reviewed=True)
    pending = executor.execute(body)
    assert executor.resolve(body["request_id"], pending["request_digest"], "denied", owner=Owner("human:owner"))
    assert not executor.execute(body)["executed"]
    second = request(reviewed=True)
    pending = executor.execute(second)
    with sqlite3.connect(executor.state / "sentinel.sqlite3") as db:
        db.execute("UPDATE approvals SET created='2000-01-01T00:00:00Z' WHERE id=?", (pending["approval_id"],))
    assert not executor.resolve(second["request_id"], pending["request_digest"], "approved", owner=Owner("human:owner"))
    assert not executor.execute(second)["executed"]


@pytest.mark.parametrize("effect", [Effect.DENY, Effect.GATE, "unknown"])
def test_non_allow_policy_never_launches_child(executor, monkeypatch, effect):
    monkeypatch.setattr("local_executor.decide", lambda *_: Decision(effect, "test.rule", "fixture refusal"))
    result = executor.execute(request())
    assert not result["ok"] and not result["executed"]
    assert executor.quota()["used_units"] == 0


def test_audit_failure_refuses_before_launch(executor, monkeypatch):
    def unavailable(_store, _row):
        raise sqlite3.OperationalError("fixture store failure")
    monkeypatch.setattr(type(executor.audit), "audit", unavailable)
    result = executor.execute(request())
    assert not result["ok"] and not result["executed"]
    assert not list((executor.state / "outputs").rglob("count.json"))


def test_quota_reservation_is_transactional_across_executor_instances(tmp_path):
    state = tmp_path / "concurrent"
    identity = Authority("agent:cto", "sandbox", "routine", "quota-test")
    first = LocalExecutor(state, identity, capacity=1)
    second = LocalExecutor(state, identity, capacity=1)
    barrier = threading.Barrier(2)
    def execute(value):
        barrier.wait()
        return value.execute(request(delay_ms=200))
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(execute, [first, second]))
        assert sum(result["ok"] for result in results) == 1
        assert sum(result.get("code") == "quota_exhausted" for result in results) == 1
        assert first.quota()["used_units"] == 1
    finally:
        first.close()
        second.close()


def test_cancel_waits_for_real_child_exit_before_claiming_cancelled(executor):
    body = request(delay_ms=2500)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(executor.execute, body)
        pid = wait_for_pid(executor, body["request_id"])
        assert executor.cancel(body["request_id"])["status"] == "cancel_requested"
        result = future.result(timeout=4)
    assert result["status"] == "cancelled" and result["executed"]
    assert result["child_exit_confirmed"]
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
    assert executor.outbox_count(body["request_id"]) == 0
    assert not executor.execute(body)["ok"]  # no automatic repeat after cancellation


def test_deadline_terminates_real_process_not_just_http_wait(tmp_path):
    value = LocalExecutor(tmp_path / "timeout", Authority("agent:cto", "sandbox", "person", "timeout-test"), timeout_s=0.15)
    try:
        result = value.execute(request(delay_ms=2000))
        assert result["status"] == "timed_out" and result["child_exit_confirmed"]
        with pytest.raises(ProcessLookupError):
            os.kill(result["pid"], 0)
    finally:
        value.close()


def test_restart_replay_does_not_reexecute_or_redeliver(executor):
    body = request()
    first = executor.execute(body)
    target = Path(first["output_path"])
    before = target.stat().st_mtime_ns
    count = executor.audit.audit_count()
    restarted = LocalExecutor(executor.state, executor.authority, capacity=3)
    try:
        replay = restarted.execute(body)
        assert replay["ok"] and replay["replayed"] and not replay["executed"]
        assert replay["result"] == first["result"] and replay["output_sha256"] == first["output_sha256"]
        assert target.stat().st_mtime_ns == before
        assert restarted.audit.audit_count() == count
        assert restarted.outbox_count(body["request_id"]) == 1
        assert restarted.quota()["used_units"] == 1
    finally:
        restarted.close()


def test_interrupted_execution_requires_reconciliation_instead_of_repeat(executor):
    body = request(reviewed=True)
    pending = executor.execute(body)
    with sqlite3.connect(executor.state / "execution.sqlite3") as db:
        db.execute("UPDATE local_jobs SET status='running' WHERE request_id=?", (body["request_id"],))
    result = executor.execute(body)
    assert not result["ok"] and not result["executed"]
    assert result["code"] == "reconciliation_required"
    assert pending["approval_id"]


def test_completed_output_corruption_is_not_trusted(executor):
    body = request()
    first = executor.execute(body)
    Path(first["output_path"]).write_text("tampered result")
    result = executor.execute(body)
    assert not result["ok"] and result["code"] == "reconciliation_required"
    assert Path(first["output_path"]).read_text() == "tampered result"
    assert executor.quota()["used_units"] == 1


def test_pending_delivery_recovers_without_duplicate_child(executor, monkeypatch):
    original = type(executor.audit).audit
    def fail_completion(store, row):
        if row["action"] == "local.delivery.complete":
            raise sqlite3.OperationalError("fixture outage after local file delivery")
        return original(store, row)
    monkeypatch.setattr(type(executor.audit), "audit", fail_completion)
    body = request()
    first = executor.execute(body)
    assert not first["ok"] and first["executed"]
    job = executor.job(body["request_id"])
    pid = job["pid"]
    target = executor.state / "outputs" / "sandbox" / body["request_id"] / "count.json"
    before = target.stat().st_mtime_ns
    monkeypatch.setattr(type(executor.audit), "audit", original)
    result = executor.execute(body)
    assert result["ok"] and result["replayed"] and not result["executed"]
    assert result["result"]["worker_pid"] == pid and target.stat().st_mtime_ns == before
    assert executor.quota()["used_units"] == 1 and executor.outbox_count(body["request_id"]) == 1


def test_symlinked_delivery_target_cannot_touch_another_path(executor, tmp_path):
    body = request()
    directory = executor.state / "outputs" / "sandbox" / body["request_id"]
    directory.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text("preserve me")
    (directory / "count.json").symlink_to(outside)
    result = executor.execute(body)
    assert not result["ok"] and not result["executed"]
    assert outside.read_text() == "preserve me"


def test_recorded_quota_cannot_be_silently_widened_by_restart(executor):
    with pytest.raises(ValueError, match="quota"):
        LocalExecutor(executor.state, executor.authority, capacity=100)


def test_corrupted_outbox_cannot_redirect_delivery_outside_venture(executor, tmp_path):
    body = request()
    first = executor.execute(body)
    original = Path(first["output_path"]).read_bytes()
    outside = tmp_path / "must-not-be-created.json"
    with sqlite3.connect(executor.state / "execution.sqlite3") as db:
        db.execute("UPDATE local_outbox SET output_path=?,status='pending' WHERE request_id=?", (str(outside), body["request_id"]))
        db.execute("UPDATE local_jobs SET status='delivery_pending' WHERE request_id=?", (body["request_id"],))
    result = executor.execute(body)
    assert not result["ok"] and result["code"] == "reconciliation_required"
    assert not outside.exists()
    assert Path(first["output_path"]).read_bytes() == original
    assert executor.quota()["used_units"] == 1


def test_changed_stored_approval_preview_cannot_approve_another_draft(executor):
    body = request(reviewed=True)
    pending = executor.execute(body)
    approval = executor.audit.get_approval(pending["approval_id"])
    action = approval["action"]
    action["request"]["arguments"]["text"] = "different preview than executable draft"
    with sqlite3.connect(executor.state / "sentinel.sqlite3") as db:
        db.execute("UPDATE approvals SET action=? WHERE id=?", (json.dumps(action), pending["approval_id"]))
    assert not executor.resolve(body["request_id"], pending["request_digest"], "approved", owner=Owner("human:owner"))
    result = executor.execute(body)
    assert not result["ok"] and not result["executed"]
    assert executor.quota()["used_units"] == 0


def test_restored_state_replay_uses_restored_scope_not_old_absolute_paths(executor, tmp_path):
    body = request()
    first = executor.execute(body)
    executor.close()
    restored_path = tmp_path / "restored-kernel"
    shutil.copytree(executor.state, restored_path)
    restored = LocalExecutor(restored_path, executor.authority, capacity=3)
    try:
        replay = restored.execute(body)
        assert replay["ok"] and replay["replayed"] and not replay["executed"]
        assert Path(replay["output_path"]).is_relative_to(restored_path)
        assert replay["output_sha256"] == first["output_sha256"]
        assert replay["result"]["worker_pid"] == first["result"]["worker_pid"]
    finally:
        restored.close()


def test_changed_stored_request_cannot_redirect_delivery(executor):
    body = request()
    first = executor.execute(body)
    changed = {**body, "arguments": {**body["arguments"], "output": "redirected.json"}}
    target = Path(first["output_path"]).with_name("redirected.json")
    with sqlite3.connect(executor.state / "execution.sqlite3") as db:
        db.execute("UPDATE local_jobs SET request_json=?,status='delivery_pending' WHERE request_id=?", (json.dumps(changed), body["request_id"]))
        db.execute("UPDATE local_outbox SET output_path=?,status='pending' WHERE request_id=?", (target.relative_to(executor.state).as_posix(), body["request_id"]))
    replay = executor.execute(body)
    assert not replay["ok"] and not replay["executed"]
    assert not target.exists() and Path(first["output_path"]).is_file()


@pytest.mark.parametrize("field", ["result", "events"])
def test_replay_cannot_return_unaudited_result_or_stream(executor, field):
    body = request()
    first = executor.execute(body)
    changed = json.loads(executor.job(body["request_id"])[field])
    if field == "result":
        changed["words"] = 999
    else:
        changed[0]["runId"] = "a-different-run"
    with sqlite3.connect(executor.state / "execution.sqlite3") as db:
        db.execute(f"UPDATE local_jobs SET {field}=? WHERE request_id=?", (json.dumps(changed), body["request_id"]))
    replay = executor.execute(body)
    assert not replay["ok"] and not replay["executed"]
    assert json.loads(Path(first["output_path"]).read_text())["result"]["words"] == 3


def test_fifo_replay_output_refuses_without_blocking(executor):
    body = request()
    first = executor.execute(body)
    target = Path(first["output_path"])
    target.unlink()  # Disposable fixture, never business state.
    os.mkfifo(target)
    replay = executor.execute(body)
    assert not replay["ok"] and not replay["executed"]


def test_symlink_replay_output_refuses_even_when_bytes_match(executor, tmp_path):
    body = request()
    first = executor.execute(body)
    target = Path(first["output_path"])
    outside = tmp_path / "identical.json"
    outside.write_bytes(target.read_bytes())
    target.unlink()  # Disposable fixture, never business state.
    target.symlink_to(outside)
    replay = executor.execute(body)
    assert not replay["ok"] and not replay["executed"]
    assert json.loads(outside.read_text())["result"]["words"] == 3


def test_bounded_control_characters_do_not_overflow_worker_json_input(executor):
    result = executor.execute(request(text="\u0000" * 8192))
    assert result["ok"] and result["result"]["characters"] == 8192


def test_changed_mapper_implementation_invalidates_pending_approval(executor, monkeypatch):
    body = request(reviewed=True)
    pending = executor.execute(body)
    original = Path.read_bytes
    def changed(path):
        raw = original(path)
        return raw + b"\n# changed mapping fixture\n" if path.name == "mapper.py" else raw
    monkeypatch.setattr(Path, "read_bytes", changed)
    assert not executor.resolve(body["request_id"], pending["request_digest"], "approved", owner=Owner("human:owner"))
