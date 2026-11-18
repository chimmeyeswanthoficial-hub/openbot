"""S02 real two-backend identity, liability, process-race and crash evidence."""

from __future__ import annotations

import multiprocessing
import os
from datetime import UTC, datetime, timedelta

import pytest
from dispatch_agui import AGUIDispatcher
from repository import Store
from work_store import WorkError, WorkStore, WorkUnavailable, digest, minor, utc

WHEN = datetime(2026, 11, 10, 6, tzinfo=UTC)


def register(work, key="one", upper=100, venture="demo", origin="manual", when=WHEN, plan=None):
    return work.register(
        venture=venture,
        routine="sample",
        origin=origin,
        key=key,
        when=when,
        initiator={"kind": "routine", "id": "original-clock", "actor": "agent:qa"},
        plan=plan or {"tool": "fixed-fixture"},
        upper_minor=upper,
    )


def queued(backend, **kwargs):
    row, created = register(backend.work, **kwargs)
    assert created and backend.work.reserve(row["id"])
    return row


def test_identity_replay_and_changed_plan_never_replace_original(durable_backend):
    w = durable_backend.work
    row, created = register(w)
    same, again = register(w)
    assert created and not again and same["id"] == row["id"]
    with pytest.raises(WorkError, match="identity_conflict"):
        register(w, plan={"tool": "changed"})
    assert w.get(row["id"])["initiator"]["id"] == "original-clock"
    assert len(w.history(row["id"])) == 1


def test_utc_occurrence_identity_uses_the_same_instant(durable_backend):
    w = durable_backend.work
    key = WHEN.isoformat()
    row, _ = register(w, key=key, origin="timer")
    same, created = register(
        w,
        key=key,
        origin="timer",
        when=WHEN.astimezone(__import__("datetime").timezone(timedelta(hours=5, minutes=30))),
    )
    assert not created and same["id"] == row["id"] and same["scheduled_utc"] == key


def test_manual_event_and_timer_do_not_coalesce(durable_backend):
    w = durable_backend.work
    rows = [
        register(w, key=WHEN.isoformat(), origin=origin)[0]
        for origin in ["manual", "event", "timer"]
    ]
    assert len({r["id"] for r in rows}) == 3
    with pytest.raises(WorkError):
        register(w, origin="retry")


def test_atomic_whole_liability_at_all_caps(durable_backend):
    b = durable_backend
    a = queued(b, key="a", upper=200)
    c, _ = register(b.work, key="b", upper=101)
    assert not b.work.reserve(c["id"])
    assert b.work.get(c["id"])["status"] == "blocked"
    assert b.work.totals("demo", "2026-11-10")["company_day"] == 200
    other, _ = register(b.work, key="other", upper=101, venture="other")
    assert not b.work.reserve(other["id"])  # company-wide, not merely a venture counter
    assert b.work.get(a["id"])["held_minor"] == 200


def test_run_bound_and_missing_scope_fail_closed(durable_backend):
    b = durable_backend
    row, _ = register(b.work, upper=1001)
    assert not b.work.reserve(row["id"])
    unknown, _ = register(b.work, key="unprovisioned", venture="not-provisioned")
    assert not b.work.reserve(unknown["id"])
    with pytest.raises(WorkError, match="trusted_setup"):
        b.work.configure("demo", {"run": 999})


def test_fencing_reclaims_only_before_any_possible_effect(durable_backend):
    b = durable_backend
    row = queued(b)
    first = b.work.claim(row["id"], "worker-one", lease=1)
    b.clock[0] += 2
    second = b.work.claim(row["id"], "worker-two", lease=1)
    assert second == first + 1
    assert not b.work.before_effect(row["id"], first, row["spec_digest"])
    assert b.work.before_effect(row["id"], second, row["spec_digest"])
    b.clock[0] += 2
    assert b.work.claim(row["id"], "worker-three") is None
    current = b.work.get(row["id"])
    assert current["status"] == "uncertain" and current["held_minor"] == 100
    assert not b.work.finish(row["id"], first, "completed", {})


def test_uncertain_liability_crosses_midnight_and_month_boundaries(durable_backend):
    b = durable_backend
    b.clock[0] = WHEN.timestamp()
    row = queued(b, upper=200)
    assert b.work.totals("demo", "2026-12-01")["company_day"] == 200
    f = b.work.claim(row["id"], "worker")
    assert b.work.before_effect(row["id"], f, row["spec_digest"])
    assert b.work.finish(row["id"], f, "completed", {"local": "observed"})
    assert b.work.get(row["id"])["held_minor"] == 200  # report is not independent usage
    assert b.work.reconcile(row["id"], "receipt-one", 120, digest({"usage": "independent-fixture"}))
    assert b.work.totals("demo", "2026-11-10")["company_day"] == 120
    assert b.work.totals("demo", "2026-11-11")["company_day"] == 0
    assert b.work.totals("demo", "2026-11-11")["company"] == 120
    assert b.work.totals("demo", "2026-12-01")["company"] == 0
    assert not b.work.reconcile(
        row["id"], "receipt-one", 120, digest({"usage": "independent-fixture"})
    )
    with pytest.raises(WorkError, match="conflict"):
        b.work.reconcile(row["id"], "receipt-two", 0, digest({"usage": "forged-release"}))


def test_actual_over_bound_usage_is_retained_not_hidden(durable_backend):
    b = durable_backend
    b.clock[0] = WHEN.timestamp()
    row = queued(b, upper=100)
    f = b.work.claim(row["id"], "worker")
    assert b.work.before_effect(row["id"], f, row["spec_digest"])
    b.work.finish(row["id"], f, "completed", {})
    b.work.reconcile(row["id"], "observed-overrun", 150, digest({"usage": 150}))
    assert b.work.get(row["id"])["status"] == "uncertain"
    assert b.work.totals("demo", "2026-11-10")["company_day"] == 150


def test_cancel_before_attempt_releases_only_proven_unattempted_work(durable_backend):
    b = durable_backend
    row = queued(b)
    f = b.work.claim(row["id"], "worker")
    assert b.work.cancel(row["id"], "human:owner")
    assert not b.work.before_effect(row["id"], f, row["spec_digest"])
    assert b.work.get(row["id"])["held_minor"] == 0
    active = queued(b, key="active")
    f = b.work.claim(active["id"], "worker")
    assert b.work.before_effect(active["id"], f, active["spec_digest"])
    assert b.work.cancel(active["id"], "human:owner")
    assert b.work.get(active["id"])["held_minor"] == 100
    assert b.work.get(active["id"])["status"] == "running"


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE work_v1_history SET kind='forged'",
        "DELETE FROM work_v1_history",
        "UPDATE work_v1_tasks SET venture='other'",
        "DELETE FROM work_v1_tasks",
        "UPDATE work_v1_limits SET cap_minor=999999",
    ],
)
def test_evidence_identity_and_caps_are_not_rewritten(durable_backend, sql):
    register(durable_backend.work)
    with pytest.raises(WorkUnavailable), durable_backend.work.tx() as cur:
        durable_backend.work.q(cur, sql)
    assert durable_backend.work.find("demo", "sample", "manual", "one") is not None


def test_missing_audit_permission_rolls_back_pre_effect_marker(durable_backend):
    b = durable_backend
    row = queued(b)
    f = b.work.claim(row["id"], "worker")
    if b.kind == "pg":
        from psycopg2 import sql

        with b.admin.cursor() as cur:
            cur.execute(
                sql.SQL("REVOKE INSERT ON {}.audit FROM {}").format(
                    sql.Identifier(b.schema), sql.Identifier(b.role)
                )
            )
    else:
        b.owner._conn.execute(
            "CREATE TRIGGER audit_fail BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT,'synthetic audit failure'); END"
        )
        b.owner._conn.commit()
    with pytest.raises(WorkUnavailable):
        b.work.before_effect(row["id"], f, row["spec_digest"])
    assert b.work.get(row["id"])["attempted"] == 0
    assert not any(r["kind"] == "effect_authorized" for r in b.work.history(row["id"]))


def test_legacy_transport_cannot_bypass_governed_claim(durable_backend):
    b = durable_backend
    row = queued(b)
    calls = []
    from types import SimpleNamespace

    spec = SimpleNamespace(
        id="sample",
        venture="demo",
        bot="ceo",
        budget_usd=1,
        max_runtime_min=1,
        body="owned fixture",
        outputs=[],
    )
    response = AGUIDispatcher(
        store=b.store, transport=lambda *_: calls.append("effect")
    ).execute_turn(spec, row["id"])
    assert not response["ok"] and not calls
    assert b.work.get(row["id"])["attempted"] == 0


def _reserve_process(dsn, key, queue, barrier):
    s = Store(dsn, initialize=False)
    w = WorkStore(s)
    try:
        row, _ = register(w, key=key, upper=200)
        barrier.wait(timeout=15)
        queue.put(w.reserve(row["id"]))
    finally:
        s._conn.close()


def test_two_processes_cannot_spend_past_the_same_cap(durable_backend):
    b = durable_backend
    ctx = multiprocessing.get_context("spawn")
    queue, barrier = ctx.Queue(), ctx.Barrier(2)
    processes = [
        ctx.Process(target=_reserve_process, args=(b.dsn, str(i), queue, barrier)) for i in range(2)
    ]
    try:
        for child in processes:
            child.start()
        for child in processes:
            child.join(timeout=20)
            assert not child.is_alive() and child.exitcode == 0
        assert sorted(queue.get(timeout=3) for _ in processes) == [False, True]
        assert b.work.totals("demo", "2026-11-10")["company_day"] == 200
    finally:
        for child in processes:
            if child.is_alive():
                child.terminate()
                child.join(timeout=3)
        queue.close()
        queue.join_thread()


def _death_process(dsn, stage, marker):
    s = Store(dsn, initialize=False)
    w = WorkStore(s)
    if stage == "before_register_commit":
        w.fault_hook = lambda at: os._exit(81) if at == "before_commit" else None
    row, _ = register(w, key="death")
    if stage == "after_register":
        os._exit(81)
    assert w.reserve(row["id"])
    f = w.claim(row["id"], "doomed", lease=1)
    if stage == "after_claim":
        os._exit(81)
    assert w.before_effect(row["id"], f, row["spec_digest"])
    if stage == "after_attempt_marker":
        os._exit(81)
    with open(marker, "a") as stream:
        stream.write("one actual fixed test effect\n")
    w.finish(row["id"], f, "completed", {"fixed_effect_observed": True})
    os._exit(81)


@pytest.mark.parametrize(
    "stage",
    [
        "before_register_commit",
        "after_register",
        "after_claim",
        "after_attempt_marker",
        "after_result",
    ],
)
def test_real_process_death_has_explainable_state_without_new_attempt(durable_backend, stage):
    b = durable_backend
    marker = b.path / "synthetic-effect.txt"
    child = multiprocessing.get_context("spawn").Process(
        target=_death_process, args=(b.dsn, stage, str(marker))
    )
    child.start()
    try:
        child.join(timeout=20)
        assert child.exitcode == 81 and not child.is_alive()
        row = b.work.find("demo", "sample", "manual", "death")
        if stage == "before_register_commit":
            assert row is None
        elif stage == "after_register":
            assert row["status"] == "preparing" and not row["attempted"]
        elif stage == "after_claim":
            b.clock[0] += 3
            assert b.work.claim(row["id"], "recovery") == 2
        elif stage == "after_attempt_marker":
            b.clock[0] += 3
            assert b.work.claim(row["id"], "recovery") is None
            assert b.work.get(row["id"])["status"] == "uncertain"
        else:
            assert row["status"] == "completed" and marker.read_text().count("effect") == 1
            assert b.work.claim(row["id"], "recovery") is None
    finally:
        if child.is_alive():
            child.terminate()
            child.join(timeout=3)


@pytest.mark.parametrize("value", ["NaN", "Infinity", -1, True, {}, 10**100])
def test_invalid_budget_cannot_enter_an_integer_reservation(value):
    with pytest.raises(WorkError):
        minor(value)


def test_fractional_cent_upper_bound_rounds_up():
    assert minor("0.001") == 1 and minor("0.10") + minor("0.20") == 30
    assert utc(WHEN) == WHEN


def _timer_worker(dsn, state, body, queue, barrier):
    from runner import Worker
    from spec import parse

    s = Store(dsn, initialize=False)
    try:
        worker = Worker(store=s, state_dir=state)
        worker.specs = [parse(body)]
        barrier.wait(timeout=15)
        queue.put(worker.tick(when=WHEN.replace(tzinfo=None)))
    finally:
        s._conn.close()


def test_two_actual_workers_and_restart_share_one_timer_occurrence(durable_backend):
    from pathlib import Path

    from runner import Worker
    from spec import parse

    b = durable_backend
    state = b.path / "state"
    state.mkdir()
    (state / "active_ventures.yaml").write_text("ventures: []\n")
    (state / "budget.json").write_text('{"company_day_cap_usd":3}')
    body = (Path(__file__).parents[3] / ".openbot/routines/scout-daily.md").read_text()
    ctx = multiprocessing.get_context("spawn")
    q = ctx.Queue()
    barrier = ctx.Barrier(2)
    children = [
        ctx.Process(target=_timer_worker, args=(b.dsn, str(state), body, q, barrier))
        for _ in range(2)
    ]
    try:
        for child in children:
            child.start()
        for child in children:
            child.join(timeout=20)
            assert not child.is_alive() and child.exitcode == 0
        outputs = [q.get(timeout=3) for _ in children]
        assert sum(result.get("ok", False) for group in outputs for result in group) == 1
        worker = Worker(store=b.store, state_dir=str(state))
        worker.specs = [parse(body)]
        assert worker.tick(when=WHEN.replace(tzinfo=None)) == []
        occurrence = b.work.find("platform", "scout-daily", "timer", WHEN.isoformat())
        assert occurrence["initiator"]["kind"] == "routine" and occurrence["upper_minor"] == 200
    finally:
        for child in children:
            if child.is_alive():
                child.terminate()
                child.join(timeout=3)
        q.close()
        q.join_thread()


@pytest.mark.parametrize("at", ["before_commit", "after_commit"])
def test_actual_connection_loss_and_same_identity_readback(durable_backend, at):
    b = durable_backend

    def disconnect(stage):
        if stage != at:
            return
        if b.kind == "pg":
            pid = b.store._conn.get_backend_pid()
            with b.admin.cursor() as cur:
                cur.execute("SELECT pg_terminate_backend(%s,1000)", (pid,))
                assert cur.fetchone()[0]
            if at == "after_commit":
                b.store._conn.cursor().execute("SELECT 1")
        else:
            b.store._conn.close()
            if at == "after_commit":
                b.store._conn.execute("SELECT 1")

    b.work.fault_hook = disconnect
    with pytest.raises(WorkUnavailable) as error:
        register(b.work, key="connection-loss")
    assert error.value.uncertain
    recovered = Store(b.dsn, initialize=False)
    try:
        work = WorkStore(recovered)
        prior = work.find("demo", "sample", "manual", "connection-loss")
        assert bool(prior) == (at == "after_commit")
        row, created = register(work, key="connection-loss")
        assert created == (at == "before_commit")
        assert row["attempted"] == 0
    finally:
        recovered._conn.close()


def test_over_500_legacy_rows_need_attested_bounds_and_are_all_counted(durable_backend):
    b = durable_backend
    for _ in range(501):
        run = b.owner.start_run("owned-one-cent-history", "demo")
        b.owner.end_run(run, "queued", 0, "synthetic fixture original upper bound was one cent")
    with pytest.raises(WorkError, match="legacy_liability_requires_review"):
        b.work.totals("demo", "2026-11-10")
    with pytest.raises(WorkError, match="trusted_legacy_import"):
        b.work.import_legacy(
            {"owned-one-cent-history": 1},
            evidence_digest=digest({"seed": "501 known one-cent bounds"}),
        )
    assert (
        b.provision.import_legacy(
            {"owned-one-cent-history": 1},
            evidence_digest=digest({"seed": "501 known one-cent bounds"}),
        )
        == 501
    )
    assert b.work.totals("demo", "2026-11-10")["company_day"] == 501
    row, _ = register(b.work, key="after-501", upper=1)
    assert not b.work.reserve(row["id"])


@pytest.mark.parametrize("old_status", ["failed", "cancelled", "unknown-old-outcome"])
def test_terminal_label_without_final_usage_never_erases_legacy_liability(
    durable_backend, old_status
):
    b = durable_backend
    run = b.owner.start_run("old-ambiguous", "demo")
    b.owner.end_run(run, old_status, 0, "no authoritative original bound or final usage")
    with pytest.raises(WorkError, match="legacy_liability_requires_review"):
        b.work.totals("demo", "2026-11-10")


def test_new_work_schema_does_not_silently_accept_an_old_incomplete_shape(durable_backend):
    b = durable_backend
    with b.provision.tx() as cur:
        b.provision.q(
            cur, "ALTER TABLE work_v1_legacy RENAME COLUMN evidence_digest TO obsolete_evidence"
        )
    with pytest.raises((WorkError, WorkUnavailable)):
        WorkStore(b.store)


def test_late_usage_recognition_and_backdated_occurrences_cannot_erase_today_spend(durable_backend):
    b = durable_backend
    b.clock[0] = WHEN.timestamp() + 86400
    row = queued(b, upper=200)
    fence = b.work.claim(row["id"], "late-worker")
    assert b.work.before_effect(row["id"], fence, row["spec_digest"])
    assert b.work.finish(row["id"], fence, "completed", {})
    assert b.work.reconcile(row["id"], "independent-late-receipt", 200, digest({"usage": 200}))
    assert b.work.totals("demo", "2026-11-11")["company_day"] == 200
    second, _ = register(b.work, key="backdated-after-late-spend", upper=101)
    assert not b.work.reserve(second["id"])
