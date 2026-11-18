"""Signed local-test package verification, atomic staging/pointers and rollback.

A Linux-host verification tool, NOT a Windows/iOS/Android native installer or an
OS code signature. No download, launch, automatic install or release-key handling.
Trust-root hashes must be supplied out of band, never accepted from the bundle.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from trust_crypto import TrustError, canonical, digest, verify

PACKAGES = {
    "windows-x64": (
        "portable",
        {"OpenBot-Control-Local-x64.exe", "WebView2Loader.dll", "WebView2-LICENSE.txt"},
    ),
    "android": ("demo-apk", {"OpenBot-Control-Local-android.apk"}),
    "ios-source": ("source-only", {"OpenBot-Control-iOS-source.zip"}),
}
HEX = r"[a-f0-9]{64}"


def file_sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


class UpdateError(ValueError):
    pass


class VerifiedUpdates:
    def __init__(
        self,
        root,
        *,
        trust_file,
        trust_sha256,
        platform,
        device_ref,
        clock=time.time,
        fault_hook=lambda _point: None,
    ):
        self.root = Path(root)
        self.trust_file, self.trust_sha = Path(trust_file), trust_sha256
        self.platform, self.device_ref, self.clock = platform, device_ref, clock
        self.fault_hook = fault_hook
        if (
            platform not in PACKAGES
            or not isinstance(device_ref, str)
            or not 1 <= len(device_ref) <= 96
        ):
            raise UpdateError("explicit_supported_local_target_required")
        if not self.root.is_absolute() or any(
            p.is_symlink() for p in (self.root, *self.root.parents)
        ):
            raise UpdateError("private_update_root_required")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.root.stat().st_mode & 0o077:
            raise UpdateError("private_update_root_required")
        (self.root / "stages").mkdir(mode=0o700, exist_ok=True)
        if (self.root / "stages").is_symlink():
            raise UpdateError("stage_root_symlink_refused")
        self.trusted()

    def trusted(self):
        if (
            any(p.is_symlink() for p in (self.trust_file, *self.trust_file.parents))
            or file_sha(self.trust_file) != self.trust_sha
        ):
            raise UpdateError("out_of_band_pinned_trust_root_required")
        value = json.loads(self.trust_file.read_text())
        if set(value) != {"schema", "keys"} or value["schema"] != "openbot.local-update-trust/1":
            raise UpdateError("local_test_trust_schema_required")
        return value["keys"]

    @contextmanager
    def lock(self):
        if (self.root / "stages").is_symlink():
            raise UpdateError("stage_root_symlink_refused")
        descriptor = os.open(
            self.root / ".update.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600
        )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        except BlockingIOError as exc:
            raise UpdateError("update_busy") from exc
        finally:
            os.close(descriptor)

    def validate(self, envelope):
        try:
            payload = verify(envelope, self.trusted(), "local-update-test")
            fields = {
                "schema",
                "product",
                "channel",
                "version",
                "platform",
                "artifact_kind",
                "issued",
                "expires",
                "source_sha256",
                "artifacts",
                "release_signed",
                "native_launch_verified",
            }
            if (
                set(payload) != fields
                or payload["schema"] != "openbot.update/1"
                or payload["product"] != "openbot-control"
                or payload["channel"] != "local-test"
                or payload["platform"] != self.platform
                or payload["artifact_kind"] != PACKAGES[self.platform][0]
                or payload["release_signed"] is not False
                or payload["native_launch_verified"] is not False
                or not isinstance(payload["version"], str)
                or not re.fullmatch(
                    r"(0|[1-9]\d{0,3})\.(0|[1-9]\d{0,3})\.(0|[1-9]\d{0,3})-local",
                    payload["version"],
                )
                or not re.fullmatch(HEX, payload["source_sha256"])
                or type(payload["issued"]) is not int
                or type(payload["expires"]) is not int
                or not payload["issued"]
                <= int(self.clock())
                < payload["expires"]
                <= payload["issued"] + 7 * 86400
                or not isinstance(payload["artifacts"], list)
                or {a["name"] for a in payload["artifacts"]} != PACKAGES[self.platform][1]
                or len(payload["artifacts"]) != len(PACKAGES[self.platform][1])
            ):
                raise UpdateError("current_exact_local_manifest_required")
            for artifact in payload["artifacts"]:
                if (
                    set(artifact) != {"name", "bytes", "sha256"}
                    or type(artifact["bytes"]) is not int
                    or not 1 <= artifact["bytes"] <= 16 << 20
                    or not re.fullmatch(HEX, artifact["sha256"])
                ):
                    raise UpdateError("bounded_artifact_required")
            if sum(a["bytes"] for a in payload["artifacts"]) > 32 << 20:
                raise UpdateError("bundle_size_limit")
            return payload
        except (TrustError, KeyError, TypeError, ValueError) as exc:
            raise UpdateError("signed_verified_local_manifest_required") from exc

    def stage(self, envelope, source):
        payload = self.validate(envelope)
        identity = digest(envelope)
        source = Path(source).absolute()
        if any(p.is_symlink() for p in (source, *source.parents)):
            raise UpdateError("source_symlink_refused")
        with self.lock():
            target = self.root / "stages" / identity
            if target.exists():
                self._verify_stage(identity)
                return {
                    "manifest": identity,
                    "staged": True,
                    "replayed": True,
                    "native_install": False,
                }
            temp = Path(tempfile.mkdtemp(prefix=".stage-", dir=self.root))
            try:
                for artifact in payload["artifacts"]:
                    path = source / artifact["name"]
                    if path.is_symlink() or not path.is_file():
                        raise UpdateError("regular_artifact_required")
                    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
                    total, hasher = 0, hashlib.sha256()
                    with (
                        os.fdopen(descriptor, "rb") as src,
                        (temp / artifact["name"]).open("xb") as dest,
                    ):
                        while block := src.read(65536):
                            total += len(block)
                            if total > artifact["bytes"]:
                                raise UpdateError("artifact_size_mismatch")
                            hasher.update(block)
                            dest.write(block)
                        dest.flush()
                        os.fsync(dest.fileno())
                    if total != artifact["bytes"] or hasher.hexdigest() != artifact["sha256"]:
                        raise UpdateError("artifact_digest_mismatch")
                (temp / "manifest.json").write_bytes(canonical(envelope))
                with (temp / "manifest.json").open("rb") as handle:
                    os.fsync(handle.fileno())
                self.fault_hook("before_stage_replace")
                os.replace(temp, target)
                self._sync_dir(self.root / "stages")
            finally:
                if temp.exists():
                    shutil.rmtree(temp)
        return {
            "manifest": identity,
            "staged": True,
            "native_install": False,
            "os_signature_verified": False,
            "launch_verified": False,
        }

    def _verify_stage(self, identity):
        if not isinstance(identity, str) or not re.fullmatch(HEX, identity):
            raise UpdateError("exact_stage_identity_required")
        stage = self.root / "stages" / identity
        if stage.is_symlink():
            raise UpdateError("stage_symlink_refused")
        if (stage / "manifest.json").is_symlink():
            raise UpdateError("stage_manifest_symlink_refused")
        envelope = json.loads((stage / "manifest.json").read_text())
        if digest(envelope) != identity:
            raise UpdateError("stage_manifest_mismatch")
        payload = self.validate(envelope)
        for artifact in payload["artifacts"]:
            path = stage / artifact["name"]
            if (
                path.is_symlink()
                or path.stat().st_size != artifact["bytes"]
                or file_sha(path) != artifact["sha256"]
            ):
                raise UpdateError("staged_artifact_mismatch")
        return payload

    @staticmethod
    def _sync_dir(path):
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def state(self):
        path = self.root / "state.json"
        if path.is_symlink():
            raise UpdateError("state_symlink_refused")
        if not path.exists():
            return {
                "schema": "openbot.local-update-state/1",
                "current": None,
                "previous": None,
                "highest_version": [0, 0, 0],
            }
        if path.is_symlink():
            raise UpdateError("state_symlink_refused")
        value = json.loads(path.read_text())
        if (
            set(value) != {"schema", "current", "previous", "highest_version"}
            or value["schema"] != "openbot.local-update-state/1"
            or any(
                v is not None and (not isinstance(v, str) or not re.fullmatch(HEX, v))
                for v in [value["current"], value["previous"]]
            )
            or type(value["highest_version"]) is not list
            or len(value["highest_version"]) != 3
            or any(type(n) is not int or not 0 <= n <= 9999 for n in value["highest_version"])
        ):
            raise UpdateError("update_state_corrupt")
        return value

    def activate(self, identity, *, acknowledge_not_native_install=False, rollback=None):
        if acknowledge_not_native_install is not True:
            raise UpdateError("explicit_local_pointer_only_acknowledgement_required")
        with self.lock():
            payload = self._verify_stage(identity)
            state = self.state()
            if state["current"] == identity:
                return {**state, "replayed": True, "native_install": False}
            version = [int(p) for p in payload["version"].removesuffix("-local").split(".")]
            if version <= state["highest_version"]:
                try:
                    receipt = verify(rollback, self.trusted(), "local-rollback-test")
                    if (
                        set(receipt)
                        != {
                            "schema",
                            "from_manifest",
                            "to_manifest",
                            "device_ref",
                            "platform",
                            "issued",
                            "expires",
                            "reason",
                        }
                        or receipt["schema"] != "openbot.rollback/1"
                        or receipt["from_manifest"] != state["current"]
                        or receipt["to_manifest"] != identity
                        or identity != state["previous"]
                        or receipt["device_ref"] != self.device_ref
                        or receipt["platform"] != self.platform
                        or not receipt["issued"]
                        <= int(self.clock())
                        < receipt["expires"]
                        <= receipt["issued"] + 120
                        or not isinstance(receipt["reason"], str)
                        or not 1 <= len(receipt["reason"]) <= 128
                    ):
                        raise UpdateError("bound_rollback_required")
                except (TrustError, KeyError, TypeError, ValueError) as exc:
                    raise UpdateError("anti_rollback_owner_decision_required") from exc
            updated = {
                "schema": "openbot.local-update-state/1",
                "current": identity,
                "previous": state["current"],
                "highest_version": max(version, state["highest_version"]),
            }
            descriptor, name = tempfile.mkstemp(prefix=".state-", dir=self.root)
            temporary = Path(name)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(canonical(updated))
                    handle.flush()
                    os.fsync(handle.fileno())
                self.fault_hook("before_state_replace")
                os.replace(temporary, self.root / "state.json")
                self._sync_dir(self.root)
                self.fault_hook("after_state_replace")
            finally:
                temporary.unlink(missing_ok=True)
        return {**updated, "native_install": False, "launch_verified": False}

    def recover(self):
        with self.lock():
            for path in [*self.root.glob(".stage-*"), *self.root.glob(".state-*")]:
                if path.is_symlink():
                    raise UpdateError("recovery_symlink_refused")
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            state = self.state()
            if state["current"] is not None:
                self._verify_stage(state["current"])
            return {**state, "recovered": True, "native_install": False}


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify-stage", "activate-pointer", "recover"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--trust", type=Path, required=True)
    parser.add_argument("--trust-sha256", required=True)
    parser.add_argument("--platform", choices=sorted(PACKAGES), required=True)
    parser.add_argument("--device-ref", required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--id")
    parser.add_argument("--rollback", type=Path)
    parser.add_argument("--ack-local-pointer-only", action="store_true")
    args = parser.parse_args()
    tool = VerifiedUpdates(
        args.root.absolute(),
        trust_file=args.trust,
        trust_sha256=args.trust_sha256,
        platform=args.platform,
        device_ref=args.device_ref,
    )
    if args.command == "verify-stage":
        if not args.manifest or not args.source:
            parser.error("--manifest and --source required")
        result = tool.stage(json.loads(args.manifest.read_text()), args.source)
    elif args.command == "activate-pointer":
        result = tool.activate(
            args.id,
            acknowledge_not_native_install=args.ack_local_pointer_only,
            rollback=json.loads(args.rollback.read_text()) if args.rollback else None,
        )
    else:
        result = tool.recover()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
