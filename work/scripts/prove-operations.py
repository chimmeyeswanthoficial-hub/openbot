#!/usr/bin/env python3
"""Actual LOCAL synthetic S11 drill; no production rollout, key custody or on-call.

NEW excluded-cache outputs only. Own SQLite/config/secrets/grants, memory-only
backup key, real namespace QA, killed restore/worker/watchdog processes, actual
loopback HTTP collector. Never distribute private profiles/DBs or orphan stages.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import multiprocessing as mp
import os
import re
import sqlite3
import sys
import time
import uuid
from contextlib import closing, suppress
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for relative in ["services/gateway/src", "services/sentinel", "services/worker/src"]:
    sys.path.insert(0, str(ROOT / relative))
from operational_controls import (  # noqa: E402
    AlertWatchdog,
    OperatorGate,
    OpsError,
    backup_sqlite,
    restore_backup,
)  # noqa: E402
from repository import Store  # noqa: E402
from trust_crypto import canonical, digest  # noqa: E402
from work_service import AuthorityError, WorkService  # noqa: E402
from work_store import WorkStore  # noqa: E402

LIMITS = {"heartbeat_seconds": 1, "rss_bytes": 1 << 30, "disk_bytes": 1 << 28, "processes": 8}


def receive(pipe, predicate=lambda _value: True, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not pipe.poll(max(0, deadline - time.monotonic())):
            break
        value = pipe.recv()
        if predicate(value):
            return value
    raise TimeoutError("owned fixture process did not reach its bounded checkpoint")


def restore_child(source, target, key, source_sha, pipe, checkpoint=None):
    import operational_controls as ops

    if checkpoint:
        original = ops._rename_new

        def stop_at_commit(stage, destination):
            if checkpoint == "after":
                original(stage, destination)
            pipe.send({"checkpoint": checkpoint, "target_exists": Path(destination).exists()})
            # Parent deliberately SIGKILLs this exact spawned fixture process.
            time.sleep(30)
            raise RuntimeError("parent failed to kill the fixture within its bound")

        ops._rename_new = stop_at_commit
    pipe.send(restore_backup(source, target, key, expected_source_sha256=source_sha))


def slow_owned_child(root, pipe):
    import isolation

    gate = OperatorGate(root)
    result = isolation.run_fixed(
        "wordcount",
        {"request_id": str(uuid.uuid4()), "text": "owned pause drill", "delay_ms": 3000},
        timeout_s=4,
        cancelled=lambda: not gate.check(),
        on_start=lambda pid: pipe.send({"child_pid": pid}),
    )
    pipe.send({"terminal": result.terminal, "returncode": result.returncode, "pid": result.pid})


def producer(root, pipe, stop):
    import resource

    admin = OperatorGate(root, admin=True)
    first = True
    while not stop.is_set():
        now = int(time.time())
        admin.heartbeat(
            last_completed=now,
            due_at=0,
            failure=False,
            rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            disk_bytes=sum(p.stat().st_size for p in Path(root).glob("*") if p.is_file()),
            processes=1,
        )
        if first:
            pipe.send({"kind": "producer-ready", "pid": os.getpid()})
            first = False
        stop.wait(0.2)


def watcher(root, outbox, pipe, stop, initialize, port):
    monitor = AlertWatchdog(OperatorGate(root), outbox, limits=LIMITS, initialize=initialize)
    attempts = 0

    def send(identity, body):
        nonlocal attempts
        attempts += 1
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=0.5)
        try:
            connection.request(
                "POST",
                "/alerts",
                body=canonical({"id": identity, "body": body}),
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            raw = response.read(4097)
            if response.status != 200 or len(raw) > 4096:
                raise ValueError("bounded ACK refused")
            return json.loads(raw)
        finally:
            connection.close()

    def pending():
        return [row["id"] for row in monitor.pending()]

    pipe.send({"kind": "watcher-ready", "pending_ids": pending(), "pid": os.getpid()})
    previous = None
    while not stop.is_set():
        monitor.sample()
        delivered = monitor.deliver(send)
        ids = pending()
        state = {
            "kind": "state",
            "pending_ids": ids,
            "delivered_this_cycle": delivered,
            "transport_attempts": attempts,
        }
        if ids != previous:
            pipe.send(state)
            previous = ids
        if pipe.poll():
            command = pipe.recv()
            if command == "snapshot":
                pipe.send({**state, "kind": "snapshot"})
        stop.wait(0.1)


def collector(root, pipe, stop):
    folder = Path(root)
    folder.mkdir(mode=0o700)
    connection = sqlite3.connect(folder / "received.sqlite3")
    connection.execute("CREATE TABLE received(id TEXT PRIMARY KEY,body_sha TEXT NOT NULL)")
    connection.commit()
    bad_ack = True

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "-1"))
                if self.path != "/alerts" or not 0 < length <= 65536:
                    raise ValueError("bounded local protocol")
                value = json.loads(self.rfile.read(length))
                identity = value["id"]
                body = value["body"]
                sha = digest(body)
                if set(value) != {"id", "body"} or identity != body["alert_id"]:
                    raise ValueError("bound alert ID")
                if not bad_ack:
                    old = connection.execute(
                        "SELECT body_sha FROM received WHERE id=?", (identity,)
                    ).fetchone()
                    if old and old != (sha,):
                        raise ValueError("same ID different body")
                    connection.execute(
                        "INSERT OR IGNORE INTO received VALUES(?,?)", (identity, sha)
                    )
                    connection.commit()
                reply = {
                    "accepted": True,
                    "alert_id": identity,
                    "body_sha256": "0" * 64 if bad_ack else sha,
                }
                raw = canonical(reply)
                self.send_response(200)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                pipe.send(
                    {"kind": "http", "correct_ack": not bad_ack, "id": identity, "body_sha256": sha}
                )
            except (ValueError, KeyError, TypeError):
                self.send_error(400)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.timeout = 0.1
    pipe.send({"kind": "collector-ready", "port": server.server_port, "pid": os.getpid()})
    try:
        while not stop.is_set():
            if pipe.poll():
                command = pipe.recv()
                if command == "valid-acks":
                    bad_ack = False
            server.handle_request()
    finally:
        server.server_close()
        connection.close()


def tables(path):
    with closing(sqlite3.connect(Path(path).as_uri() + "?mode=ro", uri=True)) as connection:
        schema = connection.execute(
            "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        ).fetchall()
        contents = {}
        for kind, name, _sql in schema:
            if kind == "table":
                if not re.fullmatch("[a-zA-Z0-9_]+", name):
                    raise ValueError("unexpected owned fixture table")
                rows = connection.execute('SELECT * FROM "' + name + '" ORDER BY rowid').fetchall()
                contents[name] = {
                    "rows": len(rows),
                    "sha256": hashlib.sha256(
                        json.dumps(rows, separators=(",", ":")).encode()
                    ).hexdigest(),
                }
        return {
            "schema_sha256": digest([list(row) for row in schema]),
            "tables": contents,
            "integrity": connection.execute("PRAGMA integrity_check").fetchone()[0],
        }


def run(cache, evidence):
    ctx = mp.get_context("spawn")
    processes = []
    stops = []
    pipes = []
    checks = []
    facts = {}

    def check(name, condition, **details):
        checks.append({"name": name, "passed": bool(condition), **details})
        if not condition:
            raise AssertionError(name)

    def spawn(target, *args):
        parent, child = ctx.Pipe()
        pipes.append(parent)
        # Child endpoints precede optional trailing options in small adapters.
        process = ctx.Process(target=target, args=(*args, child))
        process.start()
        processes.append(process)
        child.close()
        return process, parent

    def spawn_restore(target, checkpoint=None):
        parent, child = ctx.Pipe()
        pipes.append(parent)
        process = ctx.Process(
            target=restore_child, args=(backup, target, key, source_sha, child, checkpoint)
        )
        process.start()
        processes.append(process)
        child.close()
        return process, parent

    try:
        source_sha = digest(
            {
                name: hashlib.sha256(
                    (ROOT / "services/gateway/src" / name).read_bytes()
                ).hexdigest()
                for name in ["work_service.py", "operational_controls.py", "evaluation_controls.py"]
            }
        )
        admin = OperatorGate(cache / "operator", initialize=True, admin=True)
        runtime = OperatorGate(admin.root)
        store = Store(str(cache / "work.sqlite3"))
        work = WorkStore(store, initialize=True)
        work.configure(
            "demo",
            {
                "run": 1000,
                "company_day": 300,
                "company": 10000,
                "venture_day": 300,
                "venture": 10000,
            },
        )
        token = WorkService(work, enabled=True).issue_session(
            actor="human:fixture",
            venture="demo",
            role="owner",
            initiator={"kind": "person", "id": "synthetic-operations"},
            ttl=300,
        )
        service = WorkService(WorkStore(store), enabled=True, operator_gate=runtime)
        intake = {
            "request_id": str(uuid.uuid4()),
            "fixture": "invoice-good-v1",
            "goal": "Synthetic owned backup drill",
            "acceptance": "Fixed QA assertion receipt",
            "rights_ref": "owned:synthetic",
            "ai_use_approved": True,
            "destination": "local-review",
        }
        refused = False
        try:
            service.prepare(token, intake)
        except AuthorityError:
            refused = True
        check("new_profile_actually_refuses_work", refused)
        admin.pause(False, actor="human:fixture", decision_ref="a" * 64)
        task = service.prepare(token, intake)
        service.approve(token, task["id"], task["spec_digest"])
        result = service.execute(token, task["id"])
        check(
            "actual_namespace_qa_completed",
            result["status"] == "completed" and result["result"]["qa_passed"] is True,
        )
        facts["qa_verification"] = result["result"]["verification"]["counts"]
        files = {name: cache / name for name in ["config.json", "secrets.bin", "grants.json"]}
        files["config.json"].write_bytes(canonical({"synthetic": True, "outbound": False}))
        files["secrets.bin"].write_bytes(os.urandom(48))
        files["grants.json"].write_bytes(
            canonical(
                {
                    "synthetic": True,
                    "sqlite_host_profile": "private single-user files; NOT PostgreSQL GRANT restoration",
                    "runtime_ddl": False,
                }
            )
        )
        key = os.urandom(32)
        backup = cache / "backup.enc"
        before = tables(cache / "work.sqlite3")
        start = time.monotonic()
        facts["backup"] = backup_sqlite(
            cache / "work.sqlite3", files, backup, key, source_sha256=source_sha
        )
        facts["backup_microseconds"] = int((time.monotonic() - start) * 1_000_000)
        check(
            "backup_does_not_contain_secret_plaintext",
            files["secrets.bin"].read_bytes() not in backup.read_bytes(),
        )
        process, pipe = spawn_restore(cache / "isolated-restore")
        receipt = receive(pipe)
        process.join(5)
        check(
            "separate_process_restore_and_schema_data_readback",
            process.exitcode == 0
            and receipt["integrity_check"] == "ok"
            and tables(cache / "isolated-restore/database.sqlite3") == before,
        )
        check(
            "config_secrets_and_grant_bytes_read_back",
            all(
                (cache / "isolated-restore" / name).read_bytes() == path.read_bytes()
                for name, path in files.items()
            ),
        )
        facts["restore_readback"] = before
        restored = Store(str(cache / "isolated-restore/database.sqlite3"), initialize=False)
        paused = OperatorGate(cache / "restored-operator", initialize=True, admin=True)
        replay = WorkService(
            WorkStore(restored), enabled=True, operator_gate=OperatorGate(paused.root)
        ).execute(token, task["id"])
        check(
            "restored_same_id_replay_has_no_new_effect",
            replay["replayed"] is True
            and replay["attempted"] == 1
            and tables(cache / "isolated-restore/database.sqlite3") == before,
        )
        immutable = False
        try:
            restored._conn.execute("DELETE FROM work_v1_history")
        except sqlite3.DatabaseError:
            immutable = True
            restored._conn.rollback()
        check("restored_immutable_history_actually_rejects_delete", immutable)
        restored._conn.close()
        bad = False
        try:
            restore_backup(
                backup, cache / "wrong-key", os.urandom(32), expected_source_sha256=source_sha
            )
        except OpsError:
            bad = True
        check("wrong_recovery_key_no_target", bad and not (cache / "wrong-key").exists())
        for checkpoint in ["before", "after"]:
            target = cache / ("interrupted-" + checkpoint)
            process, pipe = spawn_restore(target, checkpoint)
            state = receive(pipe)
            process.kill()
            process.join(5)
            check(
                "actual_sigkill_restore_" + checkpoint,
                process.exitcode == -9
                and state["checkpoint"] == checkpoint
                and target.exists() == (checkpoint == "after"),
            )
            if checkpoint == "after":
                check(
                    "postcommit_crash_restored_data_still_valid",
                    tables(target / "database.sqlite3") == before,
                )
        process, pipe = spawn(slow_owned_child, admin.root)
        child = receive(pipe)["child_pid"]
        start = time.monotonic()
        admin.pause(True, actor="human:fixture", decision_ref="b" * 64)
        outcome = receive(pipe)
        process.join(5)
        gone = False
        try:
            os.kill(child, 0)
        except ProcessLookupError:
            gone = True
        check(
            "running_fixed_child_pause_reaped",
            process.exitcode == 0 and outcome["terminal"] == "cancelled" and gone,
            elapsed_microseconds=int((time.monotonic() - start) * 1_000_000),
            child_pid=child,
        )
        admin.pause(False, actor="human:fixture", decision_ref="c" * 64)
        # Actual independent producer/monitor/receiver processes, not alert log lines.
        producer_stop = ctx.Event()
        stops.append(producer_stop)
        pa, pc = ctx.Pipe()
        pipes.append(pa)
        prod = ctx.Process(target=producer, args=(admin.root, pc, producer_stop))
        prod.start()
        processes.append(prod)
        pc.close()
        receive(pa)
        import socket

        reserved = socket.socket()
        reserved.bind(("127.0.0.1", 0))
        closed_port = reserved.getsockname()[1]
        watch_stop = ctx.Event()
        stops.append(watch_stop)
        wa, wc = ctx.Pipe()
        pipes.append(wa)
        monitor = ctx.Process(
            target=watcher, args=(admin.root, cache / "outbox", wc, watch_stop, True, closed_port)
        )
        monitor.start()
        processes.append(monitor)
        wc.close()
        receive(wa, lambda m: m["kind"] == "watcher-ready")
        prod.kill()
        prod.join(5)
        lost = receive(wa, lambda m: m["kind"] == "state" and bool(m["pending_ids"]), timeout=8)
        check(
            "independent_watchdog_detected_actual_producer_death",
            prod.exitcode == -9 and monitor.is_alive() and len(lost["pending_ids"]) == 1,
        )
        check(
            "actual_refused_http_transport_retains_pending",
            lost["transport_attempts"] > 0 and bool(lost["pending_ids"]),
        )
        monitor.kill()
        monitor.join(5)
        reserved.close()
        collector_stop = ctx.Event()
        stops.append(collector_stop)
        ca, cc = ctx.Pipe()
        pipes.append(ca)
        receiver = ctx.Process(target=collector, args=(cache / "collector", cc, collector_stop))
        receiver.start()
        processes.append(receiver)
        cc.close()
        port = receive(ca)["port"]
        restarted_stop = ctx.Event()
        stops.append(restarted_stop)
        ra, rc = ctx.Pipe()
        pipes.append(ra)
        restarted = ctx.Process(
            target=watcher, args=(admin.root, cache / "outbox", rc, restarted_stop, False, port)
        )
        restarted.start()
        processes.append(restarted)
        rc.close()
        ready = receive(ra, lambda m: m["kind"] == "watcher-ready")
        check(
            "sigkilled_watchdog_restart_preserves_exact_outbox_id",
            monitor.exitcode == -9 and ready["pending_ids"] == lost["pending_ids"],
        )
        wrong = receive(ca, lambda m: m["kind"] == "http" and not m["correct_ack"])
        ra.send("snapshot")
        pending = receive(ra, lambda m: m["kind"] == "snapshot")
        check("real_http_wrong_ack_not_delivery", wrong["id"] in pending["pending_ids"])
        ca.send("valid-acks")
        valid = receive(ca, lambda m: m["kind"] == "http" and m["correct_ack"])
        empty = receive(ra, lambda m: m["kind"] == "state" and not m["pending_ids"])
        check(
            "real_collector_durable_ack_clears_outbox",
            valid["id"] == lost["pending_ids"][0] and empty["delivered_this_cycle"] == 1,
        )
        facts["http_ack"] = valid
        facts["restore_receipt"] = receipt
        facts["private_orphan_stages_retained_for_inspection"] = len(list(cache.glob(".restore-*")))
        store._conn.close()
    finally:
        # A SIGKILL may poison multiprocessing.Event locks. Never acquire an
        # Event shared with a killed fixture while cleaning up. Signal only the
        # explicitly tracked new children, then reap with bounded OS joins.
        for process in processes:
            if process.is_alive():
                process.terminate()
        for process in processes:
            process.join(2)
            if process.is_alive():
                process.kill()
                process.join(2)
        for pipe in pipes:
            with suppress(OSError):
                pipe.close()
        check(
            "all_new_fixture_processes_stopped",
            all(not p.is_alive() for p in processes),
            pids=[p.pid for p in processes],
            exitcodes=[p.exitcode for p in processes],
        )
        (evidence / "operations-drill.json").write_bytes(
            canonical(
                {
                    "schema": "openbot.local-operations-drill/1",
                    "synthetic": True,
                    "checks": checks,
                    "facts": facts,
                    "key_distributed": False,
                    "production_rollout_performed": False,
                    "owner_key_recovery_accepted": False,
                    "witnessed_operations_accepted": False,
                    "real_oncall_accepted": False,
                    "real_pilot_started": False,
                    "release_authorized": False,
                }
            )
            + b"\n"
        )
    print(
        json.dumps(
            {
                "passed": sum(c["passed"] for c in checks),
                "total": len(checks),
                "production_gate_accepted": False,
                "evidence": str(evidence / "operations-drill.json"),
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    for path in [args.cache, args.evidence]:
        if (
            path.exists()
            or any(p.is_symlink() for p in (path, *path.parents))
            or ".cache" not in path.absolute().parts
        ):
            raise ValueError("NEW non-symlinked excluded-cache targets required")
    if (
        args.cache.absolute() == args.evidence.absolute()
        or args.cache.absolute() in args.evidence.absolute().parents
        or args.evidence.absolute() in args.cache.absolute().parents
    ):
        raise ValueError("distinct non-nested fixture and evidence roots required")
    for path in [args.cache, args.evidence]:
        path.mkdir(mode=0o700, parents=True)
    run(args.cache.absolute(), args.evidence.absolute())


if __name__ == "__main__":
    main()
