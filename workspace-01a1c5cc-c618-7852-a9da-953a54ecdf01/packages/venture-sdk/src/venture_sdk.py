"""Venture SDK — a business is a validated object, not a slide.

    python -m venture_sdk validate .openbot/ventures/media-api/venture.yaml

A venture that does not validate cannot be started by the worker, cannot get a policy file, and
cannot post to the ledger. The rules here encode the decisions in STACK_DECISIONS.md (D4: no
autonomous spend pre-revenue, D7: one venture until the first one pays) as code, because a rule in a
document is a suggestion and a rule in a loader is a boundary.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import Any

import yaml

SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{2,40}$")
STATUSES = ("discovery", "build", "launched", "scaling", "paused", "killed")
EGRESS_MODES = ("deny_all", "allowlist_only", "defaults_plus_allowlist", "allow_all")
DATA_CLASSES = ("public", "customer_pii", "internal")
PRICING_MODELS = ("metered_subscription", "flat_subscription", "usage", "one_off")
REQUIRED = ("slug", "name", "owner_agent", "status", "thesis", "icp", "wedge",
            "pricing", "unit_economics", "channels", "budgets", "guardrails",
            "kill_criteria", "ledger_account")


class VentureError(ValueError):
    """The venture cannot be operated as written."""


@dataclass(frozen=True)
class Venture:
    slug: str
    name: str
    status: str
    owner_agent: str
    thesis: str
    icp: str
    wedge: str
    pricing: dict[str, Any]
    unit_economics: dict[str, Any]
    channels: tuple[str, ...]
    budgets: dict[str, Any]
    guardrails: dict[str, Any]
    kill_criteria: tuple[str, ...]
    ledger_account: str
    raw: dict[str, Any] = field(default_factory=dict)

    # -- derived facts a reviewer should not have to compute by hand -------------
    @property
    def plans(self) -> list[dict[str, Any]]:
        return list(self.pricing.get("plans") or [])

    @property
    def max_plan_usd_month(self) -> float:
        return max((float(p.get("usd_month") or 0) for p in self.plans), default=0.0)

    @property
    def gross_margin_per_unit(self) -> float:
        """Fraction of revenue left after measured COGS at the smallest plan."""
        if not self.plans:
            return 0.0
        plan = min(self.plans, key=lambda p: float(p.get("usd_month") or 0))
        price = float(plan.get("usd_month") or 0)
        units = float(plan.get("included_units") or 0)
        cogs = float(self.unit_economics.get("cogs_per_1k_units_usd") or 0) * units / 1000
        return round((price - cogs) / price, 4) if price else 0.0

    @property
    def payback_months(self) -> float:
        """Months of contribution to repay CAC, at the smallest plan and measured COGS."""
        if not self.plans:
            return 0.0
        plan = min(self.plans, key=lambda p: float(p.get("usd_month") or 0))
        price = float(plan.get("usd_month") or 0)
        units = float(plan.get("included_units") or 0)
        cogs = float(self.unit_economics.get("cogs_per_1k_units_usd") or 0) * units / 1000
        contribution = price - cogs
        cac = float(self.unit_economics.get("cac_target_usd") or 0)
        return round(cac / contribution, 2) if contribution > 0 else float("inf")

    def summary(self) -> dict[str, Any]:
        return {
            "slug": self.slug, "status": self.status, "owner": self.owner_agent,
            "plans": [(p.get("name"), p.get("usd_month")) for p in self.plans],
            "gross_margin_at_smallest_plan": self.gross_margin_per_unit,
            "payback_months_at_target_cac": self.payback_months,
            "budgets": self.budgets,
            "egress_mode": self.guardrails.get("egress_mode"),
            "kill_criteria": len(self.kill_criteria),
        }


def _need(d: dict[str, Any], key: str, problems: list[str], where: str = "") -> Any:
    if d.get(key) in (None, "", [], {}):
        problems.append(f"{where}{key} is required")
        return None
    return d[key]


def validate_document(raw: dict[str, Any]) -> Venture:
    problems: list[str] = []
    if not isinstance(raw, dict):
        raise VentureError("a venture manifest is a YAML mapping")

    for key in REQUIRED:
        _need(raw, key, problems)

    slug = str(raw.get("slug") or "")
    if slug and not SLUG_RE.match(slug):
        problems.append(f"slug {slug!r} must be lowercase kebab-case (3–41 chars)")

    status = str(raw.get("status") or "")
    if status and status not in STATUSES:
        problems.append(f"status {status!r} must be one of {STATUSES}")

    if len(str(raw.get("thesis") or "").strip()) < 40:
        problems.append("thesis must be at least 40 characters — one sentence of why this exists")

    pricing = raw.get("pricing") or {}
    model = pricing.get("model")
    if model and model not in PRICING_MODELS:
        problems.append(f"pricing.model {model!r} must be one of {PRICING_MODELS}")
    plans = pricing.get("plans") or []
    if not plans:
        problems.append("pricing.plans needs at least one plan (a price is not optional)")
    for i, p in enumerate(plans):
        tag = f"pricing.plans[{i}]"
        if not p.get("name"):
            problems.append(f"{tag}.name is required")
        price = float(p.get("usd_month") or 0)
        if price <= 0:
            problems.append(f"{tag}.usd_month must be > 0")
        if float(p.get("included_units") or 0) <= 0:
            problems.append(f"{tag}.included_units must be > 0")
        if float(p.get("overage_usd") or 0) < 0:
            problems.append(f"{tag}.overage_usd cannot be negative")

    ue = raw.get("unit_economics") or {}
    cogs = float(ue.get("cogs_per_1k_units_usd") or 0)
    if cogs <= 0:
        problems.append("unit_economics.cogs_per_1k_units_usd must be > 0 and measured, not guessed")
    margin = float(ue.get("target_gross_margin") or 0)
    if not 0 < margin < 1:
        problems.append("unit_economics.target_gross_margin must be between 0 and 1")
    if float(ue.get("cac_target_usd") or 0) <= 0:
        problems.append("unit_economics.cac_target_usd must be > 0")
    if int(ue.get("payback_months_target") or 0) <= 0:
        problems.append("unit_economics.payback_months_target must be > 0")

    budgets = raw.get("budgets") or {}
    day = float(budgets.get("day_usd") or 0)
    month = float(budgets.get("month_usd") or 0)
    auto = float(budgets.get("auto_spend_usd") or 0)
    if day <= 0:
        problems.append("budgets.day_usd must be > 0")
    if month < day:
        problems.append("budgets.month_usd cannot be less than day_usd")
    if auto > day:
        problems.append("budgets.auto_spend_usd cannot exceed the daily budget")
    if status in ("discovery", "build") and auto > 0:
        problems.append(
            "budgets.auto_spend_usd must be 0 before a venture has settled revenue "
            "(STACK_DECISIONS D4) — a human approves every charge until then")

    guard = raw.get("guardrails") or {}
    if guard.get("egress_mode") not in EGRESS_MODES:
        problems.append(f"guardrails.egress_mode must be one of {EGRESS_MODES}")
    if guard.get("data_class") not in DATA_CLASSES:
        problems.append(f"guardrails.data_class must be one of {DATA_CLASSES}")
    if not guard.get("hitl"):
        problems.append("guardrails.hitl must name what a human always approves")

    channels = raw.get("channels") or []
    if not channels:
        problems.append("channels must name at least one acquisition channel before you build")

    criteria = [str(c).strip() for c in (raw.get("kill_criteria") or []) if str(c).strip()]
    if len(criteria) < 2:
        problems.append("kill_criteria needs at least two written criteria")
    for c in criteria:
        if not re.search(r"\d", c):
            problems.append(
                f"kill criterion {c!r} has no number in it, so nobody can tell when it is met")

    if problems:
        raise VentureError("venture is not operable:\n  - " + "\n  - ".join(problems))

    venture = Venture(
        slug=slug, name=str(raw["name"]), status=status, owner_agent=str(raw["owner_agent"]),
        thesis=str(raw["thesis"]).strip(), icp=str(raw["icp"]), wedge=str(raw["wedge"]),
        pricing=pricing, unit_economics=ue, channels=tuple(map(str, channels)),
        budgets=budgets, guardrails=guard, kill_criteria=tuple(criteria),
        ledger_account=str(raw["ledger_account"]), raw=raw,
    )

    # A margin that the plans cannot deliver is a plan that cannot work.
    target = float(margin)
    actual = venture.gross_margin_per_unit
    if actual + 1e-9 < target:
        raise VentureError(
            f"venture is not operable:\n  - the smallest plan yields {actual:.1%} gross margin at the "
            f"stated COGS, below the target {target:.1%}; raise the price or lower the COGS")

    return venture


def load(path: str) -> Venture:
    try:
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except OSError as e:
        raise VentureError(f"cannot read {path}: {e}") from e
    return validate_document(raw or {})


def load_all(directory: str) -> tuple[list[Venture], list[str]]:
    """Every venture under a directory. Never raises: one broken venture must not hide the others."""
    import glob
    import os

    ventures: list[Venture] = []
    problems: list[str] = []
    slugs: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(directory, "*", "venture.yaml"))):
        try:
            v = load(path)
        except VentureError as e:
            problems.append(f"{path}: {e}")
            continue
        if v.slug in slugs:
            problems.append(f"{path}: duplicate slug {v.slug!r} (also {slugs[v.slug]})")
            continue
        slugs[v.slug] = path
        ventures.append(v)
    return ventures, problems


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: python -m venture_sdk validate <venture.yaml|directory>")
        print("       python -m venture_sdk list <.openbot/ventures>")
        return 0
    cmd, target = argv[0], (argv[1] if len(argv) > 1 else ".")
    import os

    try:
        if cmd == "validate":
            if os.path.isdir(target):
                ventures, problems = load_all(target)
                for v in ventures:
                    print(f"OK      {v.slug:20} {v.status:10} margin {v.gross_margin_per_unit:.0%} "
                          f"payback {v.payback_months:g}mo")
                for p in problems:
                    print(f"REFUSED {p}")
                return 1 if problems else 0
            v = load(target)
            print(yaml.safe_dump(v.summary(), sort_keys=False).rstrip())
            return 0
        if cmd == "list":
            ventures, problems = load_all(target)
            for v in ventures:
                print(f"{v.slug}\t{v.status}\t{v.name}")
            for p in problems:
                print(f"REFUSED {p}", file=sys.stderr)
            return 1 if problems else 0
    except VentureError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"unknown command {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
