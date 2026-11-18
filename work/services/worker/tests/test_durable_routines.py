"""Actual repeated-routine/history/restart regressions against the scheduler."""

from datetime import datetime
from pathlib import Path

from repository import Store
from runner import Worker
from spec import parse

SCOUT = (Path(__file__).parents[3] / ".openbot/routines/scout-daily.md").read_text()
WHEN = datetime(2026, 11, 10, 6)


def configured(tmp_path, store, cap=3):
    state = tmp_path / "state"
    state.mkdir(exist_ok=True)
    (state / "active_ventures.yaml").write_text("ventures: []\n")
    (state / "budget.json").write_text('{"company_day_cap_usd": ' + str(cap) + "}")
    worker = Worker(store=store, state_dir=str(state))
    worker.specs = [parse(SCOUT)]
    return worker


def test_repeating_same_routine_counts_full_prior_liability(tmp_path):
    store = Store()
    worker = configured(tmp_path, store)
    assert worker.dispatch("scout-daily", when=WHEN)["ok"]
    assert not worker.dispatch("scout-daily", when=WHEN)["ok"]


def test_history_beyond_500_rows_is_not_a_budget_window(tmp_path):
    store = Store()
    for _index in range(501):
        rid = store.start_run("scout-daily", "platform")
        store.end_run(rid, "queued", 0, "legacy unknown liability")
    worker = configured(tmp_path, store, cap=1001)
    assert not worker.dispatch("scout-daily", when=WHEN)["ok"]


def test_worker_restart_does_not_create_another_timer_occurrence(tmp_path):
    store = Store(str(tmp_path / "test.db"))
    assert configured(tmp_path, store, 20).tick(when=WHEN)[0]["ok"]
    restarted = Store(str(tmp_path / "test.db"))
    assert not any(
        result.get("ok") for result in configured(tmp_path, restarted, 20).tick(when=WHEN)
    )


def test_real_aware_clock_honors_timezone_but_identity_is_utc(tmp_path):
    from datetime import UTC

    w = configured(tmp_path, Store(), 20)
    due = w.due(datetime(2026, 11, 10, 0, 30, tzinfo=UTC))  # 06:00 Asia/Kolkata
    assert [s.id for s in due] == ["scout-daily"]
    out = w.tick(when=datetime(2026, 11, 10, 0, 30, tzinfo=UTC))[0]
    assert w.work.get(out["run_id"])["scheduled_utc"] == "2026-11-10T00:30:00+00:00"


def test_exact_cent_boundary_does_not_use_binary_float_addition(tmp_path):
    from dataclasses import replace

    w = configured(tmp_path, Store(), 0.30)
    w.specs = [replace(parse(SCOUT), budget_usd=0.1)]
    assert all(w.dispatch("scout-daily", when=WHEN)["ok"] for _ in range(3))
    assert not w.dispatch("scout-daily", when=WHEN)["ok"]


def test_restart_can_resume_a_durable_but_unreserved_timer_without_a_new_id(tmp_path, monkeypatch):
    from work_store import WorkUnavailable

    store = Store(str(tmp_path / "unreserved.sqlite3"))
    w = configured(tmp_path, store)
    actual = w.work.reserve

    def fail(*args, **kwargs):
        raise WorkUnavailable()

    monkeypatch.setattr(w.work, "reserve", fail)
    assert not w.tick(when=WHEN)[0]["ok"]
    old = w.work.find("platform", "scout-daily", "timer", WHEN.isoformat() + "+00:00")
    assert old["status"] == "preparing" and not old["attempted"]
    monkeypatch.setattr(w.work, "reserve", actual)
    restarted = configured(tmp_path, Store(store.path))
    resumed = restarted.tick(when=WHEN)
    assert len(resumed) == 1 and resumed[0]["ok"] and resumed[0]["run_id"] == old["id"]
