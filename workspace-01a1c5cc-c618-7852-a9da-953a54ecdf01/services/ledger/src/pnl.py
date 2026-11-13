"""P&L from rows. No opinions, no stored totals.

Every number the console or the weekly review shows is computed here from `ledger` rows, so a
replayed provider event cannot inflate revenue and a human cannot "fix" a month by editing a total.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

REVENUE = "revenue"
REFUND = "refund"
COGS = "cogs"           # compute, storage, egress billed per venture
AGENT_COST = "agent_cost"   # model/tool spend attributed to a venture
MARKETING = "marketing"
FEE = "fee"             # payment-provider fees
ADJUSTMENT = "adjustment"
KINDS = (REVENUE, REFUND, COGS, AGENT_COST, MARKETING, FEE, ADJUSTMENT)


class LedgerError(ValueError):
    pass


@dataclass(frozen=True)
class VenturePnL:
    venture: str
    revenue: float
    refunds: float
    cogs: float
    agent_cost: float
    marketing: float
    fees: float
    adjustments: float

    @property
    def net_revenue(self) -> float:
        return round(self.revenue - self.refunds + self.adjustments, 2)

    @property
    def gross_profit(self) -> float:
        return round(self.net_revenue - self.cogs - self.fees, 2)

    @property
    def gross_margin(self) -> float:
        return round(self.gross_profit / self.net_revenue, 4) if self.net_revenue else 0.0

    @property
    def contribution(self) -> float:
        """What the venture contributes after everything variable, including the agents."""
        return round(self.gross_profit - self.agent_cost - self.marketing, 2)

    @property
    def agent_share(self) -> float:
        """Agent spend as a share of net revenue — the metric that decides if this scales."""
        return round(self.agent_cost / self.net_revenue, 4) if self.net_revenue else 0.0

    def as_row(self) -> dict[str, Any]:
        return {
            "venture": self.venture,
            "revenue": self.revenue, "refunds": self.refunds,
            "net_revenue": self.net_revenue,
            "cogs": self.cogs, "fees": self.fees,
            "gross_profit": self.gross_profit, "gross_margin": self.gross_margin,
            "agent_cost": self.agent_cost, "agent_share": self.agent_share,
            "marketing": self.marketing, "contribution": self.contribution,
        }


def validate_row(row: dict[str, Any]) -> dict[str, Any]:
    """Reject a row that would corrupt the books, before it is stored."""
    kind = row.get("kind")
    if kind not in KINDS:
        raise LedgerError(f"kind {kind!r} not in {KINDS}")
    if not row.get("venture"):
        raise LedgerError("a ledger row needs a venture")
    if not row.get("idempotency_key"):
        raise LedgerError("a ledger row needs an idempotency_key (the provider event id)")
    try:
        amount = float(row.get("amount_usd"))
    except (TypeError, ValueError) as e:
        raise LedgerError(f"amount_usd is not a number: {row.get('amount_usd')!r}") from e
    if kind in (REVENUE, REFUND, COGS, AGENT_COST, MARKETING, FEE) and amount < 0:
        # A negative revenue row is an adjustment wearing a costume. Refuse it: use `adjustment`.
        raise LedgerError(f"{kind} must be >= 0; use kind=adjustment for a correction")
    out = dict(row)
    out["amount_usd"] = round(amount, 2)
    return out


def compute(rows: Iterable[dict[str, Any]]) -> dict[str, VenturePnL]:
    """Group rows by venture and derive every figure the company reports."""
    acc: dict[str, dict[str, float]] = {}
    for r in rows:
        v = r["venture"]
        bucket = acc.setdefault(v, dict.fromkeys(KINDS, 0.0))
        bucket[r["kind"]] = round(bucket[r["kind"]] + float(r["amount_usd"]), 2)
    out: dict[str, VenturePnL] = {}
    for v, b in acc.items():
        out[v] = VenturePnL(venture=v, revenue=b[REVENUE], refunds=b[REFUND], cogs=b[COGS],
                            agent_cost=b[AGENT_COST], marketing=b[MARKETING], fees=b[FEE],
                            adjustments=b[ADJUSTMENT])
    return out


def portfolio(pnl: dict[str, VenturePnL]) -> dict[str, Any]:
    def total(attr: str) -> float:
        return round(sum(getattr(v, attr) for v in pnl.values()), 2)

    net = total("net_revenue")
    return {
        "ventures": len(pnl),
        "net_revenue": net,
        "gross_profit": total("gross_profit"),
        "contribution": total("contribution"),
        "agent_cost": total("agent_cost"),
        "gross_margin": round(total("gross_profit") / net, 4) if net else 0.0,
        "agent_share": round(total("agent_cost") / net, 4) if net else 0.0,
    }


def mrr(rows: Iterable[dict[str, Any]], as_of: str | None = None) -> float:
    """Trailing-30-day recurring revenue from settled rows only.

    `as_of` is an ISO date (YYYY-MM-DD); rows are expected to carry `ts` in the same form. Rows
    without a period are treated as settled in their own month — the provider webhook date is the
    settlement date, and inventing a period would be inventing revenue.
    """
    from datetime import date, timedelta

    end = date.fromisoformat(as_of) if as_of else date.today()
    start = end - timedelta(days=30)
    total = 0.0
    for r in rows:
        if r["kind"] != REVENUE:
            continue
        d = date.fromisoformat(r["ts"][:10])
        if start <= d <= end:
            total += float(r["amount_usd"])
    return round(total, 2)


def reconcile(rows: Iterable[dict[str, Any]], provider_gross_usd: float) -> dict[str, Any]:
    """Compare our revenue rows to the provider's own statement. Never adjusts; reports."""
    ours = round(sum(float(r["amount_usd"]) - float(0) for r in rows if r["kind"] == REVENUE), 2)
    refunds = round(sum(float(r["amount_usd"]) for r in rows if r["kind"] == REFUND), 2)
    net = round(ours - refunds, 2)
    drift = round(net - round(provider_gross_usd, 2), 2)
    return {"our_net_revenue": net, "provider_gross": round(provider_gross_usd, 2),
            "drift_usd": drift, "ok": drift == 0.0}
