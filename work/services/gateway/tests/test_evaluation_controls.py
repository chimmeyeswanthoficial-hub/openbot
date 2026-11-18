"""Explicit synthetic UNIT signers/clocks. No held-out evaluation or pilot occurs."""

from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from evaluation_controls import Assessment, AssessmentError
from trust_crypto import digest, encode, sign


@pytest.fixture
def assessment(tmp_path):
    roles = [
        "evaluation-custodian",
        "independent-evaluator",
        "pilot-owner",
        "pilot-observer",
        "agent",
    ]
    keys = {role: Ed25519PrivateKey.generate() for role in roles}
    trusted = {
        role: {
            "public_key": encode(key.public_key().public_bytes_raw()),
            "roles": [role],
            "revoked": False,
            "independent": role != "agent",
            "qualified": role != "agent",
            "human": role == "pilot-owner",
        }
        for role, key in keys.items()
    }
    clock = [1794268800]
    policy = {
        "schema": "openbot.assessment-policy/1",
        "workflow": "qa-docs",
        "min_tasks": 20,
        "min_days": 30,
        "min_quality": 80,
        "max_human_minutes": 100,
        "max_cost_minor": 100,
        "oncall_ref": "c" * 64,
    }
    tool = Assessment(
        tmp_path / "assessment",
        policy=policy,
        policy_sha256=digest(policy),
        trusted=trusted,
        initialize=True,
        clock=lambda: clock[0],
    )
    tasks = [digest({"synthetic-unit-task": i}) for i in range(24)]
    freeze = {
        "schema": "openbot.protected-suite/1",
        "policy_sha256": digest(policy),
        "workflow": "qa-docs",
        "baseline_sha256": "a" * 64,
        "candidate_sha256": "b" * 64,
        "suite_sha256": digest(tasks),
        "criteria_sha256": "d" * 64,
        "task_hashes": tasks,
        "frozen_at": clock[0],
        "corpus_kind": "sealed-held-out",
        "synthetic": True,
    }

    def signed(role, value):
        return sign(keys[role], role, value)

    def report(version="b", **changes):
        rows = [
            {
                "task_sha256": t,
                "evidence_sha256": digest({"synthetic-unit-task": t, "version": version}),
                "quality": 90,
                "critical_errors": 0,
                "permission_failures": 0,
                "data_loss": False,
                "recovery_ok": True,
                "injection_ok": True,
                "human_minutes": 1,
                "cpu_millis": 100,
                "peak_rss_bytes": 1000,
                "cost_minor": 1,
            }
            for t in tasks
        ]
        return {
            "schema": "openbot.assessment-report/1",
            "freeze_sha256": digest(signed("evaluation-custodian", freeze)),
            "source_sha256": version * 64,
            "policy_sha256": digest(policy),
            "issued": clock[0],
            "results": rows,
            "synthetic": True,
            **changes,
        }

    return tool, policy, freeze, report, signed, clock, trusted


def test_freeze_precedes_reports_and_policy_cannot_be_relabelled(assessment):
    tool, policy, freeze, report, signed, _clock, _trusted = assessment
    with pytest.raises(AssessmentError):
        tool.evaluate(signed("independent-evaluator", report()))
    tool.freeze(signed("evaluation-custodian", freeze))
    with pytest.raises(AssessmentError):
        tool.freeze(signed("evaluation-custodian", {**freeze, "criteria_sha256": "e" * 64}))
    tool.evaluate(signed("independent-evaluator", report("a")))
    tool.evaluate(signed("independent-evaluator", report("b")))
    status = tool.status()
    assert status["candidate_thresholds_met"] is True
    assert status["independent_evaluation_accepted"] is False and status["fixture_only"] is True
    assert status["pilot_started"] is False and status["release_authorized"] is False
    policy["min_quality"] = 0
    assert tool.policy["min_quality"] == 80


@pytest.mark.parametrize(
    "change",
    [
        {"task_hashes": ["a" * 64] * 24},
        {"task_hashes": ["a" * 64] * 19},
        {"corpus_kind": "public-calibration"},
        {"workflow": "owned-media"},
        {"frozen_at": 1794268801},
        {"policy_sha256": "0" * 64},
    ],
)
def test_public_duplicate_short_future_or_cross_workflow_suite_is_not_protected(assessment, change):
    tool, _, freeze, _, signed, _, _ = assessment
    with pytest.raises(AssessmentError):
        tool.freeze(signed("evaluation-custodian", {**freeze, **change}))


@pytest.mark.parametrize(
    "defect",
    [
        "critical",
        "permission",
        "loss",
        "recovery",
        "injection",
        "quality",
        "cost",
        "human",
        "missing",
        "duplicate",
        "bool-number",
        "wrong-source",
    ],
)
def test_release_blocking_report_defects_fail_closed_or_remain_failed(assessment, defect):
    tool, _, freeze, report, signed, _, _ = assessment
    tool.freeze(signed("evaluation-custodian", freeze))
    tool.evaluate(signed("independent-evaluator", report("a")))
    body = report("b")
    key = {
        "critical": "critical_errors",
        "permission": "permission_failures",
        "loss": "data_loss",
        "recovery": "recovery_ok",
        "injection": "injection_ok",
        "quality": "quality",
        "cost": "cost_minor",
        "human": "human_minutes",
    }.get(defect)
    if key:
        body["results"][0][key] = {
            "critical": 1,
            "permission": 1,
            "loss": True,
            "recovery": False,
            "injection": False,
            "quality": 79,
            "cost": 101,
            "human": 101,
        }[defect]
    if defect == "missing":
        body["results"].pop()
    if defect == "duplicate":
        body["results"][0] = body["results"][1]
    if defect == "bool-number":
        body["results"][0]["cost_minor"] = True
    if defect == "wrong-source":
        body["source_sha256"] = "e" * 64
    with suppress(AssessmentError):
        tool.evaluate(signed("independent-evaluator", body))
    assert tool.status()["candidate_thresholds_met"] is False
    assert tool.status()["release_authorized"] is False


def ready(assessment):
    tool, _, freeze, report, signed, clock, _ = assessment
    tool.freeze(signed("evaluation-custodian", freeze))
    for version in ["a", "b"]:
        tool.evaluate(signed("independent-evaluator", report(version)))
    grant = {
        "schema": "openbot.pilot-grant/1",
        "source_sha256": "b" * 64,
        "policy_sha256": tool.policy_sha,
        "freeze_sha256": tool.freeze_sha(),
        "starts_at": clock[0],
        "expires": clock[0] + 60 * 86400,
        "oncall_ref": "c" * 64,
        "consent_ref": "d" * 64,
        "budget_minor": 100,
        "synthetic": True,
    }
    tool.start(signed("pilot-owner", grant))

    def day(**changes):
        body = {
            "schema": "openbot.pilot-day/1",
            "source_sha256": "b" * 64,
            "grant_sha256": digest(signed("pilot-owner", grant)),
            "day": datetime.fromtimestamp(clock[0], UTC).date().isoformat(),
            "observed_at": clock[0],
            "evidence_sha256": digest({"synthetic-clock": clock[0]}),
            "usage_minor": 0,
            "usage_verified": True,
            "critical_errors": 0,
            "data_loss": False,
            "healthy": True,
            "synthetic": True,
            **changes,
        }
        return signed("pilot-observer", body)

    return tool, clock, day, signed, grant


def test_agent_cannot_freeze_evaluate_or_authorize_pilot(assessment):
    tool, _, freeze, report, signed, _, _ = assessment
    with pytest.raises(AssessmentError):
        tool.freeze(signed("agent", freeze))
    tool.freeze(signed("evaluation-custodian", freeze))
    with pytest.raises(AssessmentError):
        tool.evaluate(signed("agent", report()))
    assert tool.status()["independent_evaluation_accepted"] is False


def test_revocation_invalidates_previous_evaluation(assessment):
    tool, _clock, _day, _signed, _grant = ready(assessment)
    assessment[-1]["independent-evaluator"]["revoked"] = True
    assert tool.status()["candidate_thresholds_met"] is False
    assert tool.status()["pilot_gate_accepted"] is False


@pytest.mark.parametrize(
    "change",
    [
        {"day": "2020-01-01"},
        {"observed_at": 1794268200},
        {"observed_at": 1794270000},
        {"source_sha256": "a" * 64},
        {"synthetic": False},
    ],
)
def test_no_backfilled_future_or_cross_version_pilot_days(assessment, change):
    tool, _, day, _, _ = ready(assessment)
    with pytest.raises(AssessmentError):
        tool.observe(day(**change))
    assert tool.status()["observed_days"] == 0


def test_fixture_clock_jumps_are_never_real_observed_pilot_acceptance(assessment):
    tool, clock, day, _, _ = ready(assessment)
    for _ in range(31):
        tool.observe(day())
        clock[0] += 86400
    result = tool.status()
    assert result["observed_days"] == 31 and result["elapsed_requirement_met"] is True
    assert result["fixture_only"] is True and result["pilot_gate_accepted"] is False
    assert result["pilot_started"] is False and result["release_authorized"] is False


@pytest.mark.parametrize(
    "change",
    [
        {"critical_errors": 1},
        {"data_loss": True},
        {"healthy": False},
        {"usage_minor": 101},
        {"usage_verified": False},
    ],
)
def test_failed_pilot_observation_stops_instead_of_resetting_history(assessment, change):
    tool, clock, day, signed, grant = ready(assessment)
    tool.observe(day(**change))
    assert tool.status()["stopped"] is True
    clock[0] += 86400
    with pytest.raises(AssessmentError):
        tool.observe(day())
    with pytest.raises(AssessmentError):
        tool.start(signed("pilot-owner", {**grant, "starts_at": clock[0]}))


def test_missing_day_and_duplicate_day_are_not_30_consecutive_observed_days(assessment):
    tool, clock, day, _, _ = ready(assessment)
    tool.observe(day())
    with pytest.raises(AssessmentError):
        tool.observe(day())
    clock[0] += 2 * 86400
    with pytest.raises(AssessmentError):
        tool.observe(day())
    assert tool.status()["stopped"] is True and tool.status()["pilot_gate_accepted"] is False


def test_nonfixture_mode_refuses_synthetic_grants_and_json_host_readiness(assessment, tmp_path):
    _tool, policy, freeze, _report, signed, clock, trusted = assessment
    real = Assessment(
        tmp_path / "external",
        policy=policy,
        policy_sha256=digest(policy),
        trusted=trusted,
        fixture_only=False,
        initialize=True,
    )
    with pytest.raises(AssessmentError):
        real.freeze(signed("evaluation-custodian", freeze))
    assert real.status()["pilot_started"] is False
    assert real.status()["release_authorized"] is False


def test_evaluation_profile_pins_policy_and_fixture_mode_across_restart(assessment):
    tool, policy, _, _, _, clock, trusted = assessment
    changed = {**policy, "min_quality": 1}
    with pytest.raises(AssessmentError):
        Assessment(
            tool.root,
            policy=changed,
            policy_sha256=digest(changed),
            trusted=trusted,
            clock=lambda: clock[0],
        )
    with pytest.raises(AssessmentError):
        Assessment(
            tool.root,
            policy=policy,
            policy_sha256=digest(policy),
            trusted=trusted,
            fixture_only=False,
        )


def test_nonfixture_profile_never_accepts_an_injected_unit_clock(assessment, tmp_path):
    _, policy, _, _, _, clock, trusted = assessment
    with pytest.raises(AssessmentError):
        Assessment(
            tmp_path / "fake-time",
            policy=policy,
            policy_sha256=digest(policy),
            trusted=trusted,
            fixture_only=False,
            initialize=True,
            clock=lambda: clock[0],
        )


def test_backdated_report_does_not_precede_local_freeze_receipt(assessment):
    tool, _, freeze, report, signed, clock, _ = assessment
    old = report()
    clock[0] += 100
    tool.freeze(signed("evaluation-custodian", freeze))
    with pytest.raises(AssessmentError):
        tool.evaluate(signed("independent-evaluator", old))


@pytest.mark.parametrize("payload", [None, [], "signed string"])
def test_malformed_but_signed_payload_is_not_evaluation_evidence(assessment, payload):
    tool, _, _, _, signed, _, _ = assessment
    with pytest.raises(AssessmentError):
        tool.freeze(signed("evaluation-custodian", payload))


def test_stopped_observation_ledger_is_latched_even_if_clock_rewinds(assessment):
    tool, clock, day, _, _ = ready(assessment)
    tool.observe(day())
    clock[0] += 2 * 86400
    assert tool.status()["stopped"] is True
    clock[0] -= 86400
    with pytest.raises(AssessmentError):
        tool.observe(day())


def test_missing_first_pilot_day_is_stopped_without_backfill(assessment):
    tool, clock, day, _, _ = ready(assessment)
    clock[0] += 86400
    assert tool.status()["stopped"] is True
    with pytest.raises(AssessmentError):
        tool.observe(day())


def test_daily_observation_binds_exact_owner_grant(assessment):
    tool, _, day, _, _ = ready(assessment)
    with pytest.raises(AssessmentError):
        tool.observe(day(grant_sha256="0" * 64))
    assert tool.status()["observed_days"] == 0


def test_owner_key_cannot_masquerade_as_independent_evaluator(assessment):
    tool, _, freeze, report, signed, _, trusted = assessment
    trusted["pilot-owner"]["public_key"] = trusted["independent-evaluator"]["public_key"]
    tool.freeze(signed("evaluation-custodian", freeze))
    with pytest.raises(AssessmentError):
        tool.evaluate(signed("independent-evaluator", report()))
