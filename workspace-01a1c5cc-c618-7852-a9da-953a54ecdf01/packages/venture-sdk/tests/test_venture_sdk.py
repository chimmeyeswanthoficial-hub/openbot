"""A venture that cannot work must not be startable."""

from __future__ import annotations

import pathlib
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from venture_sdk import VentureError, load, load_all, validate_document  # noqa: E402

ROOT = pathlib.Path(__file__).parents[3]
REAL = yaml.safe_load((ROOT / ".openbot/ventures/media-api/venture.yaml").read_text())


def bad(**patch) -> dict:
    d = yaml.safe_load(yaml.dump(REAL))
    for dotted, value in patch.items():
        node = d
        keys = dotted.split(".")
        for k in keys[:-1]:
            node = node[k]
        node[keys[-1]] = value
    return d


def test_the_real_venture_validates_and_reports_its_economics():
    v = load(str(ROOT / ".openbot" / "ventures" / "media-api" / "venture.yaml"))
    assert v.slug == "media-api" and v.status == "discovery"
    # $19 plan, 5,000 units, $0.12 per 1,000 units → COGS $0.60 → 96.8% gross margin
    assert v.gross_margin_per_unit == pytest.approx(0.9684, abs=1e-3)
    # $40 CAC / $18.40 contribution → 2.17 months, which meets the 3-month payback target
    assert v.payback_months == pytest.approx(2.17, abs=0.02)
    assert v.payback_months <= v.unit_economics["payback_months_target"]
    assert len(v.kill_criteria) >= 3


@pytest.mark.parametrize("patch,reason", [
    ({"status": "launched"}, "status is fine on its own"),
])
def test_status_values(patch, reason):
    validate_document(bad(**patch))     # launched + auto_spend 0 is legal


@pytest.mark.parametrize("patch", [
    {"slug": "Media API"},
    {"status": "dreaming"},
    {"thesis": "make money"},
    {"pricing": {"model": "vibes", "plans": [{"name": "a", "usd_month": 9,
                                              "included_units": 100, "overage_usd": 0}]}},
    {"pricing": {"model": "flat_subscription", "plans": []}},
    {"pricing": {"model": "flat_subscription",
                 "plans": [{"name": "free", "usd_month": 0, "included_units": 10, "overage_usd": 0}]}},
    {"unit_economics.cogs_per_1k_units_usd": 0},
    {"unit_economics.target_gross_margin": 1.4},
    {"budgets.auto_spend_usd": 5},
    {"budgets.month_usd": 1},
    {"guardrails.egress_mode": "yolo"},
    {"guardrails.data_class": "everything"},
    {"guardrails.hitl": []},
    {"channels": []},
    {"kill_criteria": ["it feels bad"]},
    {"kill_criteria": ["no paying customer within 45 days"]},
])
def test_unworkable_ventures_are_refused(patch):
    with pytest.raises(VentureError):
        validate_document(bad(**patch))


def test_a_plan_that_cannot_hit_the_target_margin_is_refused():
    d = bad(**{"unit_economics.cogs_per_1k_units_usd": 12.0})   # ₹12 per 1k units vs $19 plan
    with pytest.raises(VentureError, match="below the target"):
        validate_document(d)


def test_load_all_is_honest_about_a_broken_sibling(tmp_path):
    good = tmp_path / "good"
    good.mkdir()
    (good / "venture.yaml").write_text(yaml.safe_dump(REAL))
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "venture.yaml").write_text(yaml.safe_dump(bad(**{"status": "dreaming"})))
    ventures, problems = load_all(str(tmp_path))
    assert [v.slug for v in ventures] == ["media-api"]
    assert len(problems) == 1 and "dreaming" in problems[0]
