"""New workflow supervisor death, original-ID recovery and no repeated real QA.

Only bundled first-party code and disposable fixture DBs. Owner-role sessions
are synthetic test grants, NOT qualified human acceptance or client pairing.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import uuid
from pathlib import Path

import pytest
from repository import Store
from work_service import WorkService
from work_store import WorkStore, canonical

REAL = pytest.mark.skipif(
    os.environ.get("OPENBOT_TEST_NAMESPACE") != "1",
    reason="explicit fixed namespace profile required",
)


def credentials_and_body(b):
    issuer = WorkService(b.provision, enabled=True)
    agent = issuer.issue_session(
        actor="agent:qa",
        venture="demo",
        role="agent",
        initiator={"kind": "handoff", "id": "owned-crash-sample"},
        ttl=3600,
    )
    owner = issuer.issue_session(
        actor="human:fixture_reviewer",
        venture="demo",
        role="owner",
        initiator={"kind": "person", "id": "fixture-review"},
        ttl=3600,
    )
    body = {
        "request_id": str(uuid.uuid4()),
        "fixture": "invoice-good-v1",
        "goal": "Reproduce supervisor failure safely",
        "acceptance": "Keep original identity and never repeat an attempted tool",
        "rights_ref": "owned:seed",
        "ai_use_approved": True,
        "destination": "local-review",
    }
    return agent, owner, body


def _prepare_then_die(dsn, token, body):
    store = Store(dsn, initialize=False)
    work = WorkStore(store)
    armed = [False]

    def die(stage):
        if stage == "before_commit":
            cur = store._conn.cursor()
            try:
                work.q(
                    cur,
                    "SELECT count(*) FROM work_v1_tasks WHERE occurrence_key=? AND status='preparing'",
                    (body["request_id"],),
                )
                armed[0] = cur.fetchone()[0] == 1
            finally:
                cur.close()
        if stage == "after_commit" and armed[0]:
            os._exit(83)

    work.fault_hook = die
    WorkService(work, enabled=True).prepare(token, body)
    raise AssertionError("crash injection did not run")


def _real_qa_then_die(dsn, token, task_id, marker):
    import qa_workflow

    actual = qa_workflow.run_owned_qa

    def run(*args, **kwargs):
        result = actual(*args, **kwargs)
        Path(marker).write_text(canonical(result))
        # The owned child really finished/reaped, but the supervising API dies
        # before it can atomically store the result, terminal events or outbox.
        os._exit(84)

    qa_workflow.run_owned_qa = run
    store = Store(dsn, initialize=False)
    WorkService(WorkStore(store), enabled=True).execute(token, task_id)
    raise AssertionError("actual QA/death injection did not run")


def wait_for_crash(target, args, code):
    child = multiprocessing.get_context("spawn").Process(target=target, args=args)
    child.start()
    try:
        child.join(timeout=15)
        assert not child.is_alive() and child.exitcode == code
    finally:
        if child.is_alive():
            child.terminate()
            child.join(timeout=3)


@REAL
def test_actual_death_after_registration_can_resume_same_unattempted_intake(durable_backend):
    b = durable_backend
    agent, owner, body = credentials_and_body(b)
    wait_for_crash(_prepare_then_die, (b.dsn, agent, body), 83)
    existing = b.work.find("demo", "owned-qa", "manual", body["request_id"])
    assert existing["status"] == "preparing" and existing["attempted"] == 0
    reopened = WorkService(b.work, enabled=True)
    resumed = reopened.prepare(agent, body)
    assert resumed["id"] == existing["id"] and resumed["status"] == "review"
    assert reopened.approve(owner, resumed["id"], resumed["spec_digest"])
    assert reopened.execute(agent, resumed["id"])["result"]["qa_passed"]
    assert sum(r["kind"] == "effect_authorized" for r in b.work.history(resumed["id"])) == 1


@REAL
def test_actual_death_after_real_qa_never_turns_a_lost_report_into_a_new_attempt(
    durable_backend, monkeypatch
):
    import isolation

    b = durable_backend
    agent, owner, body = credentials_and_body(b)
    service = WorkService(b.work, enabled=True)
    row = service.prepare(agent, body)
    assert service.approve(owner, row["id"], row["spec_digest"])
    marker = b.path / "actual-lost-owned-report.json"
    wait_for_crash(_real_qa_then_die, (b.dsn, agent, row["id"], str(marker)), 84)
    observed = json.loads(marker.read_text())
    assert observed["verification"]["counts"] == {
        "passed": 7,
        "failed": 0,
        "skipped": 0,
        "collected": 7,
    }
    assert observed["process"]["exit_confirmed"]
    assert not Path("/proc", str(observed["process"]["pid"])).exists()
    assert b.work.get(row["id"])["attempted"] == 1
    assert len(b.work.events(row["id"])) == 2
    assert service.outbox(agent, row["id"]) is None
    b.clock[0] += 40

    def forbidden(*_args, **_kwargs):
        pytest.fail("lost report must not launch another owned worker")

    monkeypatch.setattr(isolation, "run_fixed", forbidden)
    result = WorkService(b.work, enabled=True).execute(agent, row["id"])
    assert result["status"] == "uncertain"
    assert sum(r["kind"] == "effect_authorized" for r in b.work.history(row["id"])) == 1
    assert service.outbox(agent, row["id"]) is None
