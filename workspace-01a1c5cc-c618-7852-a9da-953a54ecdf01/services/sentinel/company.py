"""OpenBot OS — the company, as data the runtime can check.

`company/company.yaml` is the org chart, the job descriptions and the prohibitions. This module
loads it and refuses to load a company that could not legally or safely operate. It is imported by
the Sentinel at boot, by the worker before it fires a duty, and by `scripts/verify.sh` in CI.

Design rule: if a check here can be expressed as code, it must not live in a prompt.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Literal

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
KNOWN_AGENT_IMPLS_EXPECTED = 16      # OpenBot ships this many `agent-*` frameworks; a typo is a lie
CRON_RE = re.compile(r"^(\S+\s+){4}\S+$")
MIN_ROUTINE_INTERVAL_MIN = 15


class CompanyError(ValueError):
    """The company definition cannot be operated as written."""


@dataclass(frozen=True)
class Role:
    id: str
    kind: Literal["human", "agent"]
    title: str
    reports_to: str | None
    mandate: str
    may: frozenset[str] = frozenset()
    may_not: frozenset[str] = frozenset()
    agent_impl: str | None = None
    tools: tuple[str, ...] = ()
    kpi: tuple[str, ...] = ()
    cost_ceiling_usd_month: float = 0.0


@dataclass(frozen=True)
class Duty:
    id: str
    role: str
    routine: str
    cadence: str


@dataclass(frozen=True)
class Company:
    trading_name: str
    legal_name: str | None
    formation: str
    roles: tuple[Role, ...]
    duties: tuple[Duty, ...]
    prohibitions: tuple[str, ...]
    meta: dict[str, Any] = field(default_factory=dict)

    # -- convenience ---------------------------------------------------------
    def role(self, role_id: str) -> Role:
        for r in self.roles:
            if r.id == role_id:
                return r
        raise CompanyError(f"no such role: {role_id}")

    def agents(self) -> tuple[Role, ...]:
        return tuple(r for r in self.roles if r.kind == "agent")

    def humans(self) -> tuple[Role, ...]:
        return tuple(r for r in self.roles if r.kind == "human")

    def chain(self, role_id: str) -> list[str]:
        """Escalation path from a role up to the human who is accountable for it."""
        out, seen = [], set()
        cur: str | None = role_id
        while cur and cur not in seen:
            seen.add(cur)
            out.append(cur)
            cur = self.role(cur).reports_to
        return out

    def duty_routines(self) -> tuple[str, ...]:
        return tuple(d.routine for d in self.duties)


# --------------------------------------------------------------------------- loading


def _read_routine_front_matter(path: str) -> dict[str, Any]:
    """Read the YAML block between the first two `---` lines. Missing file is an error."""
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        raise CompanyError(f"duty routine does not exist: {path}")
    with open(full, encoding="utf-8") as fh:
        text = fh.read()
    if not text.startswith("---"):
        raise CompanyError(f"{path}: no YAML front-matter")
    end = text.find("\n---", 3)
    if end == -1:
        raise CompanyError(f"{path}: unterminated front-matter")
    meta = yaml.safe_load(text[3:end]) or {}
    if not isinstance(meta, dict):
        raise CompanyError(f"{path}: front-matter is not a mapping")
    return meta


def _cron_minutes(expr: str) -> int | None:
    """Smallest gap between fires for simple `*/N`, `M * * * *`, `M H * * *` expressions."""
    parts = expr.split()
    if len(parts) != 5:
        return None
    minute, hour = parts[0], parts[1]
    m = re.fullmatch(r"\*/(\d+)", minute)
    if m and hour == "*":
        return int(m.group(1))
    if minute.isdigit() and hour == "*":
        return 60
    if minute.isdigit() and hour.isdigit():
        return 24 * 60
    return None


def load_company(path: str | None = None, *, check_routines: bool = True,
                 known_agent_impls: frozenset[str] | None = None,
                 company_month_cap_usd: float | None = None) -> Company:
    path = path or os.path.join(ROOT, "company", "company.yaml")
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh.read()) or {}
    meta = raw.get("company") or {}
    problems: list[str] = []

    roles_raw = raw.get("roles") or []
    roles: list[Role] = []
    seen_ids: set[str] = set()
    for r in roles_raw:
        rid = r.get("id")
        if not rid:
            problems.append("a role has no id")
            continue
        if rid in seen_ids:
            problems.append(f"duplicate role id: {rid}")
        seen_ids.add(rid)
        kind = r.get("kind")
        if kind not in ("human", "agent"):
            problems.append(f"{rid}: kind must be human|agent, got {kind!r}")
        may, may_not = set(r.get("may") or []), set(r.get("may_not") or [])
        both = may & may_not
        if both:
            problems.append(f"{rid}: capability both allowed and forbidden: {sorted(both)}")
        roles.append(Role(
            id=rid, kind=kind or "agent", title=r.get("title") or rid,
            reports_to=r.get("reports_to"), mandate=(r.get("mandate") or "").strip(),
            may=frozenset(may), may_not=frozenset(may_not),
            agent_impl=r.get("agent_impl"),
            tools=tuple(r.get("tools") or ()), kpi=tuple(r.get("kpi") or ()),
            cost_ceiling_usd_month=float(r.get("cost_ceiling_usd_month") or 0.0),
        ))

    # -- hierarchy ---------------------------------------------------------
    roots = [r for r in roles if r.reports_to is None]
    if len(roots) != 1:
        problems.append(f"exactly one role must have reports_to: null (found {len(roots)})")
    elif roots[0].kind != "human":
        problems.append("the root of the hierarchy must be a human, never an agent")
    for r in roles:
        if r.reports_to and r.reports_to not in seen_ids:
            problems.append(f"{r.id}: reports_to unknown role {r.reports_to!r}")
    # cycles
    for r in roles:
        seen, cur = set(), r
        while cur and cur.reports_to:
            if cur.id in seen:
                problems.append(f"{r.id}: reporting cycle")
                break
            seen.add(cur.id)
            cur = next((x for x in roles if x.id == cur.reports_to), None)

    # -- roles that make decisions need a human above them ------------------
    for r in roles:
        if r.kind == "agent" and not r.mandate:
            problems.append(f"{r.id}: agent role with no mandate")
        if r.kind == "agent" and not r.may_not:
            problems.append(f"{r.id}: agent role with no may_not boundary")
        if r.kind == "agent" and not r.agent_impl:
            problems.append(f"{r.id}: agent role without an agent_impl (what runs it?)")
        if r.kind == "human" and not any(c.startswith("approve_") for c in r.may):
            problems.append(f"{r.id}: a human role must be able to approve something")
    if not any(r.kind == "human" for r in roles):
        problems.append("a company with no human cannot legally sign or pay")

    # -- agent_impl must be a framework OpenBot actually ships --------------
    # Two sources, in order of authority: the substrate on disk (the truth), then the committed
    # manifest (a fallback for machines without the substrate — e.g. a fresh clone or CI). If neither
    # exists we must refuse: silently skipping this check is exactly how `agent-nope` gets deployed.
    impl_dir = os.path.join(ROOT, "repos", "OpenBot")
    available = frozenset()
    if known_agent_impls:
        available = frozenset(known_agent_impls)
    elif os.path.isdir(impl_dir):
        available = frozenset(
            n[len("agent-"):] for n in os.listdir(impl_dir)
            if n.startswith("agent-") and os.path.isdir(os.path.join(impl_dir, n))
        )
    else:
        manifest = os.path.join(ROOT, "company", "agent_impls.yaml")
        try:
            with open(manifest, encoding="utf-8") as fh:
                available = frozenset((yaml.safe_load(fh.read()) or {}).get("agent_impls") or ())
        except OSError:
            available = frozenset()
        if not available:
            problems.append(
                "cannot verify agent_impl: neither repos/OpenBot nor company/agent_impls.yaml is "
                "present — refusing to load a company naming runtimes nobody can confirm exist")
    if available:
        for r in roles:
            if r.kind == "agent" and r.agent_impl:
                short = r.agent_impl.replace("agent-", "", 1)
                if available and short not in available:
                    problems.append(
                        f"{r.id}: agent_impl {r.agent_impl!r} is not one of OpenBot's "
                        f"agent-* frameworks ({', '.join(sorted(available))})")

    # -- duties must be real, scheduled, budgeted, and unattended ----------
    duties: list[Duty] = []
    duty_ids: set[str] = set()
    for d in raw.get("duties") or []:
        did = d.get("id")
        if did in duty_ids:
            problems.append(f"duplicate duty id: {did}")
        duty_ids.add(did)
        role_id = d.get("role")
        if role_id not in seen_ids:
            problems.append(f"duty {did}: unknown role {role_id!r}")
        cadence = str(d.get("cadence") or "")
        if not CRON_RE.match(cadence):
            problems.append(f"duty {did}: cadence {cadence!r} is not a 5-field cron")
        routine = d.get("routine") or ""
        if check_routines:
            try:
                fm = _read_routine_front_matter(routine)
            except CompanyError as e:
                problems.append(f"duty {did}: {e}")
                fm = {}
            if fm:
                if str(fm.get("schedule")) != cadence:
                    problems.append(
                        f"duty {did}: cadence {cadence!r} != routine schedule {fm.get('schedule')!r}")
                if fm.get("initiator") != "routine":
                    problems.append(f"duty {did}: routine must declare initiator: routine")
                if fm.get("bot") != role_id:
                    problems.append(
                        f"duty {did}: routine runs as {fm.get('bot')!r} but the duty belongs to {role_id!r}")
                if not fm.get("budget_usd"):
                    problems.append(f"duty {did}: routine has no budget_usd")
                if not fm.get("max_runtime_min"):
                    problems.append(f"duty {did}: routine has no max_runtime_min")
                gap = _cron_minutes(cadence)
                if gap is not None and gap < MIN_ROUTINE_INTERVAL_MIN:
                    problems.append(
                        f"duty {did}: fires every {gap} min, below the {MIN_ROUTINE_INTERVAL_MIN} min floor")
        duties.append(Duty(id=did, role=role_id, routine=routine, cadence=cadence))

    # -- prohibitions ------------------------------------------------------
    prohibitions = tuple(str(p).strip() for p in (raw.get("prohibitions") or []) if str(p).strip())
    if len(prohibitions) < 5:
        problems.append("fewer than 5 prohibitions: a company this autonomous needs a real list")

    # -- money: role ceilings cannot exceed the company cap -----------------
    total_ceiling = sum(r.cost_ceiling_usd_month for r in roles)
    if company_month_cap_usd is not None and total_ceiling > company_month_cap_usd:
        problems.append(
            f"role cost ceilings total ${total_ceiling:.0f}/mo, above the company cap "
            f"${company_month_cap_usd:.0f}/mo in .openbot/state/budget.json")

    if problems:
        raise CompanyError("company definition is not operable:\n  - " + "\n  - ".join(problems))

    return Company(
        trading_name=meta.get("trading_name") or "unnamed",
        legal_name=meta.get("legal_name"),
        formation=meta.get("formation") or "",
        roles=tuple(roles), duties=tuple(duties), prohibitions=prohibitions, meta=meta,
    )
