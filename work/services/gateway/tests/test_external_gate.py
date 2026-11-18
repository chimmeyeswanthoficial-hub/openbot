"""S09 fails closed on the actual host. Positive signatures use a labeled unit fixture."""

from __future__ import annotations

import pytest
import staging_readiness as readiness
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from trust_crypto import TrustError, encode, sign


@pytest.fixture
def evidence(monkeypatch):
    private = {r: Ed25519PrivateKey.generate() for r in ["witness", "owner", "agent"]}
    roles = {
        "witness": ["independent-security-reviewer"],
        "owner": ["staging-owner", "provider-budget-owner"],
        "agent": ["agent"],
    }
    trusted = {
        r: {
            "public_key": encode(k.public_key().public_bytes_raw()),
            "roles": roles[r],
            "revoked": False,
            "independent_of_evaluated_agent": r == "witness",
            "qualification": "synthetic-unit-role-only" if r == "witness" else "",
        }
        for r, k in private.items()
    }
    observation = {
        "host_fingerprint": "a" * 64,
        "delegated_writable_cgroup": True,
        "unit_fixture_only": True,
        "not_actual_host_acceptance": True,
    }
    monkeypatch.setattr(readiness, "inspect_host", lambda _root: dict(observation))
    gate = readiness.ExternalGate(trusted=trusted, policy_sha256="b" * 64, clock=lambda: 1000)

    def receipt(who, **changes):
        payload = {
            "schema": "openbot.staging-approval/1",
            "host_fingerprint": "a" * 64,
            "policy_sha256": "b" * 64,
            "issued": 900,
            "expires": 1100,
            "approved": True,
            "evidence_sha256": "c" * 64,
            "tests": {k: True for k in readiness.HOST_TESTS},
            **changes,
        }
        return sign(private[who], who, payload)

    return gate, receipt, observation, private, trusted


def test_real_observation_never_accepts_readiness_json_or_namespace_alone():
    observation = readiness.inspect_host()
    result = readiness.ExternalGate(trusted={}, policy_sha256="unconfigured").evaluate(
        {"ready": True}, {"owner": True}
    )
    assert result["approved_host_and_security_gate"] is False
    assert result["provider_adapter_enabled"] is False
    assert result["public_release_authorized"] is False
    assert observation["rlimits_or_namespace_are_sufficient"] is False
    assert observation["provider_started"] is False
    with pytest.raises(TrustError):
        readiness.ExternalGate(trusted={}, policy_sha256="unconfigured").provider_admission(
            {"api_key": "not-authority"}
        )


@pytest.mark.parametrize(
    "change",
    [
        {"expires": 1000},
        {"host_fingerprint": "0" * 64},
        {"policy_sha256": "0" * 64},
        {"approved": False},
        {"tests": {"namespace_ok": True}},
    ],
)
def test_external_evidence_is_current_host_policy_and_test_bound(evidence, change):
    gate, receipt, _obs, _keys, _trusted = evidence
    result = gate.evaluate(receipt("witness", **change), receipt("owner"))
    assert result["approved_host_and_security_gate"] is False


def test_no_delegation_even_signed_evidence_cannot_override_live_host(evidence):
    gate, receipt, observation, _keys, _trusted = evidence
    observation["delegated_writable_cgroup"] = False
    result = gate.evaluate(receipt("witness"), receipt("owner"))
    assert "delegated_per_job_cgroup_unavailable" in result["blockers"]
    assert result["approved_host_and_security_gate"] is False


def test_independent_signer_not_evaluated_agent_and_never_starts_provider(evidence):
    gate, receipt, _obs, _keys, trusted = evidence
    assert not gate.evaluate(receipt("agent"), receipt("owner"))["approved_host_and_security_gate"]
    result = gate.evaluate(receipt("witness"), receipt("owner"))
    assert result["approved_host_and_security_gate"] is True  # unit fixture only
    assert result["provider_adapter_enabled"] is False
    trusted["witness"]["independent_of_evaluated_agent"] = False
    assert not gate.evaluate(receipt("witness"), receipt("owner"))[
        "approved_host_and_security_gate"
    ]


def test_provider_admission_is_tiny_expiring_and_still_not_execution(evidence):
    gate, receipt, _obs, keys, _trusted = evidence
    payload = {
        "schema": "openbot.provider-admission/1",
        "host_fingerprint": "a" * 64,
        "policy_sha256": "b" * 64,
        "account_ref": "owner-vault:synthetic",
        "provider": "owner-approved-one-provider",
        "max_minor": 100,
        "currency": "usd",
        "issued": 900,
        "expires": 1100,
        "eligible_account": True,
        "automatic_unattended": False,
    }
    for change in [
        {"max_minor": 101},
        {"max_minor": True},
        {"automatic_unattended": True},
        {"eligible_account": False},
        {"expires": 1000},
        {"account_ref": "pasted-key"},
    ]:
        with pytest.raises(TrustError):
            gate.provider_admission(
                sign(keys["owner"], "owner", {**payload, **change}),
                witness=receipt("witness"),
                owner_approval=receipt("owner"),
            )
    result = gate.provider_admission(
        sign(keys["owner"], "owner", payload),
        witness=receipt("witness"),
        owner_approval=receipt("owner"),
    )
    assert result["provider_adapter_enabled"] is False and result["max_minor"] == 100
