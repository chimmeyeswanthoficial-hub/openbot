"""S11 local controls. Synthetic owners/keys, not witnessed production drills."""

from __future__ import annotations

import concurrent.futures
import os
import sqlite3
import uuid

import pytest
from operational_controls import (
    AlertWatchdog,
    OperatorGate,
    OpsError,
    backup_sqlite,
    restore_backup,
)
from work_service import AuthorityError, WorkService
from work_store import WorkError


@pytest.fixture
def gate(tmp_path):
    clock = [1000]
    admin = OperatorGate(tmp_path / "ops", initialize=True, admin=True, clock=lambda: clock[0])
    runtime = OperatorGate(tmp_path / "ops", clock=lambda: clock[0])
    return admin, runtime, clock


def test_new_operator_profile_starts_paused_and_runtime_cannot_resume(gate):
    admin, runtime, _ = gate
    assert runtime.check() is False
    assert runtime.status()["epoch"] == 1
    with pytest.raises(OpsError):
        runtime.pause(False, actor="human:unit", decision_ref="a" * 64)
    admin.pause(False, actor="human:unit", decision_ref="a" * 64)
    assert runtime.check() is True and runtime.binding()["epoch"] == 2
    admin.pause(True, actor="human:unit", decision_ref="b" * 64)
    assert runtime.check() is False and runtime.status()["epoch"] == 3


@pytest.mark.parametrize(
    "change", [{"actor": "agent:self"}, {"decision_ref": "not a review"}, {"paused": 1}]
)
def test_operator_changes_need_host_authority_and_exact_decision(gate, change):
    admin, _, _ = gate
    kwargs = {"paused": False, "actor": "human:unit", "decision_ref": "a" * 64, **change}
    with pytest.raises(OpsError):
        admin.pause(**kwargs)


def test_gate_schema_audit_and_state_tampering_fail_closed(gate):
    admin, runtime, _ = gate
    admin.pause(False, actor="human:unit", decision_ref="a" * 64)
    with sqlite3.connect(admin.path) as conn:
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("DELETE FROM events")
        conn.execute("UPDATE state SET paused=1")
    assert runtime.check() is False
    with pytest.raises(OpsError):
        runtime.binding()


def test_missing_gate_never_creates_an_implicit_profile(tmp_path):
    with pytest.raises(OpsError):
        OperatorGate(tmp_path / "not-there")
    assert not (tmp_path / "not-there").exists()


def test_gate_root_symlink_and_hardlinked_db_are_refused(gate, tmp_path):
    admin, _, _ = gate
    (tmp_path / "linked").symlink_to(admin.root, target_is_directory=True)
    with pytest.raises(OpsError):
        OperatorGate(tmp_path / "linked")
    os.link(admin.path, tmp_path / "other.db")
    assert admin.check() is False


@pytest.fixture
def backup_files(tmp_path):
    root = tmp_path / "source"
    root.mkdir(mode=0o700)
    database = root / "data.db"
    with sqlite3.connect(database) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE evidence(id INTEGER PRIMARY KEY,value TEXT NOT NULL)")
        conn.execute("INSERT INTO evidence VALUES(1,'owned fixture')")
        conn.execute(
            "CREATE TRIGGER immutable BEFORE DELETE ON evidence BEGIN SELECT RAISE(ABORT,'immutable'); END"
        )
    files = {name: root / name for name in ["config.json", "secrets.bin", "grants.json"]}
    files["config.json"].write_text('{"mode":"synthetic","network":"deny"}')
    files["secrets.bin"].write_bytes(os.urandom(48))
    files["grants.json"].write_text('{"runtime":{"read":true,"ddl":false}}')
    return database, files, os.urandom(32)


def make_backup(backup_files, tmp_path):
    db, files, key = backup_files
    target = tmp_path / "owned.enc"
    receipt = backup_sqlite(db, files, target, key, source_sha256="c" * 64)
    return target, key, receipt


def test_real_encrypted_sqlite_config_secret_grants_restore(backup_files, tmp_path):
    source, key, receipt = make_backup(backup_files, tmp_path)
    _, files, _ = backup_files
    raw = source.read_bytes()
    assert b"owned fixture" not in raw and files["secrets.bin"].read_bytes() not in raw
    result = restore_backup(source, tmp_path / "restored", key, expected_source_sha256="c" * 64)
    assert result["integrity_check"] == "ok" and result["source_sha256"] == receipt["source_sha256"]
    assert result["production_backup_accepted"] is False
    for name, path in files.items():
        assert (tmp_path / "restored" / name).read_bytes() == path.read_bytes()
    with sqlite3.connect(tmp_path / "restored/database.sqlite3") as conn:
        assert conn.execute("SELECT * FROM evidence").fetchall() == [(1, "owned fixture")]
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("DELETE FROM evidence")


@pytest.mark.parametrize("defect", ["wrong-key", "tamper", "truncated", "wrong-source"])
def test_backup_authentication_refuses_before_any_restore_output(backup_files, tmp_path, defect):
    source, key, _ = make_backup(backup_files, tmp_path)
    if defect == "wrong-key":
        key = os.urandom(32)
    if defect == "tamper":
        source.write_bytes(source.read_bytes()[:-1] + bytes([source.read_bytes()[-1] ^ 1]))
    if defect == "truncated":
        source.write_bytes(source.read_bytes()[:30])
    with pytest.raises(OpsError):
        restore_backup(
            source,
            tmp_path / "output",
            key,
            expected_source_sha256="d" * 64 if defect == "wrong-source" else "c" * 64,
        )
    assert not (tmp_path / "output").exists()


def test_backup_and_restore_never_overlay_existing_paths(backup_files, tmp_path):
    source, key, _ = make_backup(backup_files, tmp_path)
    before = source.read_bytes()
    with pytest.raises(OpsError):
        backup_sqlite(backup_files[0], backup_files[1], source, key, source_sha256="c" * 64)
    assert source.read_bytes() == before
    out = tmp_path / "existing"
    out.mkdir()
    (out / "marker").write_text("retain")
    with pytest.raises(OpsError):
        restore_backup(source, out, key, expected_source_sha256="c" * 64)
    assert (out / "marker").read_text() == "retain"


def test_two_actual_concurrent_restores_have_one_winner(backup_files, tmp_path):
    source, key, _ = make_backup(backup_files, tmp_path)

    def restore(_):
        try:
            return restore_backup(
                source, tmp_path / "shared", key, expected_source_sha256="c" * 64
            )["integrity_check"]
        except OpsError:
            return "refused"

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(restore, range(3)))
    assert results.count("ok") == 1 and results.count("refused") == 2


@pytest.mark.parametrize("bad", ["symlink", "hardlink", "missing", "extra-file", "bad-key"])
def test_backup_refuses_unsafe_input_and_schema(backup_files, tmp_path, bad):
    database, files, key = backup_files
    if bad == "symlink":
        p = files["config.json"]
        real = p.with_suffix(".real")
        p.rename(real)
        p.symlink_to(real)
    if bad == "hardlink":
        os.link(files["secrets.bin"], tmp_path / "linked-secret")
    if bad == "missing":
        files.pop("grants.json")
    if bad == "extra-file":
        files["../authority.json"] = files["config.json"]
    if bad == "bad-key":
        key = b"short"
    with pytest.raises(OpsError):
        backup_sqlite(database, files, tmp_path / "refused.enc", key, source_sha256="c" * 64)
    assert not (tmp_path / "refused.enc").exists()


def test_watchdog_detects_failure_missed_job_resources_and_heartbeat(gate, tmp_path):
    admin, runtime, clock = gate
    admin.heartbeat(
        last_completed=900, due_at=950, failure=True, rss_bytes=101, disk_bytes=201, processes=4
    )
    monitor = AlertWatchdog(
        runtime,
        tmp_path / "alerts",
        limits={"heartbeat_seconds": 10, "rss_bytes": 100, "disk_bytes": 200, "processes": 3},
        initialize=True,
        clock=lambda: clock[0],
    )
    first = monitor.sample()
    assert {x["code"] for x in first} == {
        "job_failure",
        "missed_job",
        "resource_rss_bytes",
        "resource_disk_bytes",
        "resource_processes",
    }
    assert len(monitor.sample()) == len(first)
    clock[0] += 11
    assert "heartbeat_lost" in {x["code"] for x in monitor.sample()}
    assert len(monitor.pending()) == 6


def test_alert_queue_restart_wrong_ack_and_transport_loss_never_claim_delivery(gate, tmp_path):
    _admin, runtime, _ = gate
    limits = {"heartbeat_seconds": 10, "rss_bytes": 100, "disk_bytes": 200, "processes": 3}
    first = AlertWatchdog(
        runtime, tmp_path / "alerts", limits=limits, initialize=True, clock=lambda: 1000
    )
    first.sample()
    identity = first.pending()[0]["id"]

    def lost(_id, _body):
        raise TimeoutError("fixture network loss")

    assert first.deliver(lost) == 0 and first.pending()[0]["id"] == identity
    second = AlertWatchdog(runtime, tmp_path / "alerts", limits=limits, clock=lambda: 1000)
    assert second.pending()[0]["id"] == identity
    assert (
        second.deliver(lambda i, b: {"accepted": True, "alert_id": i, "body_sha256": "0" * 64}) == 0
    )
    assert (
        second.deliver(
            lambda i, b: {"accepted": True, "alert_id": i, "body_sha256": second.body_digest(b)}
        )
        == 1
    )
    assert second.pending() == []


def intake():
    return {
        "request_id": str(uuid.uuid4()),
        "fixture": "invoice-good-v1",
        "goal": "Owned pause drill",
        "acceptance": "Independent fixed QA assertions",
        "rights_ref": "owned:seed",
        "ai_use_approved": True,
        "destination": "local-review",
    }


def test_work_gate_stops_proposal_approval_and_pre_effect_but_not_reads_or_cancel(
    durable_backend, tmp_path
):
    b = durable_backend
    admin = OperatorGate(tmp_path / "ops", initialize=True, admin=True, clock=lambda: b.clock[0])
    gate = OperatorGate(tmp_path / "ops", clock=lambda: b.clock[0])
    issuer = WorkService(b.provision, enabled=True)
    agent = issuer.issue_session(
        actor="agent:qa",
        venture="demo",
        role="agent",
        initiator={"kind": "handoff", "id": "owned-ops"},
    )
    owner = issuer.issue_session(
        actor="human:unit",
        venture="demo",
        role="owner",
        initiator={"kind": "person", "id": "owned-ops"},
    )
    service = WorkService(b.work, enabled=True, operator_gate=gate)
    with pytest.raises(AuthorityError):
        service.prepare(agent, intake())
    admin.pause(False, actor="human:unit", decision_ref="a" * 64)
    task = service.prepare(agent, intake())
    service.approve(owner, task["id"], task["spec_digest"])
    admin.pause(True, actor="human:unit", decision_ref="b" * 64)
    assert service.task(agent, task["id"])[1]["id"] == task["id"]
    with pytest.raises((AuthorityError, WorkError)):
        service.execute(agent, task["id"])
    assert b.work.get(task["id"])["attempted"] == 0
    assert service.cancel(agent, task["id"])["requested"] is True


def test_resume_epoch_does_not_resurrect_an_old_exact_approval(durable_backend, tmp_path):
    b = durable_backend
    admin = OperatorGate(tmp_path / "ops", initialize=True, admin=True, clock=lambda: b.clock[0])
    admin.pause(False, actor="human:unit", decision_ref="a" * 64)
    issuer = WorkService(b.provision, enabled=True)
    token = issuer.issue_session(
        actor="human:unit",
        venture="demo",
        role="owner",
        initiator={"kind": "person", "id": "owned-ops"},
    )
    service = WorkService(
        b.work, enabled=True, operator_gate=OperatorGate(tmp_path / "ops", clock=lambda: b.clock[0])
    )
    task = service.prepare(token, intake())
    service.approve(token, task["id"], task["spec_digest"])
    admin.pause(True, actor="human:unit", decision_ref="b" * 64)
    admin.pause(False, actor="human:unit", decision_ref="c" * 64)
    with pytest.raises(WorkError):
        service.execute(token, task["id"])
    assert b.work.get(task["id"])["attempted"] == 0


def test_boolean_like_ack_is_not_an_explicit_collector_acceptance(gate, tmp_path):
    _, runtime, _ = gate
    monitor = AlertWatchdog(
        runtime,
        tmp_path / "alerts",
        limits={"heartbeat_seconds": 10, "rss_bytes": 100, "disk_bytes": 200, "processes": 3},
        initialize=True,
        clock=lambda: 1000,
    )
    monitor.sample()
    assert (
        monitor.deliver(
            lambda i, b: {"accepted": 1, "alert_id": i, "body_sha256": monitor.body_digest(b)}
        )
        == 0
    )
    assert len(monitor.pending()) == 1


def test_runtime_gate_fails_closed_if_private_directory_becomes_public(gate):
    admin, runtime, _ = gate
    admin.pause(False, actor="human:unit", decision_ref="a" * 64)
    admin.root.chmod(0o755)
    assert runtime.check() is False


def test_work_service_never_accepts_json_or_write_authority_as_operator_gate(durable_backend, gate):
    admin, _, _ = gate
    for fake in [{"paused": False}, admin]:
        with pytest.raises(WorkError):
            WorkService(durable_backend.work, enabled=True, operator_gate=fake)


def test_pause_between_claim_and_effect_revalidates_the_operator_gate(
    durable_backend, tmp_path, monkeypatch
):
    b = durable_backend
    admin = OperatorGate(tmp_path / "ops", initialize=True, admin=True, clock=lambda: b.clock[0])
    admin.pause(False, actor="human:unit", decision_ref="a" * 64)
    token = WorkService(b.provision, enabled=True).issue_session(
        actor="human:unit",
        venture="demo",
        role="owner",
        initiator={"kind": "person", "id": "unit-pause-race"},
    )
    service = WorkService(b.work, enabled=True, operator_gate=OperatorGate(admin.root))
    task = service.prepare(token, intake())
    service.approve(token, task["id"], task["spec_digest"])
    claim = b.work.claim

    def pause_after_claim(*args, **kwargs):
        fence = claim(*args, **kwargs)
        admin.pause(True, actor="human:unit", decision_ref="b" * 64)
        return fence

    monkeypatch.setattr(b.work, "claim", pause_after_claim)
    result = service.execute(token, task["id"])
    assert result["status"] == "blocked" and result["attempted"] == 0


def test_active_actual_qa_child_observes_pause_and_is_reaped(
    durable_backend, tmp_path, monkeypatch
):
    if os.environ.get("OPENBOT_TEST_NAMESPACE") != "1":
        pytest.skip("explicit namespace test opt-in required")
    import isolation

    b = durable_backend
    admin = OperatorGate(tmp_path / "ops", initialize=True, admin=True, clock=lambda: b.clock[0])
    admin.pause(False, actor="human:unit", decision_ref="a" * 64)
    token = WorkService(b.provision, enabled=True).issue_session(
        actor="human:unit",
        venture="demo",
        role="owner",
        initiator={"kind": "person", "id": "unit-running-pause"},
    )
    service = WorkService(b.work, enabled=True, operator_gate=OperatorGate(admin.root))
    task = service.prepare(token, intake())
    service.approve(token, task["id"], task["spec_digest"])
    original = isolation.run_fixed

    def paused_actual_launch(mode, body, **kwargs):
        return original(
            mode,
            body,
            **kwargs,
            on_start=lambda _pid: admin.pause(True, actor="human:unit", decision_ref="b" * 64),
        )

    monkeypatch.setattr(isolation, "run_fixed", paused_actual_launch)
    result = service.execute(token, task["id"])
    assert result["status"] == "cancelled" and result["result"]["terminal"] == "cancelled"
    assert result["result"]["child_exit_confirmed"] is True
    with pytest.raises(ProcessLookupError):
        os.kill(result["result"]["pid"], 0)
    with b.work.tx() as cursor:
        b.work.q(cursor, "SELECT COUNT(*) AS n FROM work_v1_outbox WHERE task_id=?", (task["id"],))
        assert b.work.rows(cursor)[0]["n"] == 0


def test_sqlite_backup_copies_committed_wal_not_uncommitted_changes(backup_files, tmp_path):
    database, files, key = backup_files
    conn = sqlite3.connect(database)
    try:
        conn.execute("INSERT INTO evidence VALUES(2,'committed WAL')")
        conn.commit()
        conn.execute("INSERT INTO evidence VALUES(3,'uncommitted')")
        source = tmp_path / "wal.enc"
        backup_sqlite(database, files, source, key, source_sha256="c" * 64)
        restore_backup(source, tmp_path / "wal-restored", key, expected_source_sha256="c" * 64)
        with sqlite3.connect(tmp_path / "wal-restored/database.sqlite3") as recovered:
            assert recovered.execute("SELECT id FROM evidence ORDER BY id").fetchall() == [
                (1,),
                (2,),
            ]
    finally:
        conn.rollback()
        conn.close()
