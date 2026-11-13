"""The company must be operable before any agent runs a duty.

These tests are the difference between an org chart and an org chart that means something: each one
takes a real company.yaml, breaks one thing, and requires the loader to refuse it.
"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from company import CompanyError, load_company  # noqa: E402

ROOT = pathlib.Path(__file__).parent.parent.parent.parent
BASE = yaml.safe_load((ROOT / "company" / "company.yaml").read_text())
CAP = 300.0


def broken(mutate) -> str:
    d = yaml.safe_load(yaml.dump(BASE))
    mutate(d)
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
        yaml.dump(d, fh)
        return fh.name


def test_the_real_company_loads():
    c = load_company(company_month_cap_usd=CAP)
    assert c.trading_name and len(c.roles) >= 5 and len(c.prohibitions) >= 5
    assert len(c.humans()) == 1, "exactly one accountable human"
    # every agent escalates to the human, in a finite number of hops
    for r in c.agents():
        assert c.chain(r.id)[-1] == "owner", r.id
    # every duty is a real, budgeted, unattended routine
    assert len(c.duties) == 6
    for d in c.duties:
        assert (ROOT / d.routine).exists(), d.routine


def test_every_agent_has_a_boundary_and_an_implementation():
    c = load_company(company_month_cap_usd=CAP)
    for r in c.agents():
        assert r.may_not, f"{r.id} has no may_not"
        assert r.agent_impl, f"{r.id} has no agent_impl"
        assert r.kpi, f"{r.id} has no KPI"


@pytest.mark.parametrize(
    "label,mutate",
    [
        ("no root", lambda d: [r.update(reports_to="ceo") for r in d["roles"] if r["id"] == "owner"]),
        ("agent root", lambda d: d["roles"][0].update(kind="agent")),
        ("unknown impl", lambda d: [r.update(agent_impl="agent-nope")
                                    for r in d["roles"] if r["id"] == "ceo"]),
        ("may and may_not overlap", lambda d: [r.update(may_not=list(r.get("may") or []))
                                               for r in d["roles"] if r["id"] == "growth"]),
        ("non-cron cadence", lambda d: d["duties"][0].update(cadence="every morning")),
        ("below the 15-minute floor", lambda d: d["duties"][1].update(cadence="*/5 * * * *")),
        ("too few prohibitions", lambda d: d.update(prohibitions=["be nice"])),
        ("ceilings above the company cap", lambda d: [r.update(cost_ceiling_usd_month=500)
                                                      for r in d["roles"]]),
        ("duty for a role that does not exist", lambda d: d["duties"][0].update(role="cmo")),
        ("agent with no may_not", lambda d: [r.update(may_not=[])
                                             for r in d["roles"] if r["id"] == "ops"]),
        ("missing routine file", lambda d: d["duties"][0].update(routine=".openbot/routines/nope.md")),
    ],
)
def test_an_inoperable_company_is_refused(label, mutate):
    path = broken(mutate)
    try:
        with pytest.raises(CompanyError):
            load_company(path, company_month_cap_usd=CAP)
    finally:
        os.unlink(path)


def test_auditor_does_not_report_to_the_role_it_audits():
    c = load_company(company_month_cap_usd=CAP)
    assert c.role("auditor").reports_to == "owner"
    assert "write_feature_code" in c.role("auditor").may_not


def test_no_agent_can_move_money_or_change_price():
    c = load_company(company_month_cap_usd=CAP)
    forbidden = {"spend_money", "change_price", "issue_refund", "move_money"}
    for r in c.agents():
        assert not (set(r.may) & forbidden), f"{r.id} may {set(r.may) & forbidden}"


# --------------------------------------------------------------------- the impl check cannot be
# skipped: a validator that silently passes when the substrate is missing is a false green, and a
# stranger's fresh clone (no repos/, which is a snapshot-excluded install) is exactly that machine.
def test_the_agent_impl_manifest_matches_the_substrate():
    """The committed fallback must agree with the pinned tree when both are present."""
    impl_dir = ROOT / "repos" / "OpenBot"
    if not impl_dir.is_dir():
        pytest.skip("substrate not installed on this machine")
    on_disk = {p.name[len("agent-"):] for p in impl_dir.glob("agent-*") if p.is_dir()}
    manifest = set(yaml.safe_load((ROOT / "company/agent_impls.yaml").read_text())["agent_impls"])
    assert manifest == on_disk, (
        "company/agent_impls.yaml drifted from repos/OpenBot — regenerate it (see its _comment)")


def test_a_company_naming_runtimes_that_cannot_be_verified_is_refused(monkeypatch, tmp_path):
    import company as company_mod

    # no substrate on disk *and* no committed manifest: the only honest answer is to refuse
    monkeypatch.setattr(company_mod.os.path, "isdir", lambda p: False)
    monkeypatch.setattr(company_mod, "ROOT", str(tmp_path))
    (tmp_path / "company").mkdir()          # a manifest-less tree, as a partial copy would be
    path = broken(lambda d: None)           # the real org chart, untouched
    try:
        with pytest.raises(CompanyError, match="cannot verify agent_impl"):
            load_company(path, company_month_cap_usd=CAP)
    finally:
        os.unlink(path)


def test_the_manifest_is_used_when_the_substrate_is_absent(monkeypatch):
    """With no repos/, the committed manifest still catches an invented runtime."""
    import company as company_mod

    monkeypatch.setattr(company_mod.os.path, "isdir", lambda p: False)

    def _broken(d):
        [r.update(agent_impl="agent-nope") for r in d["roles"] if r["id"] == "ceo"]

    path = broken(_broken)
    try:
        with pytest.raises(CompanyError, match="agent-nope"):
            load_company(path, company_month_cap_usd=CAP)
    finally:
        os.unlink(path)
