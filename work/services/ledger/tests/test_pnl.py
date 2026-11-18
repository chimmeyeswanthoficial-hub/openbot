"""The books must be impossible to flatter."""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from pnl import (  # noqa: E402
    LedgerError,
    compute,
    mrr,
    portfolio,
    reconcile,
    validate_row,
)

V = "media-api"


def row(kind: str, amount: float, key: str = "k", ts: str = "2026-11-08T10:00:00Z", **kw):
    d = {"venture": V, "kind": kind, "amount_usd": amount, "idempotency_key": key,
         "source": "stripe", "ts": ts}
    d.update(kw)
    return d


def test_revenue_minus_refunds_cogs_fees():
    rows = [row("revenue", 100, "e1"), row("refund", 20, "e2"), row("cogs", 12, "e3"),
            row("fee", 3, "e4"), row("agent_cost", 5, "e5"), row("marketing", 10, "e6")]
    p = compute(rows)[V]
    assert p.net_revenue == 80.0
    assert p.gross_profit == 65.0          # 80 - 12 - 3
    assert p.gross_margin == pytest.approx(0.8125, abs=1e-4)
    assert p.contribution == 50.0          # 65 - 5 - 10
    assert p.agent_share == pytest.approx(0.0625, abs=1e-4)


def test_no_revenue_means_no_margin_division_by_zero():
    p = compute([row("cogs", 5, "e1")])[V]
    assert p.gross_margin == 0.0 and p.agent_share == 0.0


def test_negative_revenue_is_refused():
    with pytest.raises(LedgerError):
        validate_row(row("revenue", -1, "x"))


def test_corrections_must_be_adjustments():
    assert validate_row(row("adjustment", -5, "x"))["amount_usd"] == -5.0


def test_row_without_idempotency_key_is_refused():
    with pytest.raises(LedgerError):
        validate_row({"venture": V, "kind": "revenue", "amount_usd": 1})


def test_unknown_kind_is_refused():
    with pytest.raises(LedgerError):
        validate_row(row("donation", 1))


def test_amounts_are_rounded_to_cents():
    assert validate_row(row("revenue", 19.005999))["amount_usd"] == 19.01


def test_mrr_only_counts_the_trailing_30_days():
    rows = [row("revenue", 19, "a", "2026-11-05T00:00:00Z"),
            row("revenue", 19, "b", "2026-10-20T00:00:00Z"),
            row("revenue", 19, "c", "2026-09-01T00:00:00Z"),   # outside
            row("refund", 19, "d", "2026-11-06T00:00:00Z")]    # refunds are not MRR
    assert mrr(rows, as_of="2026-11-10") == 38.0


def test_reconcile_reports_drift_and_never_adjusts():
    rows = [row("revenue", 100, "e1"), row("refund", 10, "e2")]
    ok = reconcile(rows, 90.0)
    assert ok["ok"] is True and ok["drift_usd"] == 0.0
    bad = reconcile(rows, 95.0)
    assert bad["ok"] is False and bad["drift_usd"] == -5.0


def test_portfolio_sums_across_ventures():
    rows = [row("revenue", 100, "e1"), row("cogs", 10, "e2"),
            dict(row("revenue", 50, "e3"), venture="second"),
            dict(row("cogs", 5, "e4"), venture="second")]
    port = portfolio(compute(rows))
    assert port["ventures"] == 2
    assert port["net_revenue"] == 150.0
    assert port["gross_profit"] == 135.0
