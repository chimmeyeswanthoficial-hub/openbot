"""The routine contract: strict keys, budgeted, bounded, unattended, and the 15-minute floor."""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from spec import SpecError, cron_min_interval, parse, parse_dir  # noqa: E402

GOOD = """---
id: scout-daily
bot: ceo
schedule: "0 6 * * *"
budget_usd: 2.00
max_runtime_min: 40
initiator: routine
outputs: ["#ops-daily"]
---

Do the work, then stop.
"""


def mutate(**kw) -> str:
    """Replace a front-matter key by name, or add one if it is not there (before the closing ---)."""
    head, rest = GOOD.split("\n---\n", 1)
    lines = head.splitlines()          # lines[0] is the opening '---'
    keys = {ln.split(":")[0].strip() for ln in lines[1:]}
    out = [lines[0]]
    for line in lines[1:]:
        k = line.split(":")[0].strip()
        out.append(f"{k}: {kw.pop(k)}" if k in kw else line)
    for k, v in kw.items():
        assert k not in keys
        out.append(f"{k}: {v}")
    return "\n".join(out) + "\n---\n" + rest


def test_good_routine_parses():
    s = parse(GOOD)
    assert s.id == "scout-daily" and s.bot == "ceo" and s.budget_usd == 2.0
    assert s.initiator == "routine" and s.approval == "gate"
    assert s.interval_min == 24 * 60 and len(s.body_hash) == 16


def test_run_plan_exposes_the_worst_case_monthly_cost():
    plan = parse(GOOD).run_plan()
    assert plan["budget_usd"] == 2.0
    assert plan["worst_case_monthly_cost_usd"] == 60.0        # 2.00 × 30 fires
    assert plan["initiator"] == {"kind": "routine", "id": "scout-daily"}


@pytest.mark.parametrize("expr,expected", [
    ("*/15 * * * *", 15), ("0 * * * *", 60), ("30 9 * * *", 1440),
    ("30 9 * * 1-5", 1440), ("0 6 1 * *", None), ("bad", None),
])
def test_cron_intervals(expr, expected):
    assert cron_min_interval(expr) == expected


@pytest.mark.parametrize("text,reason", [
    (mutate(budget_usd="0"), "budget must be > 0"),
    (mutate(budget_usd="99"), "budget above the per-run ceiling"),
    (GOOD.replace("budget_usd: 2.00", "budget: 2.00"), "misspelled key"),
    (mutate(max_runtime_min="400"), "runtime out of range"),
    (mutate(initiator="person"), "a scheduled run must say routine"),
    (mutate(schedule='"*/5 * * * *"'), "below the 15-minute floor"),
    (mutate(schedule='"every morning"'), "not a cron"),
    (mutate(**{"retry": "9"}), "retry out of range"),
    (mutate(**{"approval": "sometimes"}), "approval must be gate|auto|never"),
])
def test_bad_routines_are_refused(text, reason):
    with pytest.raises(SpecError):
        parse(text)


def test_unknown_key_is_an_error_not_ignored():
    with pytest.raises(SpecError, match="unknown front-matter key"):
        parse(mutate(**{"spend_limit": "10"}))


def test_body_that_mentions_spending_cannot_be_never_approved():
    text = mutate(approval="never").replace(
        "Do the work, then stop.", "Provision a server and spend up to $5.")
    with pytest.raises(SpecError):
        parse(text)


def test_both_output_shapes_normalise_to_the_same_thing():
    a = parse(GOOD)                                        # ["#ops-daily"]
    b = parse(GOOD.replace('outputs: ["#ops-daily"]', 'outputs:\n  - channel: "#ops-daily"'))
    assert a.outputs == b.outputs == ("channel:#ops-daily",)


def test_output_kind_must_be_known():
    with pytest.raises(SpecError, match="output kind"):
        parse(GOOD.replace('outputs: ["#ops-daily"]', 'outputs: ["slack:#ops"]'))


def test_page_and_url_outputs_are_kept_verbatim():
    s = parse(GOOD.replace('outputs: ["#ops-daily"]',
                           'outputs: ["#ops-daily", "page:Reviews/2026-W45", "url:https://x.test/h"]'))
    assert s.outputs == ("channel:#ops-daily", "page:Reviews/2026-W45", "url:https://x.test/h")


def test_missing_front_matter_is_refused():
    with pytest.raises(SpecError):
        parse("# just a note\n")


def test_parse_dir_reports_problems_without_stopping():
    root = pathlib.Path(__file__).parents[3]
    specs, problems = parse_dir(str(root / ".openbot" / "routines"))
    assert len(specs) >= 6, [s.id for s in specs]
    assert problems == [], problems
    assert {s.bot for s in specs} >= {"ceo", "cto", "auditor", "growth", "ops"}


def test_two_routines_cannot_share_an_id(tmp_path):
    (tmp_path / "a.md").write_text(GOOD)
    (tmp_path / "b.md").write_text(GOOD.replace("0 6 * * *", "0 7 * * *"))
    specs, problems = parse_dir(str(tmp_path))
    assert len(specs) == 1 and "duplicate routine id" in problems[0]
