"""S09 readiness inspector and fail-closed external evidence admission.

This module neither creates a sandbox nor starts a provider. A namespace/rlimit
fixture or JSON saying 'ready' can never substitute for live delegation and
independent witnessed enforcement on the owner-approved host.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import time
from pathlib import Path

from trust_crypto import TrustError, canonical, digest, verify

HOST_TESTS = frozenset(
    {
        "cpu_enforced",
        "memory_enforced",
        "pids_enforced",
        "disk_hard_quota",
        "default_deny_egress",
        "no_host_secrets",
        "no_authority_db_mounts",
        "no_host_sockets",
        "kernel_authority_protected",
        "process_tree_stop",
        "parent_death_cleanup",
        "escape_path_symlink_metadata",
        "tenant_boundary",
    }
)


def _read(path, maximum=16384):
    try:
        with Path(path).open() as handle:
            return handle.read(maximum)
    except OSError:
        return ""


def inspect_host(cgroup_root="/sys/fs/cgroup"):
    root = Path(cgroup_root)
    controllers = _read(root / "cgroup.controllers").split()
    membership = _read("/proc/self/cgroup").strip()
    mount = [
        line
        for line in _read("/proc/self/mountinfo", 1 << 20).splitlines()
        if " - cgroup2 " in line and root.is_relative_to(Path(line.split()[4]))
    ]
    delegated = bool(
        root.is_dir()
        and root.is_absolute()
        and not any(p.is_symlink() for p in (root, *root.parents))
        and mount
        and os.access(root, os.W_OK)
        and {"cpu", "memory", "pids"} <= set(controllers)
        and {"cpu", "memory", "pids"} <= set(_read(root / "cgroup.subtree_control").split())
    )
    identity = {
        "kernel": platform.release(),
        "machine": platform.machine(),
        "uid": os.getuid(),
        "boot_id_sha256": hashlib.sha256(
            _read("/proc/sys/kernel/random/boot_id").encode()
        ).hexdigest(),
        "mount_namespace": os.readlink("/proc/self/ns/mnt")
        if Path("/proc/self/ns/mnt").exists()
        else "",
        "membership": membership,
        "cgroup_root": str(root),
    }
    return {
        "schema": "openbot.staging-observation/1",
        "host_fingerprint": digest(identity),
        "identity": identity,
        "controllers": controllers,
        "cgroup_v2_mount": bool(mount),
        "delegated_writable_cgroup": delegated,
        "observed_at": int(time.time()),
        "rlimits_or_namespace_are_sufficient": False,
        "disk_hard_quota_independently_tested": False,
        "hostile_tests_independently_witnessed": False,
        "provider_started": False,
        "production_ready": False,
    }


class ExternalGate:
    def __init__(self, *, trusted, policy_sha256, cgroup_root="/sys/fs/cgroup", clock=time.time):
        self.trusted, self.policy_sha256 = trusted, policy_sha256
        self.cgroup_root, self.clock = cgroup_root, clock

    def evaluate(self, witness=None, owner_approval=None):
        observation = inspect_host(self.cgroup_root)  # never caller-supplied ready JSON
        blockers = []
        if not observation["delegated_writable_cgroup"]:
            blockers.append("delegated_per_job_cgroup_unavailable")
        verified = {}
        for name, envelope, role in [
            ("witness", witness, "independent-security-reviewer"),
            ("owner", owner_approval, "staging-owner"),
        ]:
            try:
                payload = verify(envelope, self.trusted, role)
                expected = {
                    "schema",
                    "host_fingerprint",
                    "policy_sha256",
                    "issued",
                    "expires",
                    "approved",
                    "evidence_sha256",
                    "tests",
                }
                if (
                    set(payload) != expected
                    or payload["schema"] != "openbot.staging-approval/1"
                    or payload["host_fingerprint"] != observation["host_fingerprint"]
                    or payload["policy_sha256"] != self.policy_sha256
                    or type(payload["issued"]) is not int
                    or type(payload["expires"]) is not int
                    or not payload["issued"]
                    <= int(self.clock())
                    < payload["expires"]
                    <= payload["issued"] + 3600
                    or payload["approved"] is not True
                    or set(payload["tests"]) != HOST_TESTS
                    or not all(v is True for v in payload["tests"].values())
                    or not isinstance(payload["evidence_sha256"], str)
                    or len(payload["evidence_sha256"]) != 64
                ):
                    raise TrustError("bound_witness_required")
                verified[name] = envelope["key_id"]
                signer = self.trusted[envelope["key_id"]]
                if name == "witness" and (
                    signer.get("independent_of_evaluated_agent") is not True
                    or not signer.get("qualification")
                ):
                    raise TrustError("independent_qualified_witness_required")
            except (TrustError, KeyError, TypeError, ValueError):
                verified.pop(name, None)
                blockers.append(name + "_current_signed_external_evidence_missing")
        if (
            "witness" in verified
            and "owner" in verified
            and self.trusted[verified["witness"]]["public_key"]
            == self.trusted[verified["owner"]]["public_key"]
        ):
            blockers.append("owner_and_independent_witness_must_differ")
        return {
            "schema": "openbot.external-gate/1",
            "observation": observation,
            "approved_host_and_security_gate": not blockers,
            "blockers": blockers,
            "provider_adapter_enabled": False,
            "public_release_authorized": False,
            "note": "Inspection/signatures alone are not a hostile sandbox implementation.",
        }

    def provider_admission(self, grant, *, witness=None, owner_approval=None):
        result = self.evaluate(witness, owner_approval)
        if not result["approved_host_and_security_gate"]:
            raise TrustError("external_host_and_independent_security_gate_required_first")
        payload = verify(grant, self.trusted, "provider-budget-owner")
        fields = {
            "schema",
            "host_fingerprint",
            "policy_sha256",
            "account_ref",
            "provider",
            "max_minor",
            "currency",
            "expires",
            "issued",
            "eligible_account",
            "automatic_unattended",
        }
        if (
            set(payload) != fields
            or payload["schema"] != "openbot.provider-admission/1"
            or payload["host_fingerprint"] != result["observation"]["host_fingerprint"]
            or payload["policy_sha256"] != self.policy_sha256
            or type(payload["max_minor"]) is not int
            or not 1 <= payload["max_minor"] <= 100
            or payload["currency"] != "usd"
            or payload["eligible_account"] is not True
            or payload["automatic_unattended"] is not False
            or not payload["issued"]
            <= int(self.clock())
            < payload["expires"]
            <= payload["issued"] + 900
            or not isinstance(payload["account_ref"], str)
            or not payload["account_ref"].startswith("owner-vault:")
            or payload["provider"] not in {"owner-approved-one-provider"}
        ):
            raise TrustError("one_tiny_expiring_owner_budget_required")
        return {
            "admission_envelope_verified": True,
            "max_minor": payload["max_minor"],
            "provider_adapter_enabled": False,
            "requires_next": [
                "actual streaming/tool/reservation/stop enforcement",
                "independent provider usage receipts",
                "owner supervised execution",
            ],
            "no_key_or_account_alone_clears_gate": True,
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    policy = Path(__file__).resolve().parents[3] / "audit/staging-required-controls.json"
    result = ExternalGate(
        trusted={}, policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest()
    ).evaluate()
    args.receipt.write_bytes(canonical(result) + b"\n")
    print(
        json.dumps({"approved": False, "blockers": result["blockers"], "provider_started": False})
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
