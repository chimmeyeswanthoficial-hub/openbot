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
import uuid
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import yaml
from spec import RoutineSpec, parse_dir
from work_store import WorkError, WorkStore, WorkUnavailable, minor, utc

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


def preflight(
    spec: RoutineSpec,
    *,
    ventures: dict[str, dict[str, Any]],
    budget: dict[str, Any],
    spent_today_usd: float,
    dispatched_today_usd: float,
) -> Refusal | None:
    """Everything that can say no before a model is involved."""
    venture = spec.venture
    if venture:
        v = ventures.get(venture)
        if v is None:
            return Refusal(
                spec.id, "venture.unknown", f"venture {venture!r} is not in active_ventures.yaml"
            )
        if v.get("paused"):
            return Refusal(spec.id, "venture.paused", f"venture {venture!r} is paused by the owner")
    cap = float(budget.get("company_day_cap_usd") or 0.0)
    try:
        exceeds = minor(spent_today_usd) + minor(dispatched_today_usd) + minor(
            spec.budget_usd
        ) > minor(cap)
    except WorkError:
        return Refusal(spec.id, "budget.invalid", "invalid finite USD upper bound")
    if exceeds:
        return Refusal(
            spec.id,
            "budget.day_cap",
            f"${spent_today_usd + dispatched_today_usd:.2f} spent + ${spec.budget_usd:.2f} for this run "
            f"exceeds the ${cap:.2f} daily cap",
        )
    if budget.get("paused"):
        return Refusal(spec.id, "company.paused", "the company is paused (state/budget.json)")

    # The manifest is the authority on money, not the summary file.
    if venture:
        manifest = load_venture_manifest(venture)
        budgets = manifest.get("budgets") or {}
        auto = float(budgets.get("auto_spend_usd") or 0.0)
        status = str(manifest.get("status") or "")
        if status in ("discovery", "build") and auto > 0:
            return Refusal(
                spec.id,
                "venture.auto_spend_pre_revenue",
                f"venture {venture!r} is {status} but auto_spend_usd is ${auto:.2f}; "
                "a human approves every charge until revenue settles (D4)",
            )
        day = float(budgets.get("day_usd") or 0.0)
        if day and spec.budget_usd > day:
            return Refusal(
                spec.id,
                "venture.run_above_day_budget",
                f"this run may spend ${spec.budget_usd:.2f}, above the venture's "
                f"${day:.2f} daily budget",
            )
    return None


# --------------------------------------------------------------------------- dispatch


class Worker:
    """Durable scheduling only. No implicit runtime/provider dispatch is enabled."""

    def __init__(self, routines_dir=None, *, store=None, sentinel=None, now=None, state_dir=None):
        self.dir = routines_dir or os.path.join(ROOT, ".openbot", "routines")
        self.state_dir = state_dir or STATE
        self.store, self.sentinel, self._now = store, sentinel, now
        self.specs, self.problems, self.work = [], [], None
        if store is not None:
            # Unavailable storage never falls back to in-memory authority.
            with suppress(WorkError, WorkUnavailable):
                self.work = WorkStore(store, initialize=store.initialize)
        self.reload()

    def reload(self):
        self.specs, self.problems = parse_dir(self.dir)

    def now(self):
        return self._now or datetime.now(UTC)

    def set_now(self, when):
        self._now = when

    def spec(self, routine_id):
        return next((s for s in self.specs if s.id == routine_id), None)

    def due(self, when=None):
        # Real daemon clocks are aware UTC; honor each spec's civil timezone.
        # Explicit naive clocks retain the historical test/embedding cron contract.
        when = when or self.now()
        return [
            s
            for s in self.specs
            if cron_matches(
                s.schedule,
                utc(when).astimezone(ZoneInfo(s.timezone)) if when.tzinfo is not None else when,
            )
        ]

    def _dispatched_today_usd(self, routine_id, when):
        if self.work is None:
            raise WorkError("durable_storage_required")
        return self.work.totals("platform", utc(when).date().isoformat())["company_day"] / 100

    def dispatch(
        self, routine_id, *, when=None, spent_today_usd=0.0, origin="manual", occurrence_key=None
    ):
        spec = self.spec(routine_id)
        if spec is None:
            return {"ok": False, "code": "routine.unknown", "routine": routine_id}
        if self.work is None:
            return {"ok": False, "code": "persistence.required", "routine": routine_id}
        if origin not in {"manual", "timer", "event"}:
            return {
                "ok": False,
                "code": "retry_requires_existing_occurrence",
                "routine": routine_id,
            }
        try:
            when = utc(when or self.now()).replace(second=0, microsecond=0)
            key = (
                when.isoformat()
                if origin == "timer"
                else occurrence_key or (str(uuid.uuid4()) if origin == "manual" else "")
            )
            row, created = self.work.register(
                venture=spec.venture or "platform",
                routine=spec.id,
                origin=origin,
                key=key,
                when=when,
                initiator={
                    "kind": "routine" if origin == "timer" else origin,
                    "id": spec.id if origin == "timer" else key,
                    "actor": "bot:" + spec.bot,
                },
                plan={"run_plan": spec.run_plan(), "body": spec.body},
                upper_minor=minor(spec.budget_usd),
            )
            if not created and row["status"] != "preparing":
                return {
                    "ok": False,
                    "code": "occurrence.exists",
                    "routine": spec.id,
                    "run_id": row["id"],
                    "status": row["status"],
                    "replayed": True,
                }
            ventures = load_ventures(os.path.join(self.state_dir, "active_ventures.yaml"))
            budget = load_budget(os.path.join(self.state_dir, "budget.json"))
            already = self._dispatched_today_usd(spec.id, when)
            refusal = preflight(
                spec,
                ventures=ventures,
                budget=budget,
                spent_today_usd=spent_today_usd,
                dispatched_today_usd=already,
            )
            verdict = {"decision": "allow", "rule": "dispatch.default"}
            if refusal:
                verdict = {"decision": "deny", "rule": refusal.code, "reason": refusal.reason}
            elif self.sentinel is not None and spec.venture:
                try:
                    reply = self.sentinel(
                        {
                            "kind": "routine.run",
                            "venture": spec.venture,
                            "actor": "bot:" + spec.bot,
                            "initiator": "routine",
                            "initiator_id": spec.id,
                            "name": "run routine " + spec.id,
                            "cost_usd": spec.budget_usd,
                        }
                    )
                    if not isinstance(reply, dict):
                        raise ValueError("invalid verdict")
                    effect = reply.get("effect", reply.get("decision"))
                    if effect not in ("allow", "deny", "gate") or (
                        "effect" in reply
                        and "decision" in reply
                        and reply["effect"] != reply["decision"]
                    ):
                        raise ValueError("invalid verdict")
                    verdict = {**reply, "decision": effect}
                except Exception:
                    verdict = {
                        "decision": "deny",
                        "rule": "sentinel.invalid_or_unreachable",
                        "reason": "governance boundary unavailable or invalid; nothing queued",
                    }
            effect = verdict["decision"]
            if effect != "allow":
                self.work.reject(
                    row["id"],
                    verdict["rule"],
                    state="review" if effect == "gate" else "blocked" if refusal else "denied",
                )
            else:
                day = minor(budget.get("company_day_cap_usd", 0))
                month = minor(
                    budget.get("company_month_cap_usd", budget.get("company_day_cap_usd", 0))
                )
                manifest = load_venture_manifest(spec.venture) if spec.venture else {}
                caps = manifest.get("budgets") or {}
                if self.work.setup:
                    self.work.configure(
                        spec.venture or "platform",
                        {
                            "run": 5000,
                            "company_day": max(
                                0,
                                day - minor(max(spent_today_usd, budget.get("spent_today_usd", 0))),
                            ),
                            "company": max(0, month - minor(budget.get("spent_month_usd", 0))),
                            "venture_day": minor(
                                caps.get("day_usd", budget.get("company_day_cap_usd", 0))
                            ),
                            "venture": minor(
                                caps.get(
                                    "month_usd",
                                    budget.get(
                                        "company_month_cap_usd",
                                        budget.get("company_day_cap_usd", 0),
                                    ),
                                )
                            ),
                        },
                    )
                if not self.work.reserve(row["id"]):
                    current = self.work.get(row["id"])
                    if current["status"] != "blocked":
                        # Another worker may have resumed the same previously
                        # unreserved occurrence. Never report a fresh dispatch.
                        return {
                            "ok": False,
                            "code": "occurrence.exists",
                            "routine": spec.id,
                            "run_id": row["id"],
                            "status": current["status"],
                            "replayed": True,
                        }
                    verdict = {
                        "decision": "deny",
                        "rule": "budget.day_cap",
                        "reason": "whole-liability reservation refused",
                    }
                    effect = "deny"
            # Compatibility audit is also durable before a caller sees a queued result.
            self.store.audit(
                {
                    "run_id": row["id"],
                    "venture": spec.venture or "platform",
                    "actor": "bot:" + spec.bot,
                    "action": "routine.dispatch",
                    "decision": effect,
                    "rule": verdict.get("rule") or "policy." + effect,
                    "reason": verdict.get("reason")
                    or "durable occurrence queued; runtime not activated",
                    "approval_id": verdict.get("approval_id"),
                    "initiator": {"kind": "routine", "id": spec.id},
                }
            )
            if effect != "allow":
                return {
                    "ok": False,
                    "routine": spec.id,
                    "run_id": row["id"],
                    "code": verdict["rule"],
                    "reason": verdict.get("reason"),
                    "approval_id": verdict.get("approval_id"),
                }
            return {
                "ok": True,
                "routine": spec.id,
                "run_id": row["id"],
                "bot": spec.bot,
                "budget_usd": spec.budget_usd,
                "plan": spec.run_plan(),
                "runtime_activated": False,
            }
        except (WorkError, WorkUnavailable, OSError, ValueError, TypeError):
            return {"ok": False, "code": "persistence_or_budget.unavailable", "routine": routine_id}

    def tick(self, *, when=None):
        when = when or self.now()
        results = []
        for spec in self.due(when):
            out = self.dispatch(spec.id, when=when, origin="timer")
            if out.get("code") != "occurrence.exists":
                results.append(out)
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


__all__ = [
    "Worker",
    "Refusal",
    "Dispatch",
    "cron_matches",
    "next_fire",
    "preflight",
    "load_ventures",
    "load_budget",
    "summarise",
    "utcnow",
    "time",
]
