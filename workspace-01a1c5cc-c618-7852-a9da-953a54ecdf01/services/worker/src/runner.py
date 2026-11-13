"""The worker: turn due routines into dispatched runs, or refuse and say why.

The worker does not run the model. Its job is the decision *about* the run:

    paused venture?  -> refuse
    over budget?     -> refuse
    policy says no?  -> refuse
    otherwise        -> dispatch (a Bot picks it up) + audit row

That boundary is deliberate. The scheduler deciding whether an unattended run may happen at all is
a governance function, and it must be testable without a model in the loop.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import yaml
from spec import RoutineSpec, parse_dir

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
STATE = os.path.join(ROOT, ".openbot", "state")


# --------------------------------------------------------------------------- cron


def _field_match(field: str, value: int, *, minimum: int, maximum: int) -> bool:
    if field == "*":
        return True
    for part in field.split(","):
        step = 1
        if "/" in part:
            part, _, step_s = part.partition("/")
            step = int(step_s)
        if part == "*":
            lo, hi = minimum, maximum
        elif "-" in part:
            lo_s, _, hi_s = part.partition("-")
            lo, hi = int(lo_s), int(hi_s)
        else:
            lo = hi = int(part)
        if lo <= value <= hi and (value - lo) % step == 0:
            return True
    return False


def cron_matches(expr: str, when: datetime) -> bool:
    minute, hour, dom, month, dow = expr.split()
    if not _field_match(minute, when.minute, minimum=0, maximum=59):
        return False
    if not _field_match(hour, when.hour, minimum=0, maximum=23):
        return False
    if not _field_match(dom, when.day, minimum=1, maximum=31):
        return False
    if not _field_match(month, when.month, minimum=1, maximum=12):
        return False
    # cron: 0 and 7 are both Sunday
    return _field_match(dow, when.isoweekday() % 7, minimum=0, maximum=6)


# --------------------------------------------------------------------------- state


def load_ventures(path: str | None = None) -> dict[str, dict[str, Any]]:
    p = path or os.path.join(STATE, "active_ventures.yaml")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return {v["slug"]: v for v in data.get("ventures", []) if v.get("slug")}


def load_venture_manifest(slug: str) -> dict[str, Any]:
    """Read the venture manifest itself; the worker refuses to trust the summary in state/."""
    path = os.path.join(ROOT, ".openbot", "ventures", slug, "venture.yaml")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_budget(path: str | None = None) -> dict[str, Any]:
    p = path or os.path.join(STATE, "budget.json")
    if not os.path.exists(p):
        return {"company_day_cap_usd": 0.0, "spent_today_usd": 0.0}
    return json.load(open(p, encoding="utf-8"))


# --------------------------------------------------------------------------- decisions


@dataclass(frozen=True)
class Refusal:
    routine_id: str
    code: str
    reason: str


@dataclass(frozen=True)
class Dispatch:
    routine_id: str
    venture: str
    bot: str
    budget_usd: float
    plan: dict[str, Any]


def preflight(spec: RoutineSpec, *, ventures: dict[str, dict[str, Any]],
              budget: dict[str, Any], spent_today_usd: float,
              dispatched_today_usd: float) -> Refusal | None:
    """Everything that can say no before a model is involved."""
    venture = spec.venture
    if venture:
        v = ventures.get(venture)
        if v is None:
            return Refusal(spec.id, "venture.unknown", f"venture {venture!r} is not in active_ventures.yaml")
        if v.get("paused"):
            return Refusal(spec.id, "venture.paused", f"venture {venture!r} is paused by the owner")
    cap = float(budget.get("company_day_cap_usd") or 0.0)
    if spent_today_usd + dispatched_today_usd + spec.budget_usd > cap:
        return Refusal(
            spec.id, "budget.day_cap",
            f"${spent_today_usd + dispatched_today_usd:.2f} spent + ${spec.budget_usd:.2f} for this run "
            f"exceeds the ${cap:.2f} daily cap")
    if budget.get("paused"):
        return Refusal(spec.id, "company.paused", "the company is paused (state/budget.json)")

    # The manifest is the authority on money, not the summary file.
    if venture:
        manifest = load_venture_manifest(venture)
        budgets = manifest.get("budgets") or {}
        auto = float(budgets.get("auto_spend_usd") or 0.0)
        status = str(manifest.get("status") or "")
        if status in ("discovery", "build") and auto > 0:
            return Refusal(spec.id, "venture.auto_spend_pre_revenue",
                           f"venture {venture!r} is {status} but auto_spend_usd is ${auto:.2f}; "
                           "a human approves every charge until revenue settles (D4)")
        day = float(budgets.get("day_usd") or 0.0)
        if day and spec.budget_usd > day:
            return Refusal(spec.id, "venture.run_above_day_budget",
                           f"this run may spend ${spec.budget_usd:.2f}, above the venture's "
                           f"${day:.2f} daily budget")
    return None


# --------------------------------------------------------------------------- dispatch


class Worker:
    """Holds the routine set and decides what is due. No model, no network, no clock surprises."""

    def __init__(self, routines_dir: str | None = None, *, store=None, sentinel=None,
                 now: datetime | None = None, state_dir: str | None = None) -> None:
        self.dir = routines_dir or os.path.join(ROOT, ".openbot", "routines")
        self.state_dir = state_dir or STATE
        self.store = store
        self.sentinel = sentinel          # callable(action: dict) -> dict, injected for tests
        self._now = now
        self.specs: list[RoutineSpec] = []
        self.problems: list[str] = []
        self._last_fired: dict[str, str] = {}
        self.reload()

    # -- lifecycle -----------------------------------------------------------
    def reload(self) -> None:
        self.problems = []
        specs, problems = parse_dir(self.dir)
        self.specs, self.problems = specs, problems

    def now(self) -> datetime:
        if self._now:
            return self._now
        return datetime.now(UTC).replace(tzinfo=None)

    def set_now(self, when: datetime | None) -> None:
        self._now = when

    def spec(self, routine_id: str) -> RoutineSpec | None:
        return next((s for s in self.specs if s.id == routine_id), None)

    # -- due -----------------------------------------------------------------
    def due(self, when: datetime | None = None) -> list[RoutineSpec]:
        when = when or self.now()
        return [s for s in self.specs if cron_matches(s.schedule, when)]

    # -- the one decision ----------------------------------------------------
    def dispatch(self, routine_id: str, *, when: datetime | None = None,
                 spent_today_usd: float = 0.0) -> dict[str, Any]:
        spec = self.spec(routine_id)
        if spec is None:
            return {"ok": False, "code": "routine.unknown", "routine": routine_id}

        ventures = load_ventures(os.path.join(self.state_dir, "active_ventures.yaml"))
        budget = load_budget(os.path.join(self.state_dir, "budget.json"))
        already = self._dispatched_today_usd(routine_id, when or self.now())

        refusal = preflight(spec, ventures=ventures, budget=budget,
                            spent_today_usd=spent_today_usd, dispatched_today_usd=already)
        if refusal:
            if self.store:
                rid = self.store.start_run(spec.id, spec.venture or "platform")
                self.store.end_run(rid, "refused", 0.0, f"{refusal.code}: {refusal.reason}")
                self.store.audit({"run_id": rid, "venture": spec.venture or "platform",
                                  "action": "routine.dispatch", "decision": "deny",
                                  "rule": refusal.code, "reason": refusal.reason,
                                  "initiator": {"kind": "routine", "id": spec.id}})
            return {"ok": False, "code": refusal.code, "routine": spec.id,
                    "reason": refusal.reason}

        # The policy boundary applies to a dispatch too: it is an action by an unattended actor.
        decision: dict[str, Any] = {"decision": "allow", "rule": "dispatch.default"}
        if self.sentinel is not None and spec.venture:
            decision = self.sentinel({
                "kind": "routine.run", "venture": spec.venture, "actor": f"bot:{spec.bot}",
                "initiator": "routine", "initiator_id": spec.id,
                "name": f"run routine {spec.id}", "cost_usd": spec.budget_usd,
            })
        if decision.get("decision") == "deny":
            if self.store:
                rid = self.store.start_run(spec.id, spec.venture or "platform")
                self.store.end_run(rid, "denied", 0.0, decision.get("rule"))
                self.store.audit({"run_id": rid, "venture": spec.venture or "platform",
                                  "action": "routine.dispatch", "decision": "deny",
                                  "rule": decision.get("rule") or "policy.deny",
                                  "reason": decision.get("reason") or "",
                                  "initiator": {"kind": "routine", "id": spec.id}})
            return {"ok": False, "code": decision.get("rule") or "policy.deny",
                    "routine": spec.id, "reason": decision.get("reason")}

        run_id = None
        if self.store:
            run_id = self.store.start_run(spec.id, spec.venture or "platform")
            self.store.audit({"run_id": run_id, "venture": spec.venture or "platform",
                              "action": "routine.dispatch", "decision": "allow",
                              "rule": decision.get("rule") or "dispatch.default",
                              "reason": "dispatched to the bot",
                              "initiator": {"kind": "routine", "id": spec.id},
                              "cost_usd": 0.0})
            self.store.end_run(run_id, "queued", 0.0, "dispatched")
        return {"ok": True, "routine": spec.id, "run_id": run_id, "bot": spec.bot,
                "budget_usd": spec.budget_usd, "plan": spec.run_plan()}

    def _dispatched_today_usd(self, routine_id: str, when: datetime) -> float:
        """What has already been committed today, so a loop cannot exceed the cap by repeating."""
        if not self.store:
            return 0.0
        today = when.strftime("%Y-%m-%d")
        return sum(
            s.budget_usd for s in self.specs
            if s.id != routine_id
            for _ in range(self._runs_today(s.id, today))
        )

    def _runs_today(self, routine_id: str, day: str) -> int:
        if not self.store:
            return 0
        return sum(1 for r in self.store.runs(500)
                   if r["routine_id"] == routine_id and r["started"].startswith(day)
                   and r["status"] in ("queued", "succeeded"))

    # -- the tick ------------------------------------------------------------
    def tick(self, *, when: datetime | None = None) -> list[dict[str, Any]]:
        """Fire everything due exactly once for this clock minute."""
        when = when or self.now()
        minute_key = when.strftime("%Y-%m-%d %H:%M")
        results = []
        for spec in self.due(when):
            if self._last_fired.get(spec.id) == minute_key:
                continue
            self._last_fired[spec.id] = minute_key
            results.append(self.dispatch(spec.id, when=when))
        return results


def summarise(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    results = list(results)
    return {
        "fired": sum(1 for r in results if r.get("ok")),
        "refused": sum(1 for r in results if not r.get("ok")),
        "detail": results,
    }


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def next_fire(expr: str, after: datetime, *, horizon_min: int = 60 * 24 * 8) -> datetime | None:
    """When does this routine fire next? Used by the console so a person can see the schedule."""
    t = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(horizon_min):
        if cron_matches(expr, t):
            return t
        t += timedelta(minutes=1)
    return None


__all__ = ["Worker", "Refusal", "Dispatch", "cron_matches", "next_fire", "preflight",
           "load_ventures", "load_budget", "summarise", "utcnow", "time"]
