"""S10 signed manifests and crash-safe LOCAL POINTERS, not native launch proof."""

from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from trust_crypto import encode, sign
from verified_updates import UpdateError, VerifiedUpdates, file_sha


@pytest.fixture
def updates(tmp_path):
    key, agent = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    trust = tmp_path / "trust.json"
    trusted = {
        "owner": {
            "public_key": encode(key.public_key().public_bytes_raw()),
            "roles": ["local-update-test", "local-rollback-test"],
            "revoked": False,
        },
        "agent": {
            "public_key": encode(agent.public_key().public_bytes_raw()),
            "roles": ["agent"],
            "revoked": False,
        },
    }
    trust.write_text(json.dumps({"schema": "openbot.local-update-trust/1", "keys": trusted}))
    clock = [1000]
    tool = VerifiedUpdates(
        tmp_path / "updates",
        trust_file=trust,
        trust_sha256=file_sha(trust),
        platform="android",
        device_ref="synthetic-fixture",
        clock=lambda: clock[0],
    )
    source = tmp_path / "source"
    source.mkdir()
    artifact = source / "OpenBot-Control-Local-android.apk"
    artifact.write_bytes(b"unit fixture, NOT an APK build or device test")

    def manifest(version="0.2.0-local", **changes):
        value = {
            "schema": "openbot.update/1",
            "product": "openbot-control",
            "channel": "local-test",
            "version": version,
            "platform": "android",
            "artifact_kind": "demo-apk",
            "issued": 900,
            "expires": 2000,
            "source_sha256": "a" * 64,
            "artifacts": [
                {
                    "name": artifact.name,
                    "bytes": artifact.stat().st_size,
                    "sha256": file_sha(artifact),
                }
            ],
            "release_signed": False,
            "native_launch_verified": False,
            **changes,
        }
        return sign(key, "owner", value)

    return tool, manifest, key, agent, source, artifact, clock


def test_valid_manifest_stages_exact_bytes_but_never_installs(updates):
    tool, manifest, _key, _agent, source, artifact, _clock = updates
    result = tool.stage(manifest(), source)
    assert result["native_install"] is False and result["os_signature_verified"] is False
    assert (
        tool.root / "stages" / result["manifest"] / artifact.name
    ).read_bytes() == artifact.read_bytes()
    with pytest.raises(UpdateError):
        tool.activate(result["manifest"])
    pointer = tool.activate(result["manifest"], acknowledge_not_native_install=True)
    assert pointer["current"] == result["manifest"] and pointer["native_install"] is False
    assert tool.activate(result["manifest"], acknowledge_not_native_install=True)["replayed"]
    assert tool.stage(manifest(), source)["replayed"]


@pytest.mark.parametrize(
    "change",
    [
        {"channel": "production"},
        {"release_signed": True},
        {"native_launch_verified": True},
        {"platform": "ios"},
        {"artifact_kind": "ipa"},
        {"expires": 1000},
        {"version": "../../0.2.0-local"},
        {"source_sha256": "unbound"},
        {"artifacts": [{"name": "../escape.apk", "bytes": 1, "sha256": "a" * 64}]},
    ],
)
def test_manifest_cannot_smuggle_production_claims_or_unsafe_paths(updates, change):
    tool, manifest, _key, _agent, source, _artifact, _clock = updates
    with pytest.raises(UpdateError):
        tool.stage(manifest(**change), source)
    assert not list((tool.root / "stages").iterdir())


def test_tampered_artifact_signature_and_trust_root_are_refused(updates):
    tool, manifest, _key, agent, source, artifact, _clock = updates
    envelope = manifest()
    artifact.write_bytes(artifact.read_bytes() + b"tamper")
    with pytest.raises(UpdateError):
        tool.stage(envelope, source)
    forged = sign(agent, "agent", envelope["payload"])
    with pytest.raises(UpdateError):
        tool.stage(forged, source)
    tool.trust_file.write_text("{}")
    with pytest.raises(UpdateError):
        tool.stage(manifest(), source)
    assert not list(tool.root.glob(".stage-*"))


def test_stage_and_source_symlinks_are_refused(updates, tmp_path):
    tool, manifest, _key, _agent, source, artifact, _clock = updates
    envelope = manifest()
    original = tmp_path / "original"
    artifact.rename(original)
    artifact.symlink_to(original)
    with pytest.raises(UpdateError):
        tool.stage(envelope, source)
    artifact.unlink()
    artifact.write_bytes(original.read_bytes())
    identity = tool.stage(envelope, source)["manifest"]
    stage_file = tool.root / "stages" / identity / artifact.name
    stage_file.unlink()
    stage_file.symlink_to(original)
    with pytest.raises(UpdateError):
        tool.activate(identity, acknowledge_not_native_install=True)


def test_rollback_requires_separate_exact_owner_decision_and_keeps_high_water(updates):
    tool, manifest, key, agent, source, _artifact, _clock = updates
    old = tool.stage(manifest("0.2.0-local"), source)["manifest"]
    tool.activate(old, acknowledge_not_native_install=True)
    new = tool.stage(manifest("0.3.0-local"), source)["manifest"]
    tool.activate(new, acknowledge_not_native_install=True)
    with pytest.raises(UpdateError):
        tool.activate(old, acknowledge_not_native_install=True)
    payload = {
        "schema": "openbot.rollback/1",
        "from_manifest": new,
        "to_manifest": old,
        "device_ref": "synthetic-fixture",
        "platform": "android",
        "issued": 990,
        "expires": 1100,
        "reason": "Synthetic recovery drill",
    }
    for who, signer, change in [
        ("agent", agent, {}),
        ("owner", key, {"device_ref": "other"}),
        ("owner", key, {"from_manifest": "0" * 64}),
        ("owner", key, {"expires": 1000}),
    ]:
        with pytest.raises(UpdateError):
            tool.activate(
                old,
                acknowledge_not_native_install=True,
                rollback=sign(signer, who, {**payload, **change}),
            )
    result = tool.activate(
        old, acknowledge_not_native_install=True, rollback=sign(key, "owner", payload)
    )
    assert result["current"] == old and result["highest_version"] == [0, 3, 0]
    assert result["native_install"] is False


@pytest.mark.parametrize(
    "crash", ["before_state_replace", "after_state_replace", "before_stage_replace"]
)
def test_crash_recovery_has_old_or_new_verified_pointer_never_partial(updates, crash):
    tool, manifest, _key, _agent, source, _artifact, _clock = updates
    old = tool.stage(manifest(), source)["manifest"]
    tool.activate(old, acknowledge_not_native_install=True)
    newer = manifest("0.3.0-local")

    def fault(point):
        if point == crash:
            raise RuntimeError("synthetic crash point")

    if crash != "before_stage_replace":
        new = tool.stage(newer, source)["manifest"]
    tool.fault_hook = fault
    with pytest.raises(RuntimeError):
        if crash == "before_stage_replace":
            tool.stage(newer, source)
        else:
            tool.activate(new, acknowledge_not_native_install=True)
    tool.fault_hook = lambda _point: None
    (tool.root / ".stage-orphan").mkdir()
    (tool.root / ".stage-orphan" / "partial").write_text("incomplete")
    result = tool.recover()
    assert result["current"] == (new if crash == "after_state_replace" else old)
    assert not list(tool.root.glob(".stage-*"))
    assert not list(tool.root.glob(".state-*"))


def test_expired_or_corrupt_stage_cannot_be_activated(updates):
    tool, manifest, _key, _agent, source, artifact, clock = updates
    identity = tool.stage(manifest(), source)["manifest"]
    (tool.root / "stages" / identity / artifact.name).write_bytes(b"tampered")
    with pytest.raises(UpdateError):
        tool.activate(identity, acknowledge_not_native_install=True)
    clock[0] = 2000
    with pytest.raises(UpdateError):
        tool.validate(manifest())


def test_update_stage_root_and_broken_state_symlinks_are_refused(updates, tmp_path):
    tool, manifest, _key, _agent, source, _artifact, _clock = updates
    other = tmp_path / "unrelated"
    other.mkdir()
    (tool.root / "stages").rmdir()
    (tool.root / "stages").symlink_to(other, target_is_directory=True)
    with pytest.raises(UpdateError):
        tool.stage(manifest(), source)
    assert not list(other.iterdir())
    (tool.root / "stages").unlink()
    (tool.root / "stages").mkdir()
    (tool.root / "state.json").symlink_to(tmp_path / "missing-state")
    with pytest.raises(UpdateError):
        tool.state()
