"""Actual synthetic SQLite backup / PG dump+restore of the new complete work state."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
from repository import Store
from work_service import WorkService
from work_store import WorkStore, WorkUnavailable, canonical

REAL = pytest.mark.skipif(
    os.environ.get("OPENBOT_TEST_NAMESPACE") != "1",
    reason="explicit fixed namespace profile required",
)


TABLES = (
    "audit",
    "approvals",
    "ledger",
    "runs",
    "work_v1_schema",
    "work_v1_limits",
    "work_v1_tasks",
    "work_v1_history",
    "work_v1_legacy",
    "work_v1_usage",
    "work_v1_events",
    "work_v1_outbox",
    "work_v1_sessions",
)


def state(work):
    data = {}
    with work.tx() as cur:
        for table in TABLES:
            work.q(cur, "SELECT * FROM " + table)
            data[table] = sorted(work.rows(cur), key=canonical)
    return {
        "rows_sha256": hashlib.sha256(canonical(data).encode()).hexdigest(),
        "table_counts": {table: len(rows) for table, rows in data.items()},
    }


@REAL
def test_actual_workflow_backup_restores_authority_history_events_and_artifact(durable_backend):
    b = durable_backend
    issuer = WorkService(b.provision, enabled=True)
    agent = issuer.issue_session(
        actor="agent:qa",
        venture="demo",
        role="agent",
        initiator={"kind": "handoff", "id": "owned-recovery-sample"},
    )
    owner = issuer.issue_session(
        actor="human:fixture_reviewer",
        venture="demo",
        role="owner",
        initiator={"kind": "person", "id": "fixture-review"},
    )
    service = WorkService(b.work, enabled=True)
    body = {
        "request_id": str(uuid.uuid4()),
        "fixture": "invoice-good-v1",
        "goal": "Validate restore/replay",
        "acceptance": "All fixed assertions and documentation examples pass",
        "rights_ref": "owned:seed",
        "ai_use_approved": True,
        "destination": "local-review",
    }
    task = service.prepare(agent, body)
    assert service.approve(owner, task["id"], task["spec_digest"])
    assert service.execute(agent, task["id"])["status"] == "completed"
    artifact = service.outbox(agent, task["id"])
    expected = state(b.work)
    if b.kind == "sqlite":
        destination = b.path / "actual-restored.sqlite3"
        with sqlite3.connect(destination) as target:
            b.store._conn.backup(target)
        restored_dsn = str(destination)
        dump = destination
        restored_db = None
    else:
        from psycopg2 import sql

        tools = Path(os.environ["OPENBOT_PG_TEST_BIN"])
        dump = b.path / "work-profile.dump"
        subprocess.run(
            [
                str(tools / "pg_dump"),
                "-Fc",
                "--no-owner",
                "--schema=" + b.schema,
                "--file=" + str(dump),
                "--dbname=" + b.owner.path,
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        restored_db = "openbot_fixture_work_restore_" + uuid.uuid4().hex[:12]
        with b.admin.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(restored_db)))
            cur.execute(
                sql.SQL("REVOKE CREATE,TEMPORARY ON DATABASE {} FROM PUBLIC").format(
                    sql.Identifier(restored_db)
                )
            )
        url = urlsplit(b.owner.path)
        target = urlunsplit((url.scheme, url.netloc, "/" + restored_db, url.query, ""))
        subprocess.run(
            [
                str(tools / "pg_restore"),
                "--exit-on-error",
                "--no-owner",
                "--dbname=" + target,
                str(dump),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        url = urlsplit(b.dsn)
        restored_dsn = urlunsplit((url.scheme, url.netloc, "/" + restored_db, url.query, ""))
    restored = Store(restored_dsn, initialize=False)
    try:
        readback = WorkStore(restored)
        actual = state(readback)
        assert actual == expected
        reopened = WorkService(readback, enabled=True)
        replay = reopened.execute(agent, task["id"])
        assert replay["replayed"] and replay["status"] == "completed"
        assert reopened.outbox(agent, task["id"])["sha256"] == artifact["sha256"]
        assert state(readback) == expected
        with pytest.raises(WorkUnavailable), readback.tx() as cur:
            readback.q(cur, "UPDATE work_v1_history SET kind='forged-restored-history'")
        assert state(readback) == expected
        assert readback.claim(task["id"], "must-not-run") is None
        role_flags = None
        if b.kind == "pg":
            with readback.tx() as cur:
                readback.q(
                    cur,
                    "SELECT current_user,rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user",
                )
                role_flags = list(cur.fetchone())
                assert role_flags == [b.role, False, False, False]
        output = os.environ.get("OPENBOT_STAGES_EVIDENCE")
        if output:
            directory = Path(output) / ("work-restore-" + b.kind)
            directory.mkdir(parents=True, exist_ok=False)
            (directory / dump.name).write_bytes(dump.read_bytes())
            (directory / "restore-readback.json").write_text(
                json.dumps(
                    {
                        "mode": "synthetic_owned_fixture",
                        "backend": b.kind,
                        "actual_restore_executed": True,
                        "expected": expected,
                        "actual": actual,
                        "restored_database": restored_db,
                        "schema": b.schema,
                        "role": b.role,
                        "app_role_flags": role_flags,
                        "task_id": task["id"],
                        "artifact_sha256": artifact["sha256"],
                        "same_task_replay_without_effect": True,
                        "all_rows_after_replay_unchanged": True,
                        "limits": "same-host fixture, not encrypted production backup/HA",
                    },
                    indent=2,
                )
                + "\n"
            )
    finally:
        restored._conn.close()
