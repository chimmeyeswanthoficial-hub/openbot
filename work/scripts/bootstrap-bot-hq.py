#!/usr/bin/env python3
"""Restore the pinned Node toolchain into snapshot-excluded .cache (Linux x86_64).

Official HTTPS download, exact SHA-256 checked before extraction. This is not an
independent signature/build attestation. No shell installer, sudo or provider call.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        raise SystemExit("This measured runtime lock is Linux x86_64 only. Review a platform-specific Node lock first.")
    lock = json.loads((ROOT / "audit/bot-hq-runtime-lock.json").read_text())
    version = lock["version"]
    if version != "v24.22.3" or lock["platform"] != "linux-x64":
        raise SystemExit("Unexpected runtime lock; review explicitly before changing the bootstrap.")
    url = f"https://nodejs.org/dist/{version}/node-{version}-linux-x64.tar.xz"
    if lock["url"] != url:
        raise SystemExit("Refusing a non-official runtime source")
    cache = ROOT / ".cache/openbot-toolchains"
    runtime = cache / f"node-{version}-linux-x64"
    marker = runtime / ".openbot-verified-sha256"
    binary = runtime / "bin/node"
    if (marker.is_file() and marker.read_text().strip() == lock["sha256"] and binary.is_file()
            and subprocess.check_output([str(binary), "--version"], text=True).strip() == version):
        print(runtime / "bin")
        return
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f"node-{version}-linux-x64.tar.xz"
    print(f"Restoring checksum-pinned Node {version}; download is toolchain-only.", file=sys.stderr)
    partial = archive.with_suffix(".partial")
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as out:
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
            out.write(chunk)
    if digest.hexdigest() != lock["sha256"]:
        raise SystemExit("Node checksum mismatch; archive was NOT executed/extracted")
    os.replace(partial, archive)
    with tarfile.open(archive) as source:
        prefix = f"node-{version}-linux-x64/"
        if any(not (member.name == prefix[:-1] or member.name.startswith(prefix)) for member in source):
            raise SystemExit("Unexpected runtime archive layout")
        source.extractall(cache, filter="data")
    marker.write_text(lock["sha256"] + "\n")
    if subprocess.check_output([str(binary), "--version"], text=True).strip() != version:
        raise SystemExit("Unexpected restored runtime")
    print(runtime / "bin")


if __name__ == "__main__":
    main()
