"""The scheduler's job is to say no for the right reasons, and to fire once."""

from __future__ import annotations

import pathlib
import sys
from datetime import datetime

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "sentinel"))

from repository import Store  # noqa: E402
from runner import Worker, cron_matches, next_fire, preflight  # noqa: E402
from spec import parse  # noqa: E402

ROOT = pathlib.Path(__file__).parents[3]
ROUTINES = ROOT / ".openbot" / "routines"
SCOUT = (ROUTINES / "scout-daily.md").read_text()
SPEC = parse(SCOUT)
VENTURE = {"media-api": {"slug": "media-api", "paused": False}}
BUDGET = {"company_day_cap_usd": 20.0, "spent_today_usd": 0.0}
VENTURED = parse(SCOUT.replace("tags: [scout, market, daily]", "tags: [scout]\nventure: media-api"))


# ---------------------------------------------------------------- cron
@pytest.mark.parametrize("expr,when,expected", [
    ("0 6 * * *", datetime(2026, 11, 10, 6, 0), True),
    ("0 6 * * *", datetime(2026, 11, 10, 6, 1), False),
    ("*/15 * * * *", datetime(2026, 11, 10, 6, 45), True),
    ("*/15 * * * *", datetime(2026, 11, 10, 6, 46), False),
    ("30 9 * * 1-5", datetime(2026, 11, 10, 9, 30), True),    # 2026-11-10 is a Tuesday
    ("30 9 * * 1-5", datetime(2026, 11, 15, 9, 30), False),   # Sunday
    ("0 8 * * 1", datetime(2026, 11, 9, 8, 0), True),         # Monday
])
def test_cron_matching(expr, when, expected):
    assert cron_matches(expr, when) is expected


def test_next_fire_is_in_the_future_and_matches():
    after = datetime(2026, 11, 10, 6, 1)
    nxt = next_fire("0 6 * * *", after)
    assert nxt == datetime(2026, 11, 11, 6, 0)


# ---------------------------------------------------------------- preflight
def test_preflight_allows_a_clean_run():
    assert preflight(SPEC, ventures=VENTURE, budget=BUDGET,
                     spent_today_usd=0.0, dispatched_today_usd=0.0) is None


def test_preflight_refuses_a_paused_venture():
    paused = {"media-api": {"slug": "media-api", "paused": True}}
    r = preflight(VENTURED, ventures=paused, budget=BUDGET,
                  spent_today_usd=0.0, dispatched_today_usd=0.0)
    assert r and r.code == "venture.paused"


def test_preflight_refuses_an_unknown_venture():
    r = preflight(VENTURED, ventures={}, budget=BUDGET, spent_today_usd=0.0, dispatched_today_usd=0.0)
    assert r and r.code == "venture.unknown"


def test_preflight_refuses_when_the_day_cap_would_be_crossed():
    r = preflight(SPEC, ventures=VENTURE, budget={"company_day_cap_usd": 1.0},
                  spent_today_usd=0.5, dispatched_today_usd=0.0)
    assert r and r.code == "budget.day_cap"


def test_preflight_refuses_when_the_company_is_paused():
    r = preflight(SPEC, ventures=VENTURE, budget={"paused": True, "company_day_cap_usd": 20},
                  spent_today_usd=0.0, dispatched_today_usd=0.0)
    assert r and r.code == "company.paused"


# ---------------------------------------------------------------- worker
def test_worker_loads_every_routine_with_no_problems():
    w = Worker()
    assert w.problems == []
    assert len(w.specs) >= 6


def test_due_selects_only_the_routines_scheduled_for_that_minute():
    w = Worker()
    at_6 = [s.id for s in w.due(datetime(2026, 11, 10, 6, 0))]
    assert "scout-daily" in at_6 and "weekly-review" not in at_6
    at_quarter = [s.id for s in w.due(datetime(2026, 11, 10, 6, 15))]
    assert "incident-watch" in at_quarter and "scout-daily" not in at_quarter


def test_dispatch_writes_a_run_and_an_audit_row():
    store = Store()
    w = Worker(store=store)
    out = w.dispatch("scout-daily", when=datetime(2026, 11, 10, 6, 0))
    assert out["ok"] is True and out["run_id"]
    row = store.audit_tail(1)[0]
    assert row["action"] == "routine.dispatch" and row["decision"] == "allow"
    assert row["initiator_kind"] == "routine" and row["initiator_id"] == "scout-daily"


def _state(tmp_path, *, paused: bool):
    (tmp_path / "active_ventures.yaml").write_text(yaml.safe_dump({"ventures": [
        {"slug": "media-api", "status": "paused" if paused else "discovery", "paused": paused}]}))
    (tmp_path / "budget.json").write_text('{"company_day_cap_usd": 20, "spent_today_usd": 0}')
    return str(tmp_path)


def test_a_paused_venture_stops_its_routines_and_says_so(tmp_path):
    store = Store()
    w = Worker(routines_dir=str(ROUTINES), store=store, state_dir=_state(tmp_path, paused=True))
    w.specs = [VENTURED]
    out = w.dispatch("scout-daily")
    assert out["ok"] is False and out["code"] == "venture.paused"
    assert "paused by the owner" in out["reason"]
    row = store.audit_tail(1)[0]
    assert row["decision"] == "deny" and row["rule"] == "venture.paused"


def test_a_venture_with_auto_spend_pre_revenue_is_refused(tmp_path):
    state = _state(tmp_path, paused=False)
    (tmp_path / "active_ventures.yaml").write_text(yaml.safe_dump(
        {"ventures": [{"slug": "media-api", "status": "discovery", "paused": False}]}))
    w = Worker(routines_dir=str(ROUTINES), store=Store(), state_dir=state)
    w.specs = [VENTURED]
    out = w.dispatch("scout-daily")
    # the real manifest has auto_spend 0, so this run is allowed
    assert out["ok"] is True


def test_a_run_above_the_venture_day_budget_is_refused(tmp_path, monkeypatch):
    state = _state(tmp_path, paused=False)
    (tmp_path / "active_ventures.yaml").write_text(yaml.safe_dump(
        {"ventures": [{"slug": "media-api", "status": "launched", "paused": False}]}))
    monkeypatch.setattr("runner.load_venture_manifest",
                        lambda slug: {"status": "launched",
                                      "budgets": {"day_usd": 0.10, "auto_spend_usd": 0}})
    w = Worker(routines_dir=str(ROUTINES), store=Store(), state_dir=state)
    w.specs = [VENTURED]
    out = w.dispatch("scout-daily")
    assert out["ok"] is False and out["code"] == "venture.run_above_day_budget"


def test_the_same_routine_runs_when_the_venture_is_not_paused(tmp_path):
    w = Worker(routines_dir=str(ROUTINES), store=Store(), state_dir=_state(tmp_path, paused=False))
    w.specs = [VENTURED]
    assert w.dispatch("scout-daily")["ok"] is True


def test_a_sentinel_deny_stops_the_dispatch():
    store = Store()
    denied = {"decision": "deny", "rule": "isolation.write_root", "reason": "outside the venture"}

    def sentinel(action):
        return denied

    w = Worker(store=store, sentinel=sentinel, state_dir=str(ROUTINES.parent / "state"))
    w.specs = [VENTURED]
    out = w.dispatch("scout-daily")
    assert out["ok"] is False and out["code"] == "isolation.write_root"
    assert store.audit_tail(1)[0]["decision"] == "deny"


def test_unknown_routine_is_refused_not_created():
    assert Worker().dispatch("no-such-routine")["code"] == "routine.unknown"


def test_tick_is_idempotent_within_same_clock_minute():
    store = Store()
    w = Worker(store=store)
    t1 = datetime(2026, 11, 10, 6, 0, 5)
    t2 = datetime(2026, 11, 10, 6, 0, 45)
    first = w.tick(when=t1)
    assert any(r.get("routine") == "scout-daily" and r.get("ok") for r in first)
    second = w.tick(when=t2)
    assert not any(r.get("routine") == "scout-daily" for r in second)

